.PHONY: load test report clean init

init:
	python -m venv .venv
	.venv\Scripts\activate && pip install -r requirements.txt
	New-Item -ItemType File -Force src\__init__.py
	New-Item -ItemType File -Force src\etl\__init__.py
	New-Item -ItemType File -Force tests\__init__.py
	New-Item -ItemType File -Force tests\etl\__init__.py

load:
	python db/init_db.py
	python src/etl/loader.py

ratios:
	python src/analytics/ratios.py
	python src/analytics/cagr.py
	python src/analytics/cashflow_kpis.py
	python src/analytics/merge_ratios.py
	python src/analytics/sector_roce.py

test:
	pytest tests/ --html=reports/pytest_report.html -v

report:
	python src/etl/dq_review.py
	python src/etl/sprint1_verify.py

dashboard:
	streamlit run src/dashboard/app.py

api:
	uvicorn src.api.main:app --port 8000 --reload

clean:
	python -c "import shutil, pathlib; [shutil.rmtree(p) for p in pathlib.Path('.').rglob('__pycache__')]; [p.unlink() for p in pathlib.Path('.').rglob('*.pyc')]"