"""
LLM Client - Unified interface for Gemini and DeepSeek models.
Supports English thinking with Chinese output.
"""
import logging
from abc import ABC, abstractmethod
from typing import Optional

from .config import get_config

logger = logging.getLogger(__name__)

# System prompt for English thinking, Chinese output
SYSTEM_PROMPT = """You are a professional information analyst.
IMPORTANT: You MUST think and reason in English internally,
but your final output MUST be in Simplified Chinese.

Your task is to analyze articles and provide concise, insightful summaries."""

USER_PROMPT_TEMPLATE = """Article Category: {category}
Article URL: {url}
Article Content:
{content}

Please analyze this article and provide:
1. One-sentence core insight (核心观点)
2. Three key takeaways as bullet points (关键要点)

Format your response EXACTLY as:
**核心观点**: [your one-sentence insight in Chinese]

**关键要点**:
- [point 1 in Chinese]
- [point 2 in Chinese]
- [point 3 in Chinese]

Remember: Think in English, output in Chinese."""


class LLMClient(ABC):
    """Abstract base class for LLM clients."""
    
    @abstractmethod
    def summarize(
        self, 
        url: str, 
        content: str, 
        category: str
    ) -> str:
        """
        Generate a summary for an article.
        
        Args:
            url: Article URL
            content: Article content (may be empty for URL-based summarization)
            category: Article category for context
            
        Returns:
            Formatted summary in Chinese
        """
        pass
    
    @abstractmethod
    def summarize_from_url(self, url: str, category: str) -> Optional[str]:
        """
        Generate a summary by directly reading from URL.
        Not all models support this.
        
        Args:
            url: Article URL to read and summarize
            category: Article category for context
            
        Returns:
            Formatted summary in Chinese, or None if not supported/failed
        """
        pass


class GeminiClient(LLMClient):
    """Google Gemini LLM client."""
    
    def __init__(self, api_key: str):
        import google.generativeai as genai
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            system_instruction=SYSTEM_PROMPT,
        )
        logger.info("Initialized Gemini client (gemini-2.0-flash)")
    
    def summarize(self, url: str, content: str, category: str) -> str:
        """Generate summary from content."""
        prompt = USER_PROMPT_TEMPLATE.format(
            category=category,
            url=url,
            content=content[:get_config().max_content_length],
        )
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Gemini summarization failed: {e}")
            raise
    
    def summarize_from_url(self, url: str, category: str) -> Optional[str]:
        """
        Generate summary by letting Gemini read the URL directly.
        Gemini 2.0 Flash supports URL understanding.
        """
        prompt = f"""Article Category: {category}

Please read and analyze the article at this URL: {url}

Then provide:
1. One-sentence core insight (核心观点)
2. Three key takeaways as bullet points (关键要点)

Format your response EXACTLY as:
**核心观点**: [your one-sentence insight in Chinese]

**关键要点**:
- [point 1 in Chinese]
- [point 2 in Chinese]
- [point 3 in Chinese]

Remember: Think in English, output in Chinese."""
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.warning(f"Gemini URL summarization failed for {url}: {e}")
            return None


class DeepSeekClient(LLMClient):
    """DeepSeek LLM client using OpenAI-compatible API."""
    
    def __init__(self, api_key: str, model: str = "deepseek-chat"):
        from openai import OpenAI
        
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com/v1",
        )
        self.model = model
        logger.info(f"Initialized DeepSeek client ({model})")
    
    def summarize(self, url: str, content: str, category: str) -> str:
        """Generate summary from content."""
        prompt = USER_PROMPT_TEMPLATE.format(
            category=category,
            url=url,
            content=content[:get_config().max_content_length],
        )
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=1000,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"DeepSeek summarization failed: {e}")
            raise
    
    def summarize_from_url(self, url: str, category: str) -> Optional[str]:
        """DeepSeek doesn't support direct URL reading."""
        return None


def get_llm_client() -> LLMClient:
    """
    Get the appropriate LLM client based on configuration.
    
    Returns:
        LLMClient instance (GeminiClient or DeepSeekClient)
        
    Raises:
        ValueError: If required API key is not configured
    """
    config = get_config()
    
    if config.llm_provider == "gemini":
        if not config.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required for Gemini provider")
        return GeminiClient(config.gemini_api_key)
    
    elif config.llm_provider == "deepseek":
        if not config.deepseek_api_key:
            raise ValueError("DEEPSEEK_API_KEY is required for DeepSeek provider")
        return DeepSeekClient(config.deepseek_api_key)
    
    else:
        raise ValueError(f"Unknown LLM provider: {config.llm_provider}")
