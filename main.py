#!/usr/bin/env python3
"""
Auto-RSS-Digest - Main entry point.

This script orchestrates the entire RSS digest generation process:
1. Load configuration
2. Parse OPML subscriptions
3. Fetch recent articles (last 24 hours)
4. Generate AI summaries for each article
5. Create daily Markdown report
6. Update README with latest digest
"""
import logging
import sys
from datetime import datetime
from pathlib import Path

# Load .env file if exists (for local development)
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

from src.config import get_config
from src.opml_parser import parse_opml, get_categories
from src.feed_fetcher import fetch_recent_articles
from src.llm_client import get_llm_client
from src.summarizer import summarize_articles, SummarySource
from src.report_generator import (
    generate_daily_report,
    generate_empty_report,
    save_report,
    update_readme,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def main() -> int:
    """
    Main entry point for the RSS digest generator.
    
    Returns:
        Exit code (0 for success, 1 for error)
    """
    logger.info("=" * 60)
    logger.info("Auto-RSS-Digest Starting")
    logger.info("=" * 60)
    
    # Step 1: Load and validate configuration
    logger.info("Step 1: Loading configuration...")
    config = get_config()
    
    errors = config.validate()
    if errors:
        for error in errors:
            logger.error(f"Config error: {error}")
        return 1
    
    logger.info(f"  LLM Provider: {config.llm_provider}")
    logger.info(f"  Time Window: {config.time_window_hours} hours")
    logger.info(f"  Timezone: {config.timezone}")
    
    # Step 2: Parse OPML
    logger.info("Step 2: Parsing OPML subscriptions...")
    try:
        feeds = parse_opml(config.opml_path)
        categories = get_categories(feeds)
        logger.info(f"  Found {len(feeds)} feeds in {len(categories)} categories")
    except Exception as e:
        logger.error(f"Failed to parse OPML: {e}")
        return 1
    
    # Step 3: Fetch recent articles
    logger.info("Step 3: Fetching recent articles...")
    articles = fetch_recent_articles(feeds, hours=config.time_window_hours)
    logger.info(f"  Found {len(articles)} articles in the last {config.time_window_hours} hours")
    
    if not articles:
        logger.info("No recent articles found. Generating empty report...")
        report_content = generate_empty_report()
        report_path = save_report(report_content)
        update_readme(report_path, report_content)
        logger.info("Empty report generated successfully.")
        return 0
    
    # Step 4: Initialize LLM client
    logger.info("Step 4: Initializing LLM client...")
    try:
        llm = get_llm_client()
    except Exception as e:
        logger.error(f"Failed to initialize LLM client: {e}")
        return 1
    
    # Step 5: Generate summaries
    logger.info("Step 5: Generating AI summaries...")
    summaries = summarize_articles(articles, llm)
    
    # Log statistics
    source_stats = {source: 0 for source in SummarySource}
    for summary in summaries:
        source_stats[summary.source] += 1
    
    logger.info("  Summary statistics:")
    logger.info(f"    LLM Direct: {source_stats[SummarySource.LLM_DIRECT]}")
    logger.info(f"    Jina Reader: {source_stats[SummarySource.JINA_READER]}")
    logger.info(f"    RSS Fallback: {source_stats[SummarySource.RSS_FALLBACK]}")
    
    # Step 6: Generate report
    logger.info("Step 6: Generating daily report...")
    today = datetime.now()
    report_content = generate_daily_report(summaries, today)
    
    # Step 7: Save report
    logger.info("Step 7: Saving report...")
    report_path = save_report(report_content, today)
    
    # Step 8: Update README
    logger.info("Step 8: Updating README...")
    update_readme(report_path, report_content)
    
    # Step 9: Sync to Lark (optional)
    if config.lark_app_token and config.lark_table_id:
        logger.info("Step 9: Syncing to Lark...")
        try:
            from src.lark_sync import sync_summaries_to_lark
            synced, skipped = sync_summaries_to_lark(summaries)
            logger.info(f"  Synced: {synced}, Skipped (existing): {skipped}")
        except Exception as e:
            logger.error(f"Failed to sync to Lark: {e}")
    
    # Done!
    logger.info("=" * 60)
    logger.info("Auto-RSS-Digest Completed Successfully!")
    logger.info(f"  Total articles: {len(articles)}")
    logger.info(f"  Report saved: {report_path}")
    logger.info("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
