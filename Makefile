# Workflow of the project. Run in the terminal (with the .venv activated):
#   make            -> run the pipeline and the tests
#   make download   -> download player history from steamcharts (~25 min, only needed once)
#   make clean      -> delete the processed files

PYTHON ?= python

all: pipeline test

pipeline:
	$(PYTHON) pipeline.py

download:
	$(PYTHON) fetch_steamcharts.py

test:
	$(PYTHON) -m pytest -q

clean:
	rm -f data/processed/*.csv

.PHONY: all pipeline download test clean
