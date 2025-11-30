from .research_agent import ResearchAgent
from .prompt import (
    SYSTEM_RESEARCH_BASE,
    PLAN_PROMPT,
    SYNTHESIS_PROMPT,
    CRITIQUE_PROMPT,
    MEMORY_SUMMARIZE_PROMPT,
    RESEARCH_PROMPT
)

# 为了向后兼容，也可以导出 prompts 模块本身
from . import prompt as prompts

__all__ = [
    "ResearchAgent",
    "SYSTEM_RESEARCH_BASE",
    "PLAN_PROMPT",
    "SYNTHESIS_PROMPT",
    "CRITIQUE_PROMPT",
    "MEMORY_SUMMARIZE_PROMPT",
    "RESEARCH_PROMPT",
    "prompts",
]