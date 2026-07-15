"""External tools: LLM factory, Tavily search, and web scraping."""
import logging
from functools import lru_cache
from typing import Optional

from langchain_community.document_loaders import WebBaseLoader
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_tavily import TavilySearch

from .config import get_settings

logger = logging.getLogger(__name__)


@lru_cache
def get_llm() -> ChatGoogleGenerativeAI:
    settings = get_settings()
    return ChatGoogleGenerativeAI(model=settings.model_name)


@lru_cache
def get_search_tool() -> TavilySearch:
    settings = get_settings()
    return TavilySearch(max_results=settings.max_search_results)


def scrape_url(url: str) -> Optional[str]:
    """Scrape a page and return its text (truncated), or None on failure."""
    settings = get_settings()
    try:
        docs = WebBaseLoader(url).load()
        return docs[0].page_content[: settings.scrape_char_limit]
    except Exception as e:
        logger.warning("Scraping failed for %s: %s", url, e)
        return None
