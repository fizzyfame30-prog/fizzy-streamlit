import os
import numpy as np
import pandas as pd
import yfinance as yf
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

APP_NAME = os.getenv("APP_NAME", "Fizzy")
APP_TAGLINE = os.getenv("APP_TAGLINE", "Your AI trading and personal assistant")
OWNER_NAME = os.getenv("OWNER_NAME", "Your Name")
PUBLIC_EMAIL = os.getenv("PUBLIC_EMAIL", "hello@yourdomain.com")
CONTACT_URL = os.getenv("CONTACT_URL", "https://yourdomain.com/contact")
DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "en")

api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key) if api_key else None

WATCHLIST = ["AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "BTC-USD", "ETH-USD", "SPY", "QQQ"]

st.set_page_config(page_title=APP_NAME, page_icon="📈", layout="wide")


def rsi(series, period=14):
    delta = series.diff().dropna()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi_val = 100 - (100 / (1 + rs))
    return float(rsi_val.iloc[-1]) if not rsi_val.empty else 50.0


def compute_signal(df):
    if df.empty:
        return {"score": 0, "action": "wait"}

    close = df["Close"].astype(float)
    last = float(close.iloc[-1])
    prev = float(close.iloc[-2]) if len(close) > 1 else last
    change_pct = ((last - prev) / prev) * 100 if prev else 0.0
    sma5 = float(close.tail(5).mean())
    sma20 = float(close.tail(20).mean())
    sma50 = float(close.tail(50).mean())
    rsi_value = rsi(close)

    score = 50
    if last > sma20:
        score += 15
    else:
        score -= 10
    if last > sma50:
        score += 10
    else:
        score -= 10
    if rsi_value > 60:
        score += 10
    elif rsi_value < 40:
        score -= 10
    if change_pct > 0:
        score += 8
    else:
        score -= 8

    action = "bullish" if score >= 60 else "bearish" if score <= 40 else "neutral"
    return {
        "last": last,
        "change_pct": change_pct,
        "sma20": sma20,
        "sma50": sma50,
        "rsi": rsi_value,
        "score": int(max(0, min(100, score))),
        "action": action,
    }


def get_market_data(symbol):
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="3mo", interval="1d")
        if hist.empty:
            return {"symbol": symbol, "error": "No data"}
        signal = compute_signal(hist)
        signal["symbol"] = symbol
        signal["name"] = ticker.info.get("shortName", symbol)
        return signal
    except Exception as e:
        return {"symbol": symbol, "error": str(e)}


def build_ai_response(message, language):
    if client:
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            f"You are {APP_NAME}, a trading and personal AI assistant. "
                            "Provide helpful, careful analysis. Never promise profits. "
                            "Always mention that this is educational and not financial advice."
                        ),
                    },
                    {"role": "user", "content": message},
                ],
                temperature=0.7,
            )
            return response.choices[0].message.content.strip()
        except Exception:
            pass

    text = message.lower()
    if "risk" in text or "danger" in text:
        return "Risk management matters most. Define your stop-loss, position size, and max drawdown before taking a trade."
    if "trend" in text or "bullish" in text or "bearish" in text or "market" in text:
        return "Check trend, volume, resistance, and confirmation before acting. Good trading plans focus on risk first, then signal quality."
    if "plan" in text or "strategy" in text or "trade" in text:
        return "A solid plan includes entry, stop, target, risk limit, and a review process. Do not force trades without clear structure."
    if "hello" in text or "hi" in text or "hey" in text:
        return f"Hi! I’m {APP_NAME}. I can help you with trading, market analysis, personal planning, and risk management."
    return "I can help with market overview, portfolio review, trade planning, and risk management. This is educational analysis, not financial advice."


st.title(APP_NAME)
st.caption(APP_TAGLINE)

st.markdown(f"Owner: **{OWNER_NAME}**")
st.markdown(f"Public email: **{PUBLIC_EMAIL}**")
st.markdown(f"Contact: [{CONTACT_URL}]({CONTACT_URL})")

language = st.selectbox("Language", ["en", "es", "fr", "ar"], index=0)

left, right = st.columns([2, 1])

with left:
    st.subheader("Market Watchlist")
    market_rows = []
    for symbol in WATCHLIST:
        data = get_market_data(symbol)
        if "error" in data:
            continue
        market_rows.append(data)

    if market_rows:
        market_df = pd.DataFrame(market_rows)
        market_df = market_df[["symbol", "name", "last", "change_pct", "rsi", "score", "action"]]
        st.dataframe(market_df, use_container_width=True)
    else:
        st.write("No market data available.")

with right:
    st.subheader("Paper Trading")
    if "cash" not in st.session_state:
        st.session_state.cash = 10000.0
    if "positions" not in st.session_state:
        st.session_state.positions = {}

    st.write(f"Cash: ${st.session_state.cash:,.2f}")
    st.write(f"Positions: {len(st.session_state.positions)}")

    trade_symbol = st.text_input("Symbol", value="AAPL")
    trade_side = st.selectbox("Side", ["buy", "sell"])
    trade_qty = st.number_input("Quantity", min_value=1, value=1)

    if st.button("Execute Trade"):
        price = get_market_data(trade_symbol).get("last", 100.0)
        value = price * trade_qty
        if trade_side == "buy":
            if st.session_state.cash < value:
                st.warning("Insufficient cash.")
            else:
                st.session_state.cash -= value
                pos = st.session_state.positions.get(trade_symbol, {"qty": 0.0, "avg": 0.0})
                prev_qty = pos["qty"]
                prev_value = pos["avg"] * prev_qty if prev_qty else 0
                new_total = prev_value + value
                pos["qty"] = prev_qty + trade_qty
                pos["avg"] = new_total / pos["qty"]
                st.session_state.positions[trade_symbol] = pos
                st.success(f"Bought {trade_qty} shares of {trade_symbol}.")
        else:
            pos = st.session_state.positions.get(trade_symbol)
            if not pos or pos["qty"] < trade_qty:
                st.warning("Not enough shares to sell.")
            else:
                st.session_state.cash += value
                pos["qty"] -= trade_qty
                if pos["qty"] <= 0:
                    st.session_state.positions.pop(trade_symbol, None)
                st.success(f"Sold {trade_qty} shares of {trade_symbol}.")

    st.subheader("Goal / Daily Planning")
    task = st.text_input("Task or goal")
    if st.button("Save task") and task:
        if "tasks" not in st.session_state:
            st.session_state.tasks = []
        st.session_state.tasks.append(task)
        st.success("Task saved.")

    if "tasks" in st.session_state and st.session_state.tasks:
        for item in st.session_state.tasks:
            st.write("- " + item)

st.subheader("AI Assistant")
assistant_message = st.text_area("Ask Fizzy", value="Give me a market overview and risk plan.")
if st.button("Send to AI"):
    reply = build_ai_response(assistant_message, language)
    st.write(reply)

st.subheader("Voice")
if st.button("Start Voice Input"):
    st.write("Voice input is available in browser-based Streamlit apps with Web Speech API support. For full browser voice support, use a frontend or a custom HTML app.")

st.subheader("Support / Public Payment")
plan = st.selectbox("Choose plan", ["Starter", "Pro", "Ultimate"])
st.write(f"Selected plan: {plan}")
if st.button("Create payment link"):
    st.write("This is a public-safe demo. In production, connect Stripe or a payment processor here.")

st.caption("Educational analysis only — not financial advice.")
