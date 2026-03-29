from analyzers.prompt_engineering import build_prompt as prompt_engineering_prompt
from analyzers.prompt_caching import build_prompt as prompt_caching_prompt
from analyzers.batching import build_prompt as batching_prompt
from analyzers.tool_use import build_prompt as tool_use_prompt
from analyzers.structured_outputs import build_prompt as structured_outputs_prompt
from models import AnalyzerType

ANALYZER_PROMPTS = {
    AnalyzerType.PROMPT_ENGINEERING: prompt_engineering_prompt,
    AnalyzerType.PROMPT_CACHING: prompt_caching_prompt,
    AnalyzerType.BATCHING: batching_prompt,
    AnalyzerType.TOOL_USE: tool_use_prompt,
    AnalyzerType.STRUCTURED_OUTPUTS: structured_outputs_prompt,
}
