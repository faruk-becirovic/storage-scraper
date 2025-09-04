"""Data models for Storage Scraper."""

from typing import List, Optional
from pydantic import BaseModel, HttpUrl

class StorageUnit(BaseModel):
    """Model for a storage unit with size and price information."""
    url: str
    size: str
    price: str
    raw_size: Optional[str] = None
    raw_price: Optional[str] = None

class ScrapingResult(BaseModel):
    """Model for scraping results from a single URL."""
    url: str
    success: bool
    units: List[StorageUnit] = []
    error: Optional[str] = None
