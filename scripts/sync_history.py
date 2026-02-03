#!/usr/bin/env python3
"""
Sync historical digest files to Lark Bitable.

This script parses existing Markdown digest files from the archives directory
and syncs them to Lark Bitable, with deduplication support.

Usage:
    python scripts/sync_history.py [--archives-dir ARCHIVES_DIR]
"""
import argparse
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from src.lark_sync import LarkClient, sync_summaries_to_lark
from src.summarizer import ArticleSummary, SummarySource
from src.feed_fetcher import Article

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def parse_digest_file(filepath: Path) -> list[ArticleSummary]:
    """
    Parse a Markdown digest file and extract article summaries.
    
    Args:
        filepath: Path to the digest .md file
        
    Returns:
        List of ArticleSummary objects
    """
    content = filepath.read_text(encoding="utf-8")
    summaries: list[ArticleSummary] = []
    
    # Extract date from filename (e.g., 2026-02-03.md)
    date_match = re.search(r"(\d{4}-\d{2}-\d{2})", filepath.name)
    file_date = date_match.group(1) if date_match else datetime.now().strftime("%Y-%m-%d")
    
    # Pattern to match article sections
    # ### [Title](URL)
    # > 来源: Feed | 发布时间: YYYY-MM-DD HH:MM
    # 
    # Summary content...
    article_pattern = re.compile(
        r'### \[(.+?)\]\((.+?)\)\s*\n'
        r'> 来源: (.+?) \| 发布时间: (\d{4}-\d{2}-\d{2} \d{2}:\d{2})\s*\n'
        r'\n'
        r'(.*?)(?=\n---|\Z)',
        re.DOTALL
    )
    
    # Get current category (## Category)
    current_category = "Uncategorized"
    
    # Split by category headers
    category_pattern = re.compile(r'^## (.+)$', re.MULTILINE)
    categories = category_pattern.split(content)
    
    # Process each category section
    for i in range(1, len(categories), 2):
        if i + 1 < len(categories):
            current_category = categories[i].strip()
            section_content = categories[i + 1]
            
            # Find all articles in this section
            for match in article_pattern.finditer(section_content):
                title = match.group(1).strip()
                url = match.group(2).strip()
                feed_title = match.group(3).strip()
                pub_time_str = match.group(4).strip()
                summary_text = match.group(5).strip()
                
                # Parse publication time
                try:
                    published = datetime.strptime(pub_time_str, "%Y-%m-%d %H:%M")
                except ValueError:
                    published = datetime.strptime(f"{file_date} 00:00", "%Y-%m-%d %H:%M")
                
                # Determine summary source from content statistics in header
                # Default to JINA_READER as most common
                source = SummarySource.JINA_READER
                
                article = Article(
                    title=title,
                    url=url,
                    published=published,
                    summary="",  # Original RSS summary not available
                    feed_title=feed_title,
                    category=current_category,
                )
                
                article_summary = ArticleSummary(
                    article=article,
                    summary=summary_text,
                    source=source,
                )
                summaries.append(article_summary)
    
    return summaries


def sync_all_archives(
    archives_dir: Path,
    app_token: str,
    table_id: str,
) -> tuple[int, int]:
    """
    Sync all digest files from archives directory to Lark.
    
    Args:
        archives_dir: Path to archives directory
        app_token: Bitable app token
        table_id: Bitable table ID
        
    Returns:
        Tuple of (total_synced, total_skipped)
    """
    total_synced = 0
    total_skipped = 0
    
    # Find all .md files
    md_files = sorted(archives_dir.glob("*.md"))
    
    logger.info(f"Found {len(md_files)} digest files in {archives_dir}")
    
    for filepath in md_files:
        if filepath.name.startswith("."):
            continue
            
        logger.info(f"Processing: {filepath.name}")
        
        try:
            summaries = parse_digest_file(filepath)
            logger.info(f"  Parsed {len(summaries)} articles")
            
            if summaries:
                synced, skipped = sync_summaries_to_lark(
                    summaries,
                    app_token=app_token,
                    table_id=table_id,
                    skip_existing=True,
                )
                total_synced += synced
                total_skipped += skipped
                logger.info(f"  Synced: {synced}, Skipped: {skipped}")
        except Exception as e:
            logger.error(f"  Failed to process {filepath.name}: {e}")
    
    return total_synced, total_skipped


def main():
    parser = argparse.ArgumentParser(
        description="Sync historical digest files to Lark Bitable"
    )
    parser.add_argument(
        "--archives-dir",
        type=Path,
        default=Path(__file__).parent.parent / "archives",
        help="Path to archives directory",
    )
    args = parser.parse_args()
    
    # Get Lark credentials from environment
    app_token = os.getenv("LARK_APP_TOKEN", "")
    table_id = os.getenv("LARK_TABLE_ID", "")
    
    if not app_token or not table_id:
        logger.error("LARK_APP_TOKEN and LARK_TABLE_ID environment variables are required")
        sys.exit(1)
    
    logger.info("=" * 60)
    logger.info("Historical Digest Sync Starting")
    logger.info("=" * 60)
    
    synced, skipped = sync_all_archives(args.archives_dir, app_token, table_id)
    
    logger.info("=" * 60)
    logger.info("Sync Completed!")
    logger.info(f"  Total synced: {synced}")
    logger.info(f"  Total skipped: {skipped}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
