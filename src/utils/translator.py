"""
Title translation service supporting multiple APIs (OpenAI, Google Gemini)
"""
import os
from typing import Optional, List, Union
from dataclasses import dataclass
import time
import logging

logger = logging.getLogger(__name__)

# Import APIs with fallback
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI package not available")

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("Google Generative AI package not available")

@dataclass
class TranslationResult:
    """Translation result"""
    original: str
    translated: str
    success: bool
    provider: str = "unknown"
    error: Optional[str] = None

class TitleTranslator:
    """Multi-provider title translator (OpenAI, Google Gemini)"""
    
    def __init__(self, openai_key: Optional[str] = None, gemini_key: Optional[str] = None):
        """Initialize translator with API keys"""
        self.openai_key = openai_key or os.getenv("OPENAI_API_KEY")
        self.gemini_key = gemini_key or os.getenv("GOOGLE_API_KEY")
        
        # Initialize available clients
        self.openai_client = None
        self.gemini_client = None
        
        if self.openai_key and OPENAI_AVAILABLE:
            try:
                self.openai_client = openai.OpenAI(api_key=self.openai_key)
                logger.info("OpenAI translator initialized")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
        
        if self.gemini_key and GEMINI_AVAILABLE:
            try:
                genai.configure(api_key=self.gemini_key)
                self.gemini_client = genai.GenerativeModel('gemini-1.5-flash')
                logger.info("Gemini translator initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {e}")
        
        if not self.openai_client and not self.gemini_client:
            raise ValueError("At least one API key (OpenAI or Gemini) is required")
    
    def translate_title(self, title: str, max_retries: int = 3, prefer_gemini: bool = True) -> TranslationResult:
        """
        Translate a conversation title to Japanese using available APIs
        
        Args:
            title: Original title to translate
            max_retries: Maximum number of retry attempts
            prefer_gemini: Whether to prefer Gemini over OpenAI
            
        Returns:
            TranslationResult with translation and status
        """
        if not title.strip():
            return TranslationResult(title, title, False, "none", "Empty title")
        
        # Skip if already looks like Japanese
        if self._contains_japanese(title):
            return TranslationResult(title, title, True, "none")
        
        # Try preferred API first
        if prefer_gemini and self.gemini_client:
            result = self._translate_with_gemini(title, max_retries)
            if result.success:
                return result
        
        # Fallback to OpenAI if available
        if self.openai_client:
            result = self._translate_with_openai(title, max_retries)
            if result.success:
                return result
        
        # Try non-preferred API if first failed
        if not prefer_gemini and self.gemini_client:
            result = self._translate_with_gemini(title, max_retries)
            if result.success:
                return result
        
        return TranslationResult(title, title, False, "none", "All translation attempts failed")
    
    def _translate_with_openai(self, title: str, max_retries: int) -> TranslationResult:
        """Translate using OpenAI API"""
        prompt = f"""
Please translate the following conversation title to natural Japanese.

Requirements:
- Keep it concise and clear
- Use appropriate Japanese technical terms
- Maintain the original meaning
- Make it suitable for a knowledge management system

Original title: "{title}"

Respond with only the Japanese translation, no explanations.
"""
        
        for attempt in range(max_retries):
            try:
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a professional translator specializing in technical and conversational content."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=100,
                    temperature=0.3
                )
                
                translated = response.choices[0].message.content.strip()
                
                if translated and len(translated) > 0:
                    return TranslationResult(title, translated, True, "openai")
                    
            except Exception as e:
                logger.error(f"OpenAI translation attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
        
        return TranslationResult(title, title, False, "openai", "OpenAI translation failed")
    
    def _translate_with_gemini(self, title: str, max_retries: int) -> TranslationResult:
        """Translate using Google Gemini API"""
        prompt = f"""
Please translate the following conversation title to natural Japanese.

Requirements:
- Keep it concise and clear
- Use appropriate Japanese technical terms
- Maintain the original meaning
- Make it suitable for a knowledge management system

Original title: "{title}"

Respond with only the Japanese translation, no explanations.
"""
        
        for attempt in range(max_retries):
            try:
                response = self.gemini_client.generate_content(prompt)
                translated = response.text.strip()
                
                if translated and len(translated) > 0:
                    return TranslationResult(title, translated, True, "gemini")
                    
            except Exception as e:
                logger.error(f"Gemini translation attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
        
        return TranslationResult(title, title, False, "gemini", "Gemini translation failed")
    
    def translate_batch(self, titles: List[str], delay: float = 0.1) -> List[TranslationResult]:
        """
        Translate multiple titles with rate limiting
        
        Args:
            titles: List of titles to translate
            delay: Delay between API calls
            
        Returns:
            List of TranslationResult objects
        """
        results = []
        
        for i, title in enumerate(titles):
            result = self.translate_title(title)
            results.append(result)
            
            # Rate limiting
            if i < len(titles) - 1:
                time.sleep(delay)
        
        return results
    
    def _contains_japanese(self, text: str) -> bool:
        """Check if text contains Japanese characters"""
        for char in text:
            if '\u3040' <= char <= '\u309F' or '\u30A0' <= char <= '\u30FF' or '\u4E00' <= char <= '\u9FAF':
                return True
        return False

# Convenience function
def translate_conversation_title(title: str, openai_key: Optional[str] = None, gemini_key: Optional[str] = None) -> str:
    """
    Simple function to translate a single title using available APIs
    
    Args:
        title: Title to translate
        openai_key: OpenAI API key (optional, uses env var if not provided)
        gemini_key: Google API key (optional, uses env var if not provided)
        
    Returns:
        Translated title or original if translation fails
    """
    try:
        translator = TitleTranslator(openai_key, gemini_key)
        result = translator.translate_title(title)
        return result.translated if result.success else title
    except Exception as e:
        logger.error(f"Translation failed: {e}")
        return title

def get_available_providers() -> List[str]:
    """Get list of available translation providers"""
    providers = []
    
    if os.getenv("OPENAI_API_KEY") and OPENAI_AVAILABLE:
        providers.append("openai")
    
    if os.getenv("GOOGLE_API_KEY") and GEMINI_AVAILABLE:
        providers.append("gemini")
    
    return providers