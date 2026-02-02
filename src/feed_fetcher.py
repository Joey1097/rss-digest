"""
Feed Fetcher - Fetch RSS feeds and filter articles by time.
"""
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

import feedparser
from dateutil import parser as date_parser

from .opml_parser import Feed

logger = logging.getLogger(__name__)


@dataclass
class Article:
    """Represents a single article from an RSS feed."""
    title: str
    url: str
    published: datetime
    summary: str  # RSS native summary
    feed_title: str
    category: str
    
    def __repr__(self) -> str:
        return f"Article({self.title!r}, feed={self.feed_title!r})"


def fetch_feed(feed: Feed) -> list[Article]:
    """
    Fetch articles from a single RSS feed.
    
    Args:
        feed: Feed object containing the RSS URL
        
    Returns:
        List of Article objects
    """
    try:
        parsed = feedparser.parse(feed.xml_url)
        
        if parsed.bozo and parsed.bozo_exception:
            logger.warning(f"Feed parse warning for {feed.title}: {parsed.bozo_exception}")
        
        articles: list[Article] = []
        
        for entry in parsed.entries:
            article = _parse_entry(entry, feed)
            if article:
                articles.append(article)
        
        return articles
        
    except Exception as e:
        logger.error(f"Failed to fetch feed {feed.title}: {e}")
        return []


def _parse_entry(entry: dict, feed: Feed) -> Optional[Article]:
    """Parse a single feed entry into an Article."""
    try:
        # Get article URL
        url = entry.get("link", "")
        if not url:
            return None
        
        # Get title
        title = entry.get("title", "Untitled")
        
        # Parse publication date - SKIP articles without valid dates
        published = _parse_date(entry)
        if published is None:
            # Skip articles without valid publication date
            # This prevents old articles from being treated as new
            return None
        
        # Sanity check: skip articles with unreasonable dates
        now = datetime.now(timezone.utc)
        one_year_ago = now - timedelta(days=365)
        
        # Skip if date is in the future (bad data)
        if published > now + timedelta(hours=24):
            logger.debug(f"Skipping article with future date: {title}")
            return None
        
        # Skip if date is too old (likely missing/default date)
        if published < one_year_ago:
            logger.debug(f"Skipping article with very old date: {title}")
            return None
        
        # Get summary (RSS native description)
        summary = ""
        if "summary" in entry:
            summary = entry.summary
        elif "description" in entry:
            summary = entry.description
        elif "content" in entry and entry.content:
            summary = entry.content[0].get("value", "")
        
        # Clean HTML from summary (basic cleaning)
        summary = _strip_html(summary)[:500]  # Limit summary length
        
        return Article(
            title=title,
            url=url,
            published=published,
            summary=summary,
            feed_title=feed.title,
            category=feed.category,
        )
        
    except Exception as e:
        logger.warning(f"Failed to parse entry from {feed.title}: {e}")
        return None


def _parse_date(entry: dict) -> Optional[datetime]:
    """Parse publication date from feed entry."""
    # Try different date fields
    for field in ["published", "updated", "created"]:
        if field in entry:
            try:
                # feedparser provides parsed time tuple
                if f"{field}_parsed" in entry and entry[f"{field}_parsed"]:
                    from time import mktime
                    return datetime.fromtimestamp(
                        mktime(entry[f"{field}_parsed"]), 
                        tz=timezone.utc
                    )
                # Fallback to string parsing
                return date_parser.parse(entry[field])
            except (ValueError, TypeError):
                continue
    return None


def _strip_html(text: str) -> str:
    """Remove HTML tags from text (basic implementation)."""
    import re
    # Remove HTML tags
    clean = re.sub(r"<[^>]+>", "", text)
    # Normalize whitespace
    clean = re.sub(r"\s+", " ", clean)
    return clean.strip()


def fetch_recent_articles(
    feeds: list[Feed], 
    hours: int = 24,
    reference_time: Optional[datetime] = None
) -> list[Article]:
    """
    Fetch articles from multiple feeds, filtering by time.
    
    Args:
        feeds: List of Feed objects to fetch
        hours: Time window in hours (default: 24)
        reference_time: Reference time for filtering (default: now)
        
    Returns:
        List of Article objects published within the time window
    """
    if reference_time is None:
        reference_time = datetime.now(timezone.utc)
    
    cutoff_time = reference_time - timedelta(hours=hours)
    
    all_articles: list[Article] = []
    
    for feed in feeds:
        logger.info(f"Fetching: {feed.title}")
        articles = fetch_feed(feed)
        
        # Filter by time
        recent = [
            article for article in articles
            if article.published >= cutoff_time
        ]
        
        logger.info(f"  Found {len(recent)}/{len(articles)} recent articles")
        all_articles.extend(recent)
    
    # Sort by publication time (newest first)
    all_articles.sort(key=lambda a: a.published, reverse=True)
    
    return all_articles
