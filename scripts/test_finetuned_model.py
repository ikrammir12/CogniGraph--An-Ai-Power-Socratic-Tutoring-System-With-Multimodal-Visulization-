"""
Run this BEFORE `streamlit run app/streamlit_app.py` to sanity-check that
your fine-tuned model loads and generates correctly, without needing to
click through the UI to find out.

Usage:
    export COGNIGRAPH_MODEL_PATH=/path/to/your/adapter/or/merged/model
    export COGNIGRAPH_BASE_MODEL=meta-llama/Meta-Llama-3-8B-Instruct   # only needed for adapters
    python scripts/test_finetuned_model.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import CONFIG
from llm.base import ChatMessage


def main():
    print(f"Backend configured: {CONFIG.llm.backend}")
    print(f"Model path: {CONFIG.llm.model_path or '(not set)'}")
    print(f"Base model (used only if this is a LoRA adapter): {CONFIG.llm.base_model_id}")

    if CONFIG.llm.backend != "finetuned":
        print(
            "\nCONFIG.llm.backend is not 'finetuned' — set "
            "COGNIGRAPH_LLM_BACKEND=finetuned (or edit config.py) first."
        )
        sys.exit(1)

    from llm.finetuned_llm import FineTunedLlamaBrain

    print("\nLoading model (this can take a minute, longer on first run)...")
    t0 = time.time()
    brain = FineTunedLlamaBrain()
    brain._ensure_loaded()
    print(f"Loaded in {time.time() - t0:.1f}s as mode='{brain._mode}'")

    system_prompt = CONFIG.socratic.system_prompt.format(
        persona_name=CONFIG.socratic.persona_name,
        min_q=CONFIG.socratic.min_questions_before_answer,
    ) + "\n\nCOURSE CONTEXT:\n[1] (test.pdf, p.1, relevance=0.90)\nOverfitting occurs when a model learns noise in the training data rather than the underlying pattern, resulting in poor generalization to new data."

    messages = [
        ChatMessage(role="system", content=system_prompt),
        ChatMessage(role="user", content="What is overfitting?"),
    ]

    print("\nSending test query: 'What is overfitting?'")
    t0 = time.time()
    response = brain.generate(messages)
    print(f"Generated in {time.time() - t0:.1f}s\n")
    print("--- Model response ---")
    print(response.text)
    print("----------------------")
    print(
        "\nIf this looks like a genuine probing question (not a direct answer), "
        "your fine-tuning worked as intended. Now run: streamlit run app/streamlit_app.py"
    )


if __name__ == "__main__":
    main()
