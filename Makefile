test:
	@uv run pytest -m "not real" \
		--cov src \
		--cov-report term-missing
	@rm .coverage

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

clean:
	@rm -rf .pytest_cache
	@rm .coverage

lint:
	@uvx ruff format
	@uvx ruff check --fix
	@uvx ty check
