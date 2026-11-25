"""
Scans a fine-tuning output folder (the kind that contains adapter/,
checkpoints/, environments/, evaluations/ subfolders) and reports every
loadable model artifact it finds, so you don't have to guess which path to
put in COGNIGRAPH_MODEL_PATH.

Usage:
    python scripts/inspect_model_folder.py /path/to/your/finetune_output
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def _describe_adapter(path: Path) -> dict:
    cfg = json.loads((path / "adapter_config.json").read_text())
    weight_file = None
    for name in ("adapter_model.safetensors", "adapter_model.bin"):
        if (path / name).exists():
            weight_file = name
            break
    return {
        "kind": "LoRA adapter",
        "path": str(path),
        "base_model": cfg.get("base_model_name_or_path", "(not recorded)"),
        "weight_file": weight_file or "MISSING — this adapter dir has no weights!",
        "has_own_tokenizer": (path / "tokenizer_config.json").exists(),
    }


def _describe_merged(path: Path) -> dict:
    cfg = json.loads((path / "config.json").read_text())
    weight_files = list(path.glob("*.safetensors")) + list(path.glob("pytorch_model*.bin"))
    return {
        "kind": "Merged full model",
        "path": str(path),
        "model_type": cfg.get("model_type", "(not recorded)"),
        "weight_files_found": len(weight_files),
        "has_own_tokenizer": (path / "tokenizer_config.json").exists(),
    }


def scan(root: Path) -> list[dict]:
    found = []
    for adapter_cfg in root.rglob("adapter_config.json"):
        found.append(_describe_adapter(adapter_cfg.parent))
    for config_json in root.rglob("config.json"):
        # Skip anything that's actually a LoRA adapter dir's own config.json
        # (adapters don't usually ship one, but be defensive) and skip
        # tokenizer-only dirs that happen to have a config.json.
        if (config_json.parent / "adapter_config.json").exists():
            continue
        if not any(config_json.parent.glob("*.safetensors")) and not any(
            config_json.parent.glob("pytorch_model*.bin")
        ):
            continue
        found.append(_describe_merged(config_json.parent))
    return found


def main():
    if len(sys.argv) != 2:
        print("Usage: python scripts/inspect_model_folder.py /path/to/finetune_output")
        sys.exit(1)

    root = Path(sys.argv[1])
    if not root.exists():
        print(f"Path does not exist: {root}")
        sys.exit(1)

    results = scan(root)
    if not results:
        print(
            f"No loadable model artifacts (adapter_config.json or a "
            f"config.json with weight files) found under {root}.\n"
            f"Check that you pointed this at the right top-level folder."
        )
        sys.exit(1)

    print(f"Found {len(results)} candidate model artifact(s) under {root}:\n")
    for i, r in enumerate(results, start=1):
        print(f"[{i}] {r['kind']}")
        for k, v in r.items():
            if k in ("kind",):
                continue
            print(f"    {k}: {v}")
        print()

    print(
        "Pick the one that corresponds to your FINAL trained model (not an "
        "intermediate checkpoint, unless that's the one you actually want to "
        "demo), then set:\n\n"
        f"    export COGNIGRAPH_MODEL_PATH=<its 'path' value above>\n"
    )
    if any(r["kind"] == "LoRA adapter" for r in results):
        print(
            "    export COGNIGRAPH_BASE_MODEL=<the 'base_model' value shown above "
            "for the adapter you picked>\n"
        )


if __name__ == "__main__":
    main()
