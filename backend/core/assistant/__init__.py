"""
Assistant Module
Handles AI assistant operations
"""

from .openai import OpenAIAssistantManager, AssistantConfig
from .chat import ChatInterface

__all__ = [
    "OpenAIAssistantManager",
    "AssistantConfig",
    "ChatInterface"
]