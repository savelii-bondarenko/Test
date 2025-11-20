import os

PRICING = {
    "mistral-tiny": {
        "input": float(os.getenv("INPUT_COST_FOR_1M")) / 1_000_000,
        "output": float(os.getenv("OUTPUT_COST_FOR_1M")) / 1_000_000
    }
}