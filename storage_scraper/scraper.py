import asyncio
from typing import List, Optional
from playwright.async_api import async_playwright, Browser, Page
from loguru import logger
from .models import ScrapingResult, StorageUnit
from .ollama_client import OllamaClient
from .config import Config

class StorageScraper:
    """Main scraper class using Playwright and Ollama."""

    def __init__(self, config: Config):
        self.config = config
        self.ollama_client = OllamaClient(config)
        self.browser: Optional[Browser] = None

    async def __aenter__(self):
        """Async context manager entry."""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.browser:
            await self.browser.close()
        await self.playwright.stop()

    async def scrape_urls(self, urls: List[str]) -> List[ScrapingResult]:
        """Scrape multiple URLs and return results."""

        if not self.browser:
            raise RuntimeError("Scraper not properly initialized. Use async with statement.")

        logger.info(f"Starting to scrape {len(urls)} URLs")
        results = []

        # Process URLs concurrently (but limit concurrency)
        semaphore = asyncio.Semaphore(3)  # Max 3 concurrent requests
        tasks = [self._scrape_single_url(semaphore, url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions in results
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error scraping {urls[i]}: {result}")
                final_results.append(ScrapingResult(
                    url=urls[i],
                    success=False,
                    error=str(result)
                ))
            else:
                final_results.append(result)

        successful = sum(1 for r in final_results if r.success)
        logger.info(f"Scraping completed: {successful}/{len(urls)} successful")

        return final_results

    async def _scrape_single_url(self, semaphore: asyncio.Semaphore, url: str) -> ScrapingResult:
        """Scrape a single URL with semaphore for concurrency control."""

        async with semaphore:
            return await self._scrape_url(url)

    async def _scrape_url(self, url: str) -> ScrapingResult:
        """Scrape a single URL and return structured data."""

        logger.info(f"Scraping {url}")

        try:
            # Create a new page for this URL
            page = await self.browser.new_page()

            # Set user agent and other headers
            await page.set_extra_http_headers({
                'User-Agent': self.config.user_agent
            })

            # Navigate to the page
            response = await page.goto(
                url,
                wait_until='networkidle',
                timeout=self.config.timeout_seconds * 1000
            )

            if not response or response.status >= 400:
                error_msg = f"Failed to load page: HTTP {response.status if response else 'No response'}"
                logger.error(f"{url}: {error_msg}")
                await page.close()
                return ScrapingResult(url=url, success=False, error=error_msg)

            # Wait a bit for dynamic content
            await page.wait_for_timeout(2000)

            # Get page content
            html_content = await page.content()
            await page.close()

            # Extract data using Ollama
            units = await self.ollama_client.extract_storage_data(html_content, url)

            if units:
                logger.success(f"Found {len(units)} storage units at {url}")
                return ScrapingResult(url=url, success=True, units=units)
            else:
                logger.warning(f"No storage units found at {url}")
                return ScrapingResult(url=url, success=True, units=[])

        except Exception as e:
            error_msg = f"Scraping error: {str(e)}"
            logger.error(f"{url}: {error_msg}")
            return ScrapingResult(url=url, success=False, error=error_msg)
