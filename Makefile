.PHONY: help start backend frontend

help:
	@echo "VizLab Commands"
	@echo "==============="
	@echo "make start    - Start unified VizLab application (in-memory, single-server)"
	@echo "make backend  - Start standalone FastAPI backend (optional)"
	@echo "make frontend - Start Streamlit frontend only"
	@echo ""

start:
	cd frontend && . ../backend/.venv/bin/activate && streamlit run app.py

backend:
	cd backend && . .venv/bin/activate && uvicorn app:app --reload

frontend:
	cd frontend && . ../backend/.venv/bin/activate && streamlit run app.py
