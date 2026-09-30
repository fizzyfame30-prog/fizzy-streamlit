# Fizzy Streamlit

A public Streamlit app for:
- trading assistant
- personal AI assistant
- voice recognition and spoken responses
- paper trading simulation
- task planning
- payment / support panel

## Features
- Real-time market watchlist using yfinance
- Technical signal summaries (RSI, moving averages)
- Paper trading simulation
- AI chat assistant using OpenAI if available
- Browser voice recognition and speech output
- Multi-language prompt support
- Stripe-ready payment section

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Notes
- Keep private data in `.env` and never commit it.
- This is educational and not financial advice.
