"""
Report Generator - Generate Markdown daily digest reports.
"""
import logging
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from .config import get_config
from .summarizer import ArticleSummary, SummarySource

logger = logging.getLogger(__name__)


def generate_daily_report(
    summaries: list[ArticleSummary],
    date: Optional[datetime] = None,
) -> str:
    """
    Generate a Markdown daily report from article summaries.
    
    Args:
        summaries: List of ArticleSummary objects
        date: Report date (default: today)
        
    Returns:
        Markdown formatted report string
    """
    if date is None:
        date = datetime.now()
    
    date_str = date.strftime("%Y-%m-%d")
    
    # Group by category
    by_category: dict[str, list[ArticleSummary]] = defaultdict(list)
    for summary in summaries:
        by_category[summary.article.category].append(summary)
    
    # Count sources
    source_counts = {source: 0 for source in SummarySource}
    for summary in summaries:
        source_counts[summary.source] += 1
    
    # Build report
    lines: list[str] = []
    
    # Header
    lines.append(f"# RSS Digest - {date_str}")
    lines.append("")
    lines.append(f"> 本日共收录 **{len(summaries)}** 篇文章，来自 **{len(by_category)}** 个分类。")
    lines.append(">")
    lines.append(f"> 📊 内容获取统计：LLM直读 {source_counts[SummarySource.LLM_DIRECT]} | "
                 f"Jina Reader {source_counts[SummarySource.JINA_READER]} | "
                 f"RSS降级 {source_counts[SummarySource.RSS_FALLBACK]}")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Content by category
    for category in sorted(by_category.keys()):
        articles = by_category[category]
        lines.append(f"## {category}")
        lines.append("")
        
        for summary in articles:
            article = summary.article
            pub_time = article.published.strftime("%Y-%m-%d %H:%M")
            
            lines.append(f"### [{article.title}]({article.url})")
            lines.append(f"> 来源: {article.feed_title} | 发布时间: {pub_time}")
            lines.append("")
            lines.append(summary.summary)
            lines.append("")
            lines.append("---")
            lines.append("")
    
    # Footer
    lines.append(f"*Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (SGT)*")
    
    return "\n".join(lines)


def save_report(
    content: str,
    date: Optional[datetime] = None,
    archives_dir: Optional[str] = None,
) -> Path:
    """
    Save report to archives directory.
    
    Args:
        content: Report content
        date: Report date (default: today)
        archives_dir: Archives directory path (default: from config)
        
    Returns:
        Path to saved report file
    """
    config = get_config()
    
    if date is None:
        date = datetime.now()
    
    if archives_dir is None:
        archives_dir = config.archives_dir
    
    # Ensure directory exists
    dir_path = Path(archives_dir)
    dir_path.mkdir(parents=True, exist_ok=True)
    
    # Save file
    filename = f"{date.strftime('%Y-%m-%d')}.md"
    file_path = dir_path / filename
    
    file_path.write_text(content, encoding="utf-8")
    logger.info(f"Report saved to: {file_path}")
    
    return file_path


def update_readme(
    report_path: Path,
    report_content: str,
    readme_path: Optional[str] = None,
) -> None:
    """
    Update README.md with latest report.
    
    Args:
        report_path: Path to the saved report
        report_content: Report content
        readme_path: README path (default: from config)
    """
    config = get_config()
    
    if readme_path is None:
        readme_path = config.readme_path
    
    readme = Path(readme_path)
    
    # Build README content
    lines: list[str] = []
    lines.append("# Auto-RSS-Digest")
    lines.append("")
    lines.append("🤖 AI-powered RSS digest, automatically generated daily at 07:00 SGT.")
    lines.append("")
    lines.append("## 📰 Latest Digest")
    lines.append("")
    lines.append(f"👉 [View Full Report]({report_path})")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(report_content)
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 📚 Archives")
    lines.append("")
    lines.append("Browse all daily digests in the [`archives/`](./archives) directory.")
    lines.append("")
    lines.append("## ⚙️ Configuration")
    lines.append("")
    lines.append("- **Schedule**: Daily at 07:00 SGT (23:00 UTC)")
    lines.append("- **LLM**: Gemini 2.0 Flash / DeepSeek V3")
    lines.append("- **Subscriptions**: See [`feeds.opml`](./feeds.opml)")
    
    readme.write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"README updated: {readme}")


def generate_empty_report(date: Optional[datetime] = None) -> str:
    """Generate a report for days with no articles."""
    if date is None:
        date = datetime.now()
    
    date_str = date.strftime("%Y-%m-%d")
    
    return f"""# RSS Digest - {date_str}

> 📭 今日无新文章收录。

---

*Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (SGT)*
"""
