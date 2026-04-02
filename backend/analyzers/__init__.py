from analyzers.prompt_engineering import build_prompt as prompt_engineering_prompt
from analyzers.prompt_caching import build_prompt as prompt_caching_prompt
from analyzers.batching import build_prompt as batching_prompt
from analyzers.tool_use import build_prompt as tool_use_prompt
from analyzers.structured_outputs import build_prompt as structured_outputs_prompt
from analyzers.model_upgrade import build_prompt as model_upgrade_prompt
from analyzers.claude_md_bloat import build_prompt as claude_md_bloat_prompt
from analyzers.mcp_tool_bloat import build_prompt as mcp_tool_bloat_prompt
from analyzers.claudeignore_quality import build_prompt as claudeignore_quality_prompt
from analyzers.commands_quality import build_prompt as commands_quality_prompt
from analyzers.settings_permissions import build_prompt as settings_permissions_prompt
from analyzers.skills_quality import build_prompt as skills_quality_prompt
from analyzers.context_budget import build_prompt as context_budget_prompt
from analyzers.skills_from_history import build_prompt as skills_from_history_prompt
from models import AnalyzerGroup, AnalyzerType, ANALYZER_GROUPS

ANALYZER_PROMPTS = {
    AnalyzerType.PROMPT_ENGINEERING: prompt_engineering_prompt,
    AnalyzerType.PROMPT_CACHING: prompt_caching_prompt,
    AnalyzerType.BATCHING: batching_prompt,
    AnalyzerType.TOOL_USE: tool_use_prompt,
    AnalyzerType.STRUCTURED_OUTPUTS: structured_outputs_prompt,
    AnalyzerType.MODEL_UPGRADE: model_upgrade_prompt,
    AnalyzerType.CLAUDE_MD_BLOAT: claude_md_bloat_prompt,
    AnalyzerType.MCP_TOOL_BLOAT: mcp_tool_bloat_prompt,
    AnalyzerType.CLAUDEIGNORE_QUALITY: claudeignore_quality_prompt,
    AnalyzerType.COMMANDS_QUALITY: commands_quality_prompt,
    AnalyzerType.SETTINGS_PERMISSIONS: settings_permissions_prompt,
    AnalyzerType.SKILLS_QUALITY: skills_quality_prompt,
    AnalyzerType.CONTEXT_BUDGET: context_budget_prompt,
    AnalyzerType.SKILLS_FROM_HISTORY: skills_from_history_prompt,
}

API_ANALYZER_PROMPTS = {
    k: v for k, v in ANALYZER_PROMPTS.items()
    if k in ANALYZER_GROUPS[AnalyzerGroup.API]
}

AGENTIC_ANALYZER_PROMPTS = {
    k: v for k, v in ANALYZER_PROMPTS.items()
    if k in ANALYZER_GROUPS[AnalyzerGroup.AGENTIC]
}
