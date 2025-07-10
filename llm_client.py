"""
LLM Client for Pokemon Showdown Bot
Handles communication with Large Language Model APIs for decision making.
"""

import os
import logging
import asyncio
from typing import Optional
from dataclasses import dataclass

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None

try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    AsyncOpenAI = None

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    anthropic = None

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Response from LLM API."""
    content: str
    success: bool
    error_message: Optional[str] = None


class LLMClient:
    """
    Client for communicating with LLM APIs.
    Supports Google Gemini and OpenAI-compatible APIs.
    """
    
    def __init__(self, provider: str = "gemini", model: Optional[str] = None):
        """
        Initialize the LLM client.
        
        Args:
            provider: The LLM provider to use ("gemini", "openai", "anthropic", "ollama", etc.)
            model: Specific model to use (overrides environment variable)
        """
        self.provider = provider
        self.client = None
        self.model = None
        self.requested_model = model  # Store requested model for later use
        
        if provider == "gemini":
            self._initialize_gemini()
        elif provider in ["openai", "anthropic", "ollama", "custom"]:
            self._initialize_openai_compatible(provider)
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")
    
    def _initialize_gemini(self):
        """Initialize Google Gemini client."""
        if not GEMINI_AVAILABLE:
            raise ImportError("google-generativeai package not installed. Since you're using Anthropic, you can ignore this.")
        
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        try:
            genai.configure(api_key=api_key)
            
            # Use requested model or default to Gemini Flash
            model_name = self.requested_model or os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
            self.model = genai.GenerativeModel(model_name)
            
            logger.info(f"Gemini client initialized successfully with model: {model_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}")
            raise
    
    def _initialize_openai_compatible(self, provider: str):
        """Initialize OpenAI-compatible client (OpenAI, Anthropic, Ollama, etc.)."""
        if not OPENAI_AVAILABLE:
            raise ImportError("openai package not installed. Run: pip install openai")
        
        # Get configuration based on provider
        if provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
            model_name = self.requested_model or os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")
        elif provider == "anthropic":
            api_key = os.getenv("ANTHROPIC_API_KEY")
            # Anthropic uses a different API structure, not OpenAI-compatible
            # For now, we'll use the messages endpoint
            base_url = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
            model_name = self.requested_model or os.getenv("ANTHROPIC_MODEL", "claude-3-opus-20240229")
        elif provider == "ollama":
            api_key = "ollama"  # Ollama doesn't need API key
            base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
            model_name = self.requested_model or os.getenv("OLLAMA_MODEL", "llama2")
        else:  # custom
            api_key = os.getenv("LLM_API_KEY")
            base_url = os.getenv("LLM_BASE_URL")
            model_name = self.requested_model or os.getenv("LLM_MODEL")
        
        if not api_key and provider != "ollama":
            raise ValueError(f"{provider.upper()}_API_KEY not found in environment variables")
        
        if not base_url:
            raise ValueError(f"Base URL not configured for {provider}")
        
        try:
            self.client = AsyncOpenAI(
                api_key=api_key,
                base_url=base_url
            )
            self.model = model_name
            
            logger.info(f"{provider} client initialized successfully with model: {model_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize {provider} client: {e}")
            raise
    
    async def get_decision(self, prompt: str, max_tokens: int = 150, temperature: float = 0.3) -> LLMResponse:
        """
        Get a decision from the LLM.
        
        Args:
            prompt: The prompt to send to the LLM
            max_tokens: Maximum tokens in response
            temperature: Creativity/randomness (0.0 = deterministic, 1.0 = very creative)
            
        Returns:
            LLMResponse with the LLM's decision
        """
        if self.provider == "gemini":
            return await self._get_gemini_decision(prompt, max_tokens, temperature)
        elif self.provider in ["openai", "anthropic", "ollama", "custom"]:
            return await self._get_openai_compatible_decision(prompt, max_tokens, temperature)
        else:
            return LLMResponse(
                content="",
                success=False,
                error_message=f"Unsupported provider: {self.provider}"
            )
    
    async def _get_gemini_decision(self, prompt: str, max_tokens: int, temperature: float) -> LLMResponse:
        """Get decision from Gemini API."""
        try:
            # Configure generation parameters
            generation_config = genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature,
                top_p=0.8,
                top_k=40
            )
            
            # Make the API call in a thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.model.generate_content(
                    prompt,
                    generation_config=generation_config
                )
            )
            
            if response.text:
                logger.info(f"Received Gemini response: {response.text[:100]}...")
                return LLMResponse(
                    content=response.text.strip(),
                    success=True
                )
            else:
                logger.warning("Gemini returned empty response")
                return LLMResponse(
                    content="",
                    success=False,
                    error_message="Empty response from Gemini"
                )
                
        except Exception as e:
            logger.error(f"Error calling Gemini API: {e}")
            return LLMResponse(
                content="",
                success=False,
                error_message=str(e)
            )
    
    async def _get_openai_compatible_decision(self, prompt: str, max_tokens: int, temperature: float) -> LLMResponse:
        """Get decision from OpenAI-compatible API."""
        try:
            # Create the chat completion
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a master Pokemon strategist. Analyze the battle state and choose the best action."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=0.8
            )
            
            if response.choices and response.choices[0].message.content:
                content = response.choices[0].message.content.strip()
                logger.info(f"Received {self.provider} response: {content[:100]}...")
                return LLMResponse(
                    content=content,
                    success=True
                )
            else:
                logger.warning(f"{self.provider} returned empty response")
                return LLMResponse(
                    content="",
                    success=False,
                    error_message="Empty response from API"
                )
                
        except Exception as e:
            logger.error(f"Error calling {self.provider} API: {e}")
            return LLMResponse(
                content="",
                success=False,
                error_message=str(e)
            )
    
    def is_available(self) -> bool:
        """Check if the LLM client is properly configured and available."""
        return self.model is not None


class MockLLMClient(LLMClient):
    """
    Mock LLM client for testing without API calls.
    Returns hardcoded responses for development/testing.
    """
    
    def __init__(self):
        """Initialize mock client."""
        self.provider = "mock"
        self.model = "mock-model"
        logger.info("Mock LLM client initialized")
    
    async def get_decision(self, prompt: str, max_tokens: int = 150, temperature: float = 0.3) -> LLMResponse:
        """Return a mock decision based on available moves in prompt."""
        # Simulate API delay
        await asyncio.sleep(0.1)
        
        # Extract available moves from prompt
        available_moves = []
        if "Available moves:" in prompt:
            moves_section = prompt.split("Available moves:")[1].split("\n")[0]
            available_moves = [move.strip() for move in moves_section.split(",")]
        
        # Choose a reasonable move
        chosen_move = "tackle"  # fallback
        if available_moves:
            # Prefer offensive moves
            for move in available_moves:
                move_lower = move.lower()
                if any(keyword in move_lower for keyword in ["attack", "punch", "slash", "beam", "blast", "storm", "fall", "whip"]):
                    chosen_move = move
                    break
            else:
                chosen_move = available_moves[0]  # use first available move
        
        mock_response = f"""action: move
value: {chosen_move}
reasoning: Using available move for battle strategy"""
        
        logger.info(f"Mock LLM response: {mock_response}")
        
        return LLMResponse(
            content=mock_response,
            success=True
        )
    
    def is_available(self) -> bool:
        """Mock client is always available."""
        return True


def create_llm_client(use_mock: bool = False, provider: Optional[str] = None, model: Optional[str] = None) -> LLMClient:
    """
    Factory function to create an LLM client.
    
    Args:
        use_mock: If True, returns a mock client for testing
        provider: LLM provider to use (gemini, openai, anthropic, ollama, custom)
        model: Specific model to use (e.g., 'gpt-4o', 'claude-3-5-sonnet-20241022')
        
    Returns:
        LLMClient instance
    """
    if use_mock:
        return MockLLMClient()
    
    # Get provider from environment if not specified
    if provider is None:
        provider = os.getenv("LLM_PROVIDER", "gemini")
    
    # Try to create real client, fall back to mock if configuration is missing
    try:
        return LLMClient(provider, model)
    except (ValueError, ImportError) as e:
        logger.warning(f"Failed to create {provider} LLM client ({e}), using mock client")
        return MockLLMClient()