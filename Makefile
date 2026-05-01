test:
	@uv run pytest -m "not real" \
		--cov src \
		--cov-report term-missing
	@rm .coverage*

prof:
	@.venv/bin/pytest
	@uv run pytest --profile

.PHONY: bench
bench:
	@uv run pytest bench/ -v \
		-o python_files='bench_*.py' \
		--benchmark-only \
		--benchmark-columns=min,mean,max \
		--benchmark-time-unit=s \
		--no-cov

prek:
	@uv run prek run --all-files

prek-install:
	@uv run prek install

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
	@uv run ruff format
	@uv run ruff check --fix
	@uv run ty check
