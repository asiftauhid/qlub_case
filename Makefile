PY := .venv/bin/python

.PHONY: setup run test

setup:
	python3 -m venv .venv
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -r requirements.txt
	$(PY) -m ipykernel install --user --name qlub-verano --display-name "Python (qlub_case)"

run:
	$(PY) -m verano.run

test:
	$(PY) -m pytest -q
