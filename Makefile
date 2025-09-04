.PHONY: install dev-install test lint format clean build upload

# Install the package
install:
pip install -e .
playwright install chromium

# Install with development dependencies
dev-install:
pip install -e ".[dev]"
playwright install chromium

# Run tests
test:
pytest tests/ -v --cov=storage_scraper --cov-report=html

# Run linting
lint:
flake8 storage_scraper/
mypy storage_scraper/

# Format code
format:
black storage_scraper/ tests/
isort storage_scraper/ tests/

# Clean build artifacts
clean:
rm -rf build/
rm -rf dist/
rm -rf *.egg-info/
rm -rf .pytest_cache/
rm -rf htmlcov/
find . -type d -name __pycache__ -delete
find . -type f -name "*.pyc" -delete

# Build package
build: clean
python -m build

# Upload to PyPI (requires credentials)
upload: build
python -m twine upload dist/*
