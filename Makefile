.PHONY: lint typecheck test check release docs

lint:
	uv run ruff format code/
	uv run ruff check --fix code/

typecheck:
	uv run ty check code/

test:
	uv run pytest code/tests -q

check: lint typecheck test

docs:
	uv run zensical serve

release: check
	@echo "--- Bumping patch version ---"
	@python3 -c "import re; f=open('pyproject.toml'); c=f.read(); f.close(); n=re.sub(r'(version\s*=\s*\x22)(\d+)\.(\d+)\.(\d+)(\x22)', lambda m: f'{m.group(1)}{m.group(2)}.{m.group(3)}.{int(m.group(4))+1}{m.group(5)}', c); open('pyproject.toml','w').write(n)"
	@python3 -c "import re; print('New version:', re.search(r'version\s*=\s*\"(\d+\.\d+\.\d+)\"', open('pyproject.toml').read()).group(1))"
	uv sync
	uv build
	@echo ""
	@read -p "Publish to PyPI? [y/N] " ans; \
	if [ "$$ans" = "y" ] || [ "$$ans" = "Y" ]; then \
		uv publish; \
		echo "Published."; \
	else \
		echo "Skipped publish."; \
	fi
