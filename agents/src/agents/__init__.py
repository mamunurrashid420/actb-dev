"""Multi-agent system for actBI."""

from agents.abstract_agent import BaseAgent  # deprecated — use AgentBuilder
from agents.base import AgentBuilder
from agents.data_explorer import DataExplorer
from agents.intent_classifier import IntentClassifier
from agents.lib.utils import create_agent_context
from agents.llm import LLMClient, disable_cache, enable_cache
from agents.viz_designer import VisualizationDesigner

__all__ = [
    # New builder pattern (preferred for new agents)
    "AgentBuilder",
    "create_agent_context",
    # Legacy base (deprecated — will be removed)
    "BaseAgent",
    # Agents
    "VisualizationDesigner",
    "DataExplorer",
    "IntentClassifier",
    # LLM utilities
    "LLMClient",
    "enable_cache",
    "disable_cache",
]
