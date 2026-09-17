from typing import Dict

# Rough pricing per 1K tokens in USD
MODEL_PRICING: Dict[str, Dict[str, float]] = {
    "deepseek-chat": {"input": 0.00014, "output": 0.00028},
    "deepseek-reasoner": {"input": 0.00055, "output": 0.00219},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-4o": {"input": 0.0025, "output": 0.01},
    "gemini-1.5-flash": {"input": 0.000075, "output": 0.0003},
    "qwen-plus": {"input": 0.0004, "output": 0.0012}
}

def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate cost in USD based on model and token counts."""
    pricing = MODEL_PRICING.get(model.lower())
    if not pricing:
        # Default fallback estimate
        pricing = {"input": 0.0002, "output": 0.0008}
    cost = (input_tokens / 1000.0) * pricing["input"] + (output_tokens / 1000.0) * pricing["output"]
    return round(cost, 6)
