"""
Lark (Feishu) Sync - Sync article summaries to Lark Bitable.
"""
import logging
import os
from datetime import datetime
from typing import Optional

import httpx

from .summarizer import ArticleSummary

logger = logging.getLogger(__name__)

# Lark API endpoints
LARK_HOST = "https://open.feishu.cn"
TOKEN_URL = f"{LARK_HOST}/open-apis/auth/v3/tenant_access_token/internal"


class LarkClient:
    """Lark (Feishu) API client for Bitable operations."""
    
    def __init__(
        self,
        app_id: Optional[str] = None,
        app_secret: Optional[str] = None,
    ):
        """
        Initialize Lark client.
        
        Args:
            app_id: Lark app ID (default: from LARK_APP_ID env var)
            app_secret: Lark app secret (default: from LARK_APP_SECRET env var)
        """
        self.app_id = app_id or os.getenv("LARK_APP_ID", "")
        self.app_secret = app_secret or os.getenv("LARK_APP_SECRET", "")
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
    
    def _get_access_token(self) -> str:
        """Get or refresh tenant access token."""
        # Check if we have a valid cached token
        if self._access_token and self._token_expires_at:
            if datetime.now() < self._token_expires_at:
                return self._access_token
        
        # Request new token
        with httpx.Client() as client:
            response = client.post(
                TOKEN_URL,
                json={
                    "app_id": self.app_id,
                    "app_secret": self.app_secret,
                },
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()
        
        if data.get("code") != 0:
            raise RuntimeError(f"Failed to get access token: {data.get('msg')}")
        
        self._access_token = data["tenant_access_token"]
        # Token expires in 2 hours, refresh 5 minutes early
        from datetime import timedelta
        self._token_expires_at = datetime.now() + timedelta(seconds=data["expire"] - 300)
        
        return self._access_token
    
    def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs,
    ) -> dict:
        """Make authenticated API request."""
        token = self._get_access_token()
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {token}"
        
        with httpx.Client() as client:
            response = client.request(
                method,
                f"{LARK_HOST}{endpoint}",
                headers=headers,
                timeout=30.0,
                **kwargs,
            )
            response.raise_for_status()
            return response.json()
    
    def get_existing_urls(self, app_token: str, table_id: str) -> set[str]:
        """
        Get all existing article URLs from the table.
        
        Args:
            app_token: Bitable app token
            table_id: Table ID
            
        Returns:
            Set of existing article URLs
        """
        urls: set[str] = set()
        page_token: Optional[str] = None
        
        while True:
            params = {"page_size": 500}
            if page_token:
                params["page_token"] = page_token
            
            endpoint = f"/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records"
            data = self._request("GET", endpoint, params=params)
            
            if data.get("code") != 0:
                logger.error(f"Failed to fetch records: {data.get('msg')}")
                break
            
            records = data.get("data", {}).get("items", [])
            for record in records:
                fields = record.get("fields", {})
                link_field = fields.get("链接")
                if link_field:
                    # 超链接字段格式: {"link": "url", "text": "title"}
                    if isinstance(link_field, dict):
                        url = link_field.get("link", "")
                    else:
                        url = str(link_field)
                    if url:
                        urls.add(url)
            
            # Check for more pages
            page_token = data.get("data", {}).get("page_token")
            if not page_token or not data.get("data", {}).get("has_more"):
                break
        
        logger.info(f"Found {len(urls)} existing records in table")
        return urls
    
    def create_records(
        self,
        app_token: str,
        table_id: str,
        records: list[dict],
    ) -> int:
        """
        Create multiple records in the table.
        
        Args:
            app_token: Bitable app token
            table_id: Table ID
            records: List of record field dicts
            
        Returns:
            Number of records created
        """
        if not records:
            return 0
        
        # Batch create (max 500 per request)
        created = 0
        batch_size = 500
        
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            
            endpoint = f"/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_create"
            data = self._request(
                "POST",
                endpoint,
                json={"records": [{"fields": r} for r in batch]},
            )
            
            if data.get("code") != 0:
                logger.error(f"Failed to create records: {data.get('msg')}")
                continue
            
            created += len(batch)
            logger.info(f"Created {len(batch)} records (batch {i // batch_size + 1})")
        
        return created


def summary_to_record(summary: ArticleSummary) -> dict:
    """
    Convert ArticleSummary to Lark Bitable record format.
    
    Args:
        summary: ArticleSummary object
        
    Returns:
        Dict of field values for Bitable
    """
    article = summary.article
    
    # Convert datetime to Lark timestamp format (milliseconds)
    pub_timestamp = int(article.published.timestamp() * 1000)
    
    return {
        "标题": article.title,
        "摘要": summary.summary,
        "来源": article.feed_title,
        "链接": {"link": article.url, "text": article.title},
        "发布时间": pub_timestamp,
    }


def sync_summaries_to_lark(
    summaries: list[ArticleSummary],
    app_token: Optional[str] = None,
    table_id: Optional[str] = None,
    skip_existing: bool = True,
) -> tuple[int, int]:
    """
    Sync article summaries to Lark Bitable.
    
    Args:
        summaries: List of ArticleSummary objects to sync
        app_token: Bitable app token (default: from LARK_APP_TOKEN env var)
        table_id: Table ID (default: from LARK_TABLE_ID env var)
        skip_existing: Whether to skip articles that already exist in the table
        
    Returns:
        Tuple of (synced_count, skipped_count)
    """
    app_token = app_token or os.getenv("LARK_APP_TOKEN", "")
    table_id = table_id or os.getenv("LARK_TABLE_ID", "")
    
    if not app_token or not table_id:
        logger.warning("Lark sync skipped: LARK_APP_TOKEN or LARK_TABLE_ID not configured")
        return (0, 0)
    
    client = LarkClient()
    
    # Get existing URLs for deduplication
    existing_urls: set[str] = set()
    if skip_existing:
        try:
            existing_urls = client.get_existing_urls(app_token, table_id)
        except Exception as e:
            logger.warning(f"Failed to fetch existing URLs, proceeding without dedup: {e}")
    
    # Filter out existing articles
    new_summaries = [
        s for s in summaries
        if s.article.url not in existing_urls
    ]
    skipped = len(summaries) - len(new_summaries)
    
    if skipped > 0:
        logger.info(f"Skipping {skipped} existing articles")
    
    if not new_summaries:
        logger.info("No new articles to sync")
        return (0, skipped)
    
    # Convert to records and create
    records = [summary_to_record(s) for s in new_summaries]
    
    try:
        created = client.create_records(app_token, table_id, records)
        return (created, skipped)
    except Exception as e:
        logger.error(f"Failed to sync to Lark: {e}")
        return (0, skipped)
