# Nifty 100 Financial Intelligence Platform

## Quick Start (Windows)

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy config\.env.template .env
python src/etl/loader.py
streamlit run src/dashboard/app.py
```

## Makefile Targets
| Command | Action |
|---|---|
| `make load` | ETL: load all 12 Excel files into nifty100.db |
| `make ratios` | Compute 50+ KPIs into financial_ratios table |
| `make test` | Run full pytest suite |
| `make report` | Generate 92 tearsheet PDFs |
| `make dashboard` | Start Streamlit on localhost:8501 |
| `make api` | Start FastAPI on localhost:8000 |

## Project Structure