from setuptools import setup, find_packages

setup(
    name="storage-scraper",
    version="1.0.0",
    description="CLI tool for scraping self-storage unit sizes and prices",
    author="Storage Scraper",
    packages=find_packages(),
    install_requires=[
        "playwright>=1.40.0",
        "loguru>=0.7.0",
        "click>=8.1.0",
        "requests>=2.31.0",
        "beautifulsoup4>=4.12.0",
        "pandas>=2.0.0",
        "pydantic>=2.0.0",
        "aiohttp>=3.9.0",
    ],
    entry_points={
        "console_scripts": [
            "storage-scraper=storage_scraper.cli:main",
        ],
    },
    python_requires=">=3.8",
)
