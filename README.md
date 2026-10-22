# 🍩 BakeWise — bakery production planning prototype

A solo Taskforge hackathon MVP: record produced and leftover quantities, forecast next-day demand for 10 bakery products, choose a lean/balanced/buffer strategy, and download a production plan. **Built-in sales are synthetic**, for demonstration only.

## Run locally (Windows / Mac / Linux)

Install Python 3.10+, then from this folder:

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Open the browser URL shown (usually http://localhost:8501).

## Deploy to Streamlit Community Cloud

Push this repository to GitHub. Create an app at https://share.streamlit.io/ and select the repository, `main` branch, and `app.py` entrypoint. Judges can use the public URL without installing software. Cloud local-file changes are **not durable**: demonstration inputs might be lost when the instance restarts or is moved. Persistent multi-user data needs an external database.

## Try Google Colab

In a Colab notebook, clone the repository (after uploading it to GitHub), install requirements, and start Streamlit:

```python
!git clone https://github.com/chfchen/BakeWise.git
%cd BakeWise
!pip install -q -r requirements.txt
!streamlit run app.py --server.port 8501 > /content/streamlit.log 2>&1 &
```

Then use a tunnel (e.g. Cloudflare Quick Tunnel) to access port 8501. Colab sessions and tunnel addresses are temporary. Streamlit Community Cloud is better for judges.

## Files

- `app.py` — interface and local CSV writes
- `forecast.py` — validation, feature engineering, ridge-regression forecasts
- `data/historical_sales.csv` — 128 days of **synthetic** 10-product history
- `tests/test_forecast.py` — basic tests

## Forecast methodology

- Observed sales = produced − leftover (not always full demand).
- Trains one model per product using US federal holiday indicators, weekday, forecast temperature, rain, and a time trend. Uses ridge regression with chronological holdout when 28+ observations exist, or a recent weekday average with less data.
- Early stockouts are excluded when enough non-stockout data exists, since sold units may understate true demand.
- Lean and Safe Buffer quantities adjust predictions by heuristic fractions of held-out MAE. These are **not optimized** for bakery costs; financial decision optimization is future work.

## Limitations and accuracy

- Sample data are synthetic. Do not treat demo holdout scores as evidence of real bakery performance.
- Weather is entered manually. Historical temperature and rain in the demo are simulated.
- The simple local save file is convenient for localhost demo but not robust for cloud or concurrent users.
- Scheduling, email, mobile app, authentication, POS integration, and a real-time weather API are **not implemented**.
- This is intended to demonstrate a real workflow; bakery operators should validate recommendations against real records before use.

## AI assistance

ChatGPT assisted with project planning, writing and initial code generation. Review, test and adapt all software prior to submission.
