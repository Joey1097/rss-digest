"""
Summarizer - Coordinate content fetching and LLM summarization.
Implements fallback strategies: LLM Direct -> Jina Reader -> RSS Summary
"""
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import httpx

from .config import get_config
from .feed_fetcher import Article
from .llm_client import LLMClient

logger = logging.getLogger(__name__)


class SummarySource(Enum):
    """Source of the summary content."""
    LLM_DIRECT = "llm_direct"      # LLM read URL directly
    JINA_READER = "jina_reader"    # Jina Reader API
    RSS_FALLBACK = "rss_fallback"  # RSS native summary


@dataclass
class ArticleSummary:
    """Article with its AI-generated summary."""
    article: Article
    summary: str
    source: SummarySource
    
    def __repr__(self) -> str:
        return f"ArticleSummary({self.article.title!r}, source={self.source.value})"


async def fetch_content_jina(url: str, timeout: float = 30.0) -> Optional[str]:
    """
    Fetch article content using Jina Reader API.
    
    Args:
        url: Article URL to fetch
        timeout: Request timeout in seconds
        
    Returns:
        Article content as markdown, or None if failed
    """
    jina_url = f"https://r.jina.ai/{url}"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                jina_url,
                timeout=timeout,
                headers={"Accept": "text/markdown"},
            )
            response.raise_for_status()
            return response.text
    except Exception as e:
        logger.warning(f"Jina Reader failed for {url}: {e}")
        return None


def fetch_content_jina_sync(url: str, timeout: float = 30.0) -> Optional[str]:
    """Synchronous version of fetch_content_jina."""
    jina_url = f"https://r.jina.ai/{url}"
    
    try:
        with httpx.Client() as client:
            response = client.get(
                jina_url,
                timeout=timeout,
                headers={"Accept": "text/markdown"},
            )
            response.raise_for_status()
            return response.text
    except Exception as e:
        logger.warning(f"Jina Reader failed for {url}: {e}")
        return None


def summarize_article(
    article: Article, 
    llm: LLMClient,
    delay_seconds: Optional[float] = None,
) -> ArticleSummary:
    """
    Generate summary for an article using fallback strategies.
    
    Strategy order:
    1. LLM direct URL reading (Gemini only)
    2. Jina Reader API + LLM summarization
    3. RSS native summary + LLM summarization
    
    Args:
        article: Article to summarize
        llm: LLM client instance
        delay_seconds: Delay between API calls (default: from config)
        
    Returns:
        ArticleSummary with the generated summary
    """
    config = get_config()
    if delay_seconds is None:
        delay_seconds = config.api_delay_seconds
    
    logger.info(f"Summarizing: {article.title}")
    
    # Strategy 1: LLM direct URL reading
    try:
        summary = llm.summarize_from_url(article.url, article.category)
        if summary:
            logger.info(f"  ✓ LLM direct read successful")
            time.sleep(delay_seconds)
            return ArticleSummary(
                article=article,
                summary=summary,
                source=SummarySource.LLM_DIRECT,
            )
    except Exception as e:
        logger.warning(f"  ✗ LLM direct read failed: {e}")
    
    # Strategy 2: Jina Reader + LLM
    try:
        content = fetch_content_jina_sync(article.url)
        if content:
            summary = llm.summarize(article.url, content, article.category)
            logger.info(f"  ✓ Jina Reader + LLM successful")
            time.sleep(delay_seconds)
            return ArticleSummary(
                article=article,
                summary=summary,
                source=SummarySource.JINA_READER,
            )
    except Exception as e:
        logger.warning(f"  ✗ Jina Reader + LLM failed: {e}")
    
    # Strategy 3: RSS summary fallback
    try:
        if article.summary:
            summary = llm.summarize(article.url, article.summary, article.category)
            logger.info(f"  ⚠ Using RSS summary fallback")
            time.sleep(delay_seconds)
            return ArticleSummary(
                article=article,
                summary=summary,
                source=SummarySource.RSS_FALLBACK,
            )
    except Exception as e:
        logger.error(f"  ✗ RSS fallback failed: {e}")
    
    # Final fallback: just use RSS summary as-is
    logger.warning(f"  ⚠ All strategies failed, using raw RSS summary")
    return ArticleSummary(
        article=article,
        summary=f"**核心观点**: {article.summary[:200] or '无法获取摘要'}\n\n**关键要点**:\n- 原文需要人工查看",
        source=SummarySource.RSS_FALLBACK,
    )


def summarize_articles(
    articles: list[Article],
    llm: LLMClient,
) -> list[ArticleSummary]:
    """
    Summarize multiple articles.
    
    Args:
        articles: List of articles to summarize
        llm: LLM client instance
        
    Returns:
        List of ArticleSummary objects
    """
    summaries: list[ArticleSummary] = []
    
    for i, article in enumerate(articles, 1):
        logger.info(f"[{i}/{len(articles)}] Processing...")
        summary = summarize_article(article, llm)
        summaries.append(summary)
    
    return summaries
