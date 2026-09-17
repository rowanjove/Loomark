import os
import json
import logging
from typing import Dict, Any, Optional
from openai import AsyncOpenAI
from engine.ai.prompts import PROMPT_TEMPLATES
from engine.ai.cost_tracker import estimate_cost
from engine.ai.cache import AICache

logger = logging.getLogger(__name__)

class AIProviderClient:
    """
    Unified AI client supporting OpenAI-compatible endpoints
    (DeepSeek, OpenAI, Gemini OpenAI proxy, Ollama, LM Studio).
    """
    def __init__(self, api_key: Optional[str] = None,
                 base_url: Optional[str] = None,
                 default_model: str = "deepseek-chat"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "EMPTY")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com/v1")
        self.default_model = default_model
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=30.0
        )

    async def execute_task(self, task_type: str, content: str, title: str = "",
                           model: Optional[str] = None, cache: Optional[AICache] = None,
                           content_hash: Optional[str] = None,
                           extra_params: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Execute an AI task (summary, tags, classification, change_summary)
        with automatic caching and token accounting.
        """
        prompt_info = PROMPT_TEMPLATES.get(task_type)
        if not prompt_info:
            raise ValueError(f"Unknown task type: {task_type}")

        model_name = model or self.default_model
        prompt_version = prompt_info["version"]

        # 1. Check cache first
        if cache and content_hash:
            cached = cache.get(content_hash, prompt_version, model_name)
            if cached:
                return {
                    "task_type": task_type,
                    "model": model_name,
                    "result": json.loads(cached["result_json"]) if isinstance(cached["result_json"], str) else cached["result_json"],
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost": 0.0,
                    "from_cache": True
                }

        # 2. Prepare prompt messages
        # Clip overly long content to protect context window and token usage
        clipped_content = (content or "")[:12000]
        user_prompt = (
            prompt_info["user"]
            .replace("{title}", title or "Untitled")
            .replace("{content}", clipped_content)
        )
        if extra_params:
            for k, v in extra_params.items():
                user_prompt = user_prompt.replace(f"{{{k}}}", str(v)[:12000] if v else "")

        messages = [
            {"role": "system", "content": prompt_info["system"]},
            {"role": "user", "content": user_prompt}
        ]

        # 3. Call model
        try:
            response = await self.client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=0.3
            )
            raw_text = response.choices[0].message.content or ""
            usage = response.usage
            in_tokens = usage.prompt_tokens if usage else len(user_prompt) // 4
            out_tokens = usage.completion_tokens if usage else len(raw_text) // 4
            cost = estimate_cost(model_name, in_tokens, out_tokens)

            # Parse structured output if task expects json or contains json fences
            result_payload = {"text": raw_text}
            clean_str = raw_text.strip()
            if clean_str.startswith("```json"):
                clean_str = clean_str[7:]
            elif clean_str.startswith("```"):
                clean_str = clean_str[3:]
            if clean_str.endswith("```"):
                clean_str = clean_str[:-3]
            clean_str = clean_str.strip()

            is_json_task = task_type in (
                "article_tags_v1", "page_classification_v1", "entity_extraction_v1",
                "selector_repair_v1", "research_decompose_v1", "relevance_scoring_v1",
                "knowledge_gap_v1"
            ) or (clean_str.startswith(("{", "[")) and clean_str.endswith(("}", "]")))

            if is_json_task:
                try:
                    parsed_json = json.loads(clean_str)
                    result_payload["data"] = parsed_json
                except Exception:
                    if task_type in ("article_tags_v1", "page_classification_v1"):
                        result_payload["data"] = raw_text

            # 4. Save to cache
            if cache and content_hash:
                cache.set(content_hash, prompt_version, model_name, result_payload, in_tokens, out_tokens)

            return {
                "task_type": task_type,
                "model": model_name,
                "result": result_payload,
                "input_tokens": in_tokens,
                "output_tokens": out_tokens,
                "cost": cost,
                "from_cache": False
            }
        except Exception as e:
            logger.error(f"AI execution error for task {task_type}: {e}")
            return {
                "task_type": task_type,
                "model": model_name,
                "error": str(e),
                "from_cache": False
            }
