import asyncio
import sys
from pathlib import Path
from typing import List
import click
from loguru import logger
from .config import ConfigManager
from .scraper import StorageScraper
from .exporter import DataExporter

def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    logger.remove()

    level = "DEBUG" if verbose else "INFO"

    # Console logging
    logger.add(
        sys.stderr,
        level=level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
        colorize=True
    )

    # File logging
    logger.add(
        "storage_scraper.log",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        rotation="10 MB",
        retention="7 days"
    )

def read_urls_from_file(file_path: str) -> List[str]:
    """Read URLs from a text file (one per line)."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip()]

        if not urls:
            raise click.ClickException(f"No URLs found in {file_path}")

        logger.info(f"Loaded {len(urls)} URLs from {file_path}")
        return urls

    except FileNotFoundError:
        raise click.ClickException(f"File not found: {file_path}")
    except Exception as e:
        raise click.ClickException(f"Error reading file {file_path}: {e}")

async def run_scraper(urls: List[str], output_file: str, export_format: str):
    """Run the scraper with given URLs."""

    # Load configuration
    config_manager = ConfigManager()
    config = config_manager.get_config()

    logger.info(f"Using Ollama model: {config.ollama_model}")
    logger.info(f"Ollama URL: {config.ollama_base_url}")

    # Run scraper
    async with StorageScraper(config) as scraper:
        results = await scraper.scrape_urls(urls)

    # Export results
    if export_format.lower() == 'csv':
        DataExporter.export_to_csv(results, output_file)
    elif export_format.lower() == 'json':
        DataExporter.export_to_json(results, output_file)
    else:
        raise click.ClickException(f"Unsupported export format: {export_format}")

    # Summary
    successful = sum(1 for r in results if r.success)
    total_units = sum(len(r.units) for r in results if r.success)

    logger.info(f"Scraping complete!")
    logger.info(f"URLs processed: {len(urls)}")
    logger.info(f"Successful: {successful}")
    logger.info(f"Failed: {len(urls) - successful}")
    logger.info(f"Total units found: {total_units}")
    logger.info(f"Results saved to: {output_file}")

@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.pass_context
def cli(ctx, verbose):
    """Storage Scraper - Extract self-storage unit sizes and prices from websites."""
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    setup_logging(verbose)

@cli.command()
@click.option('--url', help='Single URL to scrape')
@click.option('--urls', multiple=True, help='Multiple URLs to scrape')
@click.option('--file', 'url_file', help='File containing URLs (one per line)')
@click.option('--output', '-o', default='output.csv', help='Output file path')
@click.option('--format', 'export_format', default='csv', type=click.Choice(['csv', 'json']), help='Export format')
@click.pass_context
def scrape(ctx, url, urls, url_file, output, export_format):
    """Scrape storage unit data from websites."""

    # Collect URLs from different sources
    all_urls = []

    if url:
        all_urls.append(url)

    if urls:
        all_urls.extend(urls)

    if url_file:
        file_urls = read_urls_from_file(url_file)
        all_urls.extend(file_urls)

    if not all_urls:
        raise click.ClickException("No URLs provided. Use --url, --urls, or --file")

    # Remove duplicates while preserving order
    seen = set()
    unique_urls = []
    for u in all_urls:
        if u not in seen:
            seen.add(u)
            unique_urls.append(u)

    if len(unique_urls) != len(all_urls):
        logger.info(f"Removed {len(all_urls) - len(unique_urls)} duplicate URLs")

    logger.info(f"Starting scrape of {len(unique_urls)} URLs")

    try:
        # Run the async scraper
        asyncio.run(run_scraper(unique_urls, output, export_format))
    except KeyboardInterrupt:
        logger.warning("Scraping interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        sys.exit(1)

@cli.command()
@click.option('--model', help='Set Ollama model name')
@click.option('--base-url', help='Set Ollama base URL')
@click.option('--timeout', type=int, help='Set timeout in seconds')
@click.option('--show', is_flag=True, help='Show current configuration')
def config(model, base_url, timeout, show):
    """Manage configuration settings."""

    config_manager = ConfigManager()

    if show:
        current_config = config_manager.get_config()
        click.echo("Current configuration:")
        click.echo(f"  Ollama model: {current_config.ollama_model}")
        click.echo(f"  Ollama base URL: {current_config.ollama_base_url}")
        click.echo(f"  Timeout: {current_config.timeout_seconds}s")
        click.echo(f"  Max retries: {current_config.max_retries}")
        return

    updates = {}
    if model:
        updates['ollama_model'] = model
    if base_url:
        updates['ollama_base_url'] = base_url
    if timeout:
        updates['timeout_seconds'] = timeout

    if updates:
        config_manager.update_config(**updates)
        click.echo("Configuration updated successfully!")
    else:
        click.echo("No configuration changes specified. Use --show to view current config.")

def main():
    """Main entry point."""
    cli()

if __name__ == '__main__':
    main()
