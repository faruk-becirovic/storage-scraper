import json
import re
from typing import List, Dict, Any, Optional
import aiohttp
from loguru import logger
from .models import StorageUnit
from .config import Config

class OllamaClient:
    """Client for interacting with Ollama API."""

    def __init__(self, config: Config):
        self.config = config
        self.base_url = config.ollama_base_url.rstrip('/')

    async def extract_storage_data(self, html_content: str, url: str) -> List[StorageUnit]:
        """Extract storage unit data from HTML using Ollama."""

        # Create a focused prompt for the LLM
        prompt = self._create_extraction_prompt(html_content, url)

        try:
            async with aiohttp.ClientSession() as session:
                response = await self._call_ollama(session, prompt)

                if response:
                    return self._parse_ollama_response(response, url)
                else:
                    logger.error(f"No response from Ollama for {url}")
                    return []

        except Exception as e:
            logger.error(f"Error calling Ollama for {url}: {e}")
            return []

    def _create_extraction_prompt(self, html_content: str, url: str) -> str:
        """Create a prompt for extracting storage unit information."""

        # Clean and truncate HTML to avoid token limits
        cleaned_html = self._clean_html_for_llm(html_content)

        prompt = f"""
You are an expert at extracting self-storage unit information from web pages.

Your task: Extract storage unit sizes and prices from the HTML below.

Look for:
- Unit sizes (examples: "5x5", "10x20", "5' x 5'", "50 sq ft", "25 square feet")
- Prices (examples: "$100", "$99/month", "€75", "£50 per month")

Return ONLY a JSON array in this exact format:
[
  {{"size": "5x5", "price": "$100/month"}},
  {{"size": "10x10", "price": "$150/month"}}
]

Rules:
- Return ONLY valid JSON, no other text
- Normalize sizes to simple format (e.g., "5x5" not "5' x 5'")
- Include pricing period if mentioned (e.g., "/month", "/week")
- If no data found, return empty array: []
- Skip duplicate entries

HTML Content from {url}:
{cleaned_html}
"""
        return prompt

    def _clean_html_for_llm(self, html_content: str, max_chars: int = 8000) -> str:
        """Clean and truncate HTML for LLM processing."""
        from bs4 import BeautifulSoup

        try:
            soup = BeautifulSoup(html_content, 'html.parser')

            # Remove script and style elements
            for script in soup(["script", "style", "meta", "link"]):
                script.decompose()

            # Get text content
            text = soup.get_text()

            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)

            # Truncate if too long
            if len(text) > max_chars:
                text = text[:max_chars] + "..."

            return text

        except Exception as e:
            logger.warning(f"Failed to clean HTML: {e}")
            # Fallback: just truncate raw HTML
            return html_content[:max_chars]

    async def _call_ollama(self, session: aiohttp.ClientSession, prompt: str) -> Optional[str]:
        """Make API call to Ollama."""

        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.config.ollama_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,  # Low temperature for consistent extraction
                "top_p": 0.9,
                "num_predict": 2000
            }
        }

        try:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout_seconds)
            async with session.post(url, json=payload, timeout=timeout) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('response', '').strip()
                else:
                    logger.error(f"Ollama API error: {response.status}")
                    return None

        except aiohttp.ClientTimeout:
            logger.error(f"Ollama request timeout after {self.config.timeout_seconds}s")
            return None
        except Exception as e:
            logger.error(f"Ollama request failed: {e}")
            return None

    def _parse_ollama_response(self, response: str, url: str) -> List[StorageUnit]:
        """Parse Ollama response into StorageUnit objects."""

        try:
            # Extract JSON from response (in case there's extra text)
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
            else:
                json_str = response.strip()

            data = json.loads(json_str)

            if not isinstance(data, list):
                logger.error(f"Expected list from Ollama, got {type(data)}")
                return []

            units = []
            for item in data:
                if isinstance(item, dict) and 'size' in item and 'price' in item:
                    unit = StorageUnit(
                        url=url,
                        size=str(item['size']).strip(),
                        price=str(item['price']).strip(),
                        raw_size=str(item.get('raw_size', item['size'])),
                        raw_price=str(item.get('raw_price', item['price']))
                    )
                    units.append(unit)
                else:
                    logger.warning(f"Invalid unit data: {item}")

            logger.info(f"Extracted {len(units)} units from {url}")
            return units

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from Ollama response: {e}")
            logger.debug(f"Raw response: {response}")
            return []
        except Exception as e:
            logger.error(f"Error parsing Ollama response: {e}")
            return []
