"""
Langfuse integration for LLM observability.

This module provides a simple integration with Langfuse for tracking LLM API calls,
using LiteLLM's built-in Langfuse integration. It sets up the necessary environment
variables for LiteLLM to automatically send data to Langfuse.
"""

import os
from typing import Optional

# Import Langfuse components
try:
    import langfuse
    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False

from utils.logger import logger
from utils.config import config

def setup_langfuse() -> bool:
    """
    Set up environment variables for Langfuse integration with LiteLLM.

    This function checks for required Langfuse API keys and sets up the necessary
    environment variables for LiteLLM's built-in Langfuse integration. Langfuse
    integration is optional and the application will continue to function without it.

    Required configuration:
    - LANGFUSE_PUBLIC_KEY: Your Langfuse public API key
    - LANGFUSE_SECRET_KEY: Your Langfuse secret API key
    - LANGFUSE_HOST: (Optional) Langfuse API host, defaults to cloud.langfuse.com

    Returns:
        bool: True if setup was successful, False otherwise
    """
    # Check if Langfuse package is installed
    if not LANGFUSE_AVAILABLE:
        logger.warning(
            "Langfuse package not installed. LLM observability will be disabled. "
            "Install with 'pip install langfuse>=2.0.0' to enable observability."
        )
        return False

    # Check for required configuration keys
    missing_keys = []

    # Check for public key
    public_key = config.LANGFUSE_PUBLIC_KEY
    if not public_key:
        missing_keys.append("LANGFUSE_PUBLIC_KEY")

    # Check for secret key
    secret_key = config.LANGFUSE_SECRET_KEY
    if not secret_key:
        missing_keys.append("LANGFUSE_SECRET_KEY")

    # If any keys are missing, log a warning and return False
    if missing_keys:
        logger.warning(
            f"Langfuse integration disabled due to missing configuration: {', '.join(missing_keys)}. "
            f"Add these to your .env file to enable LLM observability. "
            f"Application will continue without observability."
        )
        return False

    try:
        # Get host configuration (optional, has default)
        host = config.LANGFUSE_HOST or "https://cloud.langfuse.com"

        # Set environment variables for LiteLLM's Langfuse integration
        os.environ["LANGFUSE_PUBLIC_KEY"] = public_key
        os.environ["LANGFUSE_SECRET_KEY"] = secret_key
        os.environ["LANGFUSE_HOST"] = host

        logger.info(f"Langfuse environment variables set successfully with host: {host}")
        return True

    except Exception as e:
        # Log warning instead of error since this is optional functionality
        logger.warning(
            f"Failed to set up Langfuse environment variables: {str(e)}. "
            f"Application will continue without LLM observability."
        )
        return False
