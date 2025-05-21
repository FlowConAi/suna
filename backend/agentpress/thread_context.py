"""
Thread context utilities for AgentPress.

This module provides context variables and utilities for tracking
the current thread and user IDs across async contexts.
"""

from contextvars import ContextVar
from typing import Optional

# Context variables to track current thread and user IDs
current_thread_id: ContextVar[Optional[str]] = ContextVar('current_thread_id', default=None)
current_user_id: ContextVar[Optional[str]] = ContextVar('current_user_id', default=None)

def set_current_thread_id(thread_id: Optional[str]) -> None:
    """Set the current thread ID in the context."""
    current_thread_id.set(thread_id)

def get_current_thread_id() -> Optional[str]:
    """Get the current thread ID from the context."""
    return current_thread_id.get()

def set_current_user_id(user_id: Optional[str]) -> None:
    """Set the current user ID in the context."""
    current_user_id.set(user_id)

def get_current_user_id() -> Optional[str]:
    """Get the current user ID from the context."""
    return current_user_id.get()
