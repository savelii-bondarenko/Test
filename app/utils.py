import os

PRICING = {
    "mistral-small-latest": {
        "input": float(os.getenv("INPUT_COST_FOR_1M")) / 1_000_000,
        "output": float(os.getenv("OUTPUT_COST_FOR_1M")) / 1_000_000
    }
}