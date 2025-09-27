PYTHON ?= python3
VENV ?= .venv
PIP := $(VENV)/bin/pip
UVICORN := $(VENV)/bin/uvicorn
PORT ?= 8000
PYTEST := $(VENV)/bin/pytest

.PHONY: setup run dev test clean

setup:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install -U pip
	$(PIP) install -r requirements.txt

run:
	$(UVICORN) app.main:app --reload --port $(PORT)

run8888:
	$(UVICORN) app.main:app --reload --port 8888

dev: setup run

test:
	DATABASE_URL=sqlite:///./test.db PYTHONPATH=. $(PYTEST)

clean:
	rm -f test.db dev.db
	find . -name "__pycache__" -type d -prune -exec rm -rf {} +
	find . -name "*.pyc" -delete
