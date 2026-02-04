.PHONY: help backend frontend

help:
	@echo "VizLab Commands"
	@echo "==============="
	@echo "make backend  - Start backend server (cd backend && source .venv/bin/activate && uvicorn app:app --reload)"
	@echo "make frontend - Start frontend server (cd frontend && source .venv/bin/activate && streamlit run app.py)"
	@echo ""

backend:
	cd backend && . .venv/bin/activate && uvicorn app:app --reload

frontend:
	cd frontend && . ../backend/.venv/bin/activate && streamlit run app.py
