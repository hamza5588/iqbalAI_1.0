"""
LLM Factory for dynamic LLM initialization
Supports OpenAI, Groq, and vLLM providers based on environment configuration
"""
import os
import logging
from typing import Optional
from langchain_openai import ChatOpenAI
from app.config import Config

logger = logging.getLogger(__name__)

# Try to import ChatGroq, but don't fail if it's not installed
try:
    from langchain_groq import ChatGroq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    logger.warning("langchain-groq not available. Groq provider will not work.")


def create_llm(
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    timeout: Optional[int] = None,
    model_name: Optional[str] = None,
    api_key: Optional[str] = None,
    provider: Optional[str] = None
) -> ChatOpenAI:
    """
    Create an LLM instance based on provider selection.
    
    Args:
        temperature: Override default temperature (optional)
        max_tokens: Override default max_tokens (optional)
        timeout: Override default timeout (optional)
        model_name: Override default model name (optional)
        api_key: Override default API key (optional, used for OpenAI and Groq)
        provider: Override LLM_PROVIDER setting (optional: 'openai', 'groq', 'vllm')
    
    Returns:
        LLM instance configured for the selected provider (ChatOpenAI or ChatGroq)
        
    Environment Variables:
        LLM_PROVIDER: 'openai', 'groq', or 'vllm' (default: 'openai')
        
        For OpenAI:
            OPENAI_API_KEY: Your OpenAI API key (required if LLM_PROVIDER='openai')
            OPENAI_MODEL: Model name (default: 'gpt-3.5-turbo')
            OPENAI_TEMPERATURE: Temperature (default: 0.7)
            OPENAI_MAX_TOKENS: Max tokens (default: 1024)
            OPENAI_TIMEOUT: Timeout in seconds (default: 60)
            
        For Groq:
            GROQ_API_KEY: Your Groq API key (required if LLM_PROVIDER='groq')
            GROQ_MODEL: Model name (default: 'llama-3.3-70b-versatile')
            GROQ_TEMPERATURE: Temperature (default: 0.7)
            GROQ_MAX_TOKENS: Max tokens (default: 1024)
            GROQ_TIMEOUT: Timeout in seconds (default: 60)
            
        For vLLM:
            VLLM_API_BASE: vLLM API base URL (default: 'http://69.28.92.113:8000/v1')
            VLLM_MODEL: Model name (default: 'Qwen/Qwen2.5-14B-Instruct')
            VLLM_TEMPERATURE: Temperature (default: 0.7)
            VLLM_MAX_TOKENS: Max tokens (default: 1024)
            VLLM_TIMEOUT: Timeout in seconds (default: 600)
    """
    # Use provided provider or fall back to config
    provider = (provider or Config.LLM_PROVIDER).lower()
    
    # Use provided values or fall back to config defaults
    if provider == 'openai':
        # OpenAI configuration
        api_key_to_use = api_key or Config.OPENAI_API_KEY
        if not api_key_to_use:
            raise ValueError(
                "OPENAI_API_KEY environment variable is required when LLM_PROVIDER='openai'. "
                "Please set OPENAI_API_KEY in your environment or .env file."
            )
        
        model = model_name or Config.OPENAI_MODEL
        temp = temperature if temperature is not None else Config.OPENAI_TEMPERATURE
        max_toks = max_tokens if max_tokens is not None else Config.OPENAI_MAX_TOKENS
        time_out = timeout if timeout is not None else Config.OPENAI_TIMEOUT
        
        llm = ChatOpenAI(
            openai_api_key=api_key_to_use,
            model_name="gpt-4o-mini",
            temperature=temp,
            timeout=time_out,
        )
        
        logger.info(f"Initialized OpenAI LLM: model={model}, temperature={temp}, max_tokens={max_toks}")
        
    elif provider == 'groq':
        # Groq configuration
        if not GROQ_AVAILABLE:
            raise ValueError(
                "Groq provider requires langchain-groq package. "
                "Please install it with: pip install langchain-groq"
            )
        
        api_key_to_use = api_key or os.getenv('GROQ_API_KEY', '')
        if not api_key_to_use:
            raise ValueError(
                "GROQ_API_KEY is required when LLM_PROVIDER='groq'. "
                "Please set GROQ_API_KEY in your environment or provide it via api_key parameter."
            )
        
        model = model_name or os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile')
        temp = temperature if temperature is not None else float(os.getenv('GROQ_TEMPERATURE', '0.7'))
        # max_toks = max_tokens if max_tokens is not None else int(os.getenv('GROQ_MAX_TOKENS', '1024'))
        time_out = timeout if timeout is not None else int(os.getenv('GROQ_TIMEOUT', '60'))
        
        llm = ChatGroq(
            groq_api_key=api_key_to_use,
            model_name=model,
            temperature=temp,
            timeout=time_out,
        )
        
        logger.info(f"Initialized Groq LLM: model={model}, temperature={temp}, max_tokens={max_toks}")
        
    elif provider == 'vllm':
        # vLLM configuration (OpenAI-compatible API)
        api_base = Config.VLLM_API_BASE
        model = model_name or Config.VLLM_MODEL
        temp = temperature if temperature is not None else Config.VLLM_TEMPERATURE
        max_toks = max_tokens if max_tokens is not None else Config.VLLM_MAX_TOKENS
        time_out = timeout if timeout is not None else Config.VLLM_TIMEOUT
        
        llm = ChatOpenAI(
            openai_api_key="EMPTY",  # vLLM doesn't require a real API key
            openai_api_base=api_base,
            model_name=model,
            temperature=temp,
            timeout=time_out,
        )
        
        logger.info(f"Initialized vLLM LLM: base={api_base}, model={model}, temperature={temp}, max_tokens={max_toks}")
        
    else:
        raise ValueError(
            f"Invalid LLM_PROVIDER: '{provider}'. Must be 'openai', 'groq', or 'vllm'. "
            f"Current value: {provider or Config.LLM_PROVIDER}"
        )
    
    return llm

