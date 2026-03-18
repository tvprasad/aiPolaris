.PHONY: install dev graph-viz eval eval-smoke test lint security tf-plan tf-apply release-record audit-log

install:
	pip install -e '.[dev]' && pre-commit install

dev:
	uvicorn api.main:app --reload --port 8000

graph-viz:
	python -c "from agent.graph import graph; print(graph.get_graph().draw_mermaid())" \
	  > docs/architecture/graph.mmd
	@echo "Graph written to docs/architecture/graph.mmd"

eval:
	python eval/run_eval.py --questions eval/golden_questions.json

eval-smoke:
	python eval/run_eval.py --questions eval/golden_questions_smoke.json

ingest-local:
	python -m pipeline.run_ingest --env local

test:
	pytest tests/ \
	  --cov=agent \
	  --cov=pipeline \
	  --cov=api \
	  --cov-report=term-missing \
	  --cov-fail-under=80

lint:
	ruff check . && ruff format --check .

security:
	bandit -c pyproject.toml -r agent/ pipeline/ api/ && pip-audit

tf-plan:
	cd infra/terraform && \
	  terraform workspace select $(env) && \
	  terraform plan -var-file=workspaces/$(env).tfvars

tf-apply:
	cd infra/terraform && \
	  terraform workspace select $(env) && \
	  terraform apply -var-file=workspaces/$(env).tfvars

release-record:
	python scripts/generate_release_record.py

audit-log:
	python scripts/tail_trace_log.py --last 50

check-all: lint security test eval-smoke
	@echo "All gates passed."
