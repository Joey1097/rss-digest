"""
OPML Parser - Parse OPML files to extract RSS feeds and categories.
"""
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET


@dataclass
class Feed:
    """Represents a single RSS feed subscription."""
    title: str
    xml_url: str
    html_url: str
    category: str
    
    def __repr__(self) -> str:
        return f"Feed({self.title!r}, category={self.category!r})"


def parse_opml(file_path: str | Path) -> list[Feed]:
    """
    Parse an OPML file and extract all RSS feeds with their categories.
    
    Args:
        file_path: Path to the OPML file
        
    Returns:
        List of Feed objects
        
    Raises:
        FileNotFoundError: If the OPML file doesn't exist
        ET.ParseError: If the OPML file is malformed
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"OPML file not found: {path}")
    
    tree = ET.parse(path)
    root = tree.getroot()
    
    feeds: list[Feed] = []
    body = root.find("body")
    
    if body is None:
        return feeds
    
    # Process all outline elements
    _process_outlines(body, "", feeds)
    
    return feeds


def _process_outlines(
    parent: ET.Element, 
    category: str, 
    feeds: list[Feed]
) -> None:
    """
    Recursively process outline elements to extract feeds.
    
    Args:
        parent: Parent XML element
        category: Current category name (from parent outline)
        feeds: List to append found feeds to
    """
    for outline in parent.findall("outline"):
        xml_url = outline.get("xmlUrl")
        
        if xml_url:
            # This is a feed entry
            feed = Feed(
                title=outline.get("text", outline.get("title", "Unknown")),
                xml_url=xml_url,
                html_url=outline.get("htmlUrl", ""),
                category=category or "Uncategorized",
            )
            feeds.append(feed)
        else:
            # This is a category folder, process children
            folder_name = outline.get("text", outline.get("title", ""))
            _process_outlines(outline, folder_name, feeds)


def get_categories(feeds: list[Feed]) -> list[str]:
    """Get unique categories from a list of feeds, preserving order."""
    seen: set[str] = set()
    categories: list[str] = []
    
    for feed in feeds:
        if feed.category not in seen:
            seen.add(feed.category)
            categories.append(feed.category)
    
    return categories
