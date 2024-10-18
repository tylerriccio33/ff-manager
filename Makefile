test:
	@uv run pytest -m "not real"

prof:
	@.venv/bin/pytest
	@uv run pytest --profile

pre-commit: ## Stages all files
	@git add .
	@uv run pre-commit

deps: ## Analyze dependancies
	uv tool run deptry .

opts:
	@uv run ff-manager print-trade-opts
	@echo "\n"
	@uv run ff-manager print-prof-opts

example:
	@uv run ff-manager find-trades --help

cov:
	@uv run pytest \
		--cov-report term-missing \
		--cov=ff_manager tests/

clean:
	@rm -rf .pytest_cache
	@rm .coverage

lint:
	@uv tool run ruff check --fix
