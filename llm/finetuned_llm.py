"""
FineTunedLlamaBrain — loads YOUR trained model.

Supports:
  - LoRA adapter directories containing adapter_config.json
  - Fully merged model directories containing config.json

The loader automatically detects whether CUDA is available.

CUDA available:
    Uses the configured 4-bit quantized loading path.

CUDA unavailable:
    Forces the model onto CPU instead of using device_map="auto".
    This avoids BitsAndBytes/Accelerate errors caused by attempting
    to partially dispatch a quantized model to CPU/disk.

Note:
    CPU inference can be very slow for a multi-billion-parameter model.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List

from config import CONFIG
from llm.base import ChatMessage, LLMBrain, LLMResponse


class FineTunedLlamaBrain(LLMBrain):

    def __init__(self):
        self._model = None
        self._tokenizer = None
        self._mode = None  # "adapter" | "merged"
        self._device = None

    def _ensure_loaded(self):
        if self._model is not None:
            return

        # ---------------------------------------------------------
        # Validate model path
        # ---------------------------------------------------------
        if not CONFIG.llm.model_path:
            raise RuntimeError(
                "COGNIGRAPH_MODEL_PATH is not set. Point it at your trained "
                "model directory (a LoRA adapter dir or a merged model dir) "
                "either in config.py or as an environment variable."
            )

        model_path = Path(CONFIG.llm.model_path)

        if not model_path.exists():
            raise FileNotFoundError(
                f"Model path does not exist: {model_path}"
            )

        is_adapter = (model_path / "adapter_config.json").exists()

        # ---------------------------------------------------------
        # Imports
        # ---------------------------------------------------------
        import torch
        from transformers import (
            AutoModelForCausalLM,
            AutoTokenizer,
            BitsAndBytesConfig,
        )

        cuda_available = torch.cuda.is_available()

        print(
            f"[CogniGraph] CUDA available: {cuda_available}"
        )

        if cuda_available:
            self._device = torch.device("cuda")
        else:
            self._device = torch.device("cpu")

        print(
            f"[CogniGraph] Inference device: {self._device}"
        )

        # ---------------------------------------------------------
        # Quantization configuration
        #
        # Use 4-bit only when CUDA is actually available.
        #
        # Your current environment reports CUDA=False, so passing a
        # 4-bit configuration together with device_map='auto' can
        # cause the CPU/disk dispatch error seen in the traceback.
        # ---------------------------------------------------------
        quant_config = None

        if CONFIG.llm.load_in_4bit and cuda_available:

            quant_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_quant_type="nf4",
            )

        # ---------------------------------------------------------
        # Load LoRA adapter
        # ---------------------------------------------------------
        if is_adapter:

            from peft import PeftModel

            adapter_cfg_path = model_path / "adapter_config.json"

            adapter_cfg = json.loads(
                adapter_cfg_path.read_text(encoding="utf-8")
            )

            trained_base = adapter_cfg.get(
                "base_model_name_or_path"
            )

            if (
                trained_base
                and trained_base != CONFIG.llm.base_model_id
            ):
                print(
                    "[CogniGraph] WARNING: adapter was trained against "
                    f"'{trained_base}' but "
                    f"CONFIG.llm.base_model_id is "
                    f"'{CONFIG.llm.base_model_id}'. "
                    "The base model should match the training base."
                )

            # -----------------------------------------------------
            # CUDA path
            # -----------------------------------------------------
            if cuda_available:

                print(
                    "[CogniGraph] Loading quantized base model on CUDA..."
                )

                base_model = AutoModelForCausalLM.from_pretrained(
                    CONFIG.llm.base_model_id,
                    quantization_config=quant_config,
                    device_map="auto",
                )

            # -----------------------------------------------------
            # CPU path
            # -----------------------------------------------------
            else:

                print(
                    "[CogniGraph] CUDA unavailable. "
                    "Loading base model on CPU..."
                )

                # Explicit CPU placement.
                #
                # Do NOT use device_map="auto" here.
                base_model = AutoModelForCausalLM.from_pretrained(
                    CONFIG.llm.base_model_id,
                    device_map={"": "cpu"},
                    torch_dtype=torch.float32,
                    low_cpu_mem_usage=True,
                )

            # -----------------------------------------------------
            # Tokenizer
            # -----------------------------------------------------
            tokenizer_source = (
                str(model_path)
                if (model_path / "tokenizer_config.json").exists()
                else CONFIG.llm.base_model_id
            )

            self._tokenizer = AutoTokenizer.from_pretrained(
                tokenizer_source
            )

            # -----------------------------------------------------
            # Apply LoRA adapter
            # -----------------------------------------------------
            self._model = PeftModel.from_pretrained(
                base_model,
                str(model_path),
            )

            self._mode = "adapter"

        # ---------------------------------------------------------
        # Load merged model
        # ---------------------------------------------------------
        else:

            if cuda_available:

                print(
                    "[CogniGraph] Loading merged model on CUDA..."
                )

                self._model = AutoModelForCausalLM.from_pretrained(
                    str(model_path),
                    quantization_config=quant_config,
                    device_map="auto",
                )

            else:

                print(
                    "[CogniGraph] CUDA unavailable. "
                    "Loading merged model on CPU..."
                )

                self._model = AutoModelForCausalLM.from_pretrained(
                    str(model_path),
                    device_map={"": "cpu"},
                    torch_dtype=torch.float32,
                    low_cpu_mem_usage=True,
                )

            self._tokenizer = AutoTokenizer.from_pretrained(
                str(model_path)
            )

            self._mode = "merged"

        # ---------------------------------------------------------
        # Final model setup
        # ---------------------------------------------------------
        self._model.eval()

        print(
            f"[CogniGraph] Loaded fine-tuned brain in "
            f"'{self._mode}' mode from {model_path}"
        )

        print(
            f"[CogniGraph] Running inference on: {self._device}"
        )

    def generate(
        self,
        messages: List[ChatMessage]
    ) -> LLMResponse:

        # Use remote GPU inference when configured; otherwise keep local behavior.
        remote_url = os.environ.get("COGNIGRAPH_REMOTE_LLM_URL")
        if remote_url:
            remote_key = os.environ.get("COGNIGRAPH_REMOTE_LLM_API_KEY")
            if not remote_key:
                raise RuntimeError("RunPod URL is set but its API key is missing.")

            from urllib.request import Request, urlopen
            from urllib.error import HTTPError, URLError

            payload = {
                "messages": [
                    {"role": m.role, "content": m.content}
                    for m in messages
                ],
                "max_new_tokens": max(
                    1, min(int(CONFIG.llm.max_new_tokens), 512)
                ),
                "temperature": float(CONFIG.llm.temperature),
            }
            request = Request(
                remote_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "X-API-Key": remote_key,
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                    "Accept": "application/json",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "identity",
                },
                method="POST",
            )

            try:
                with urlopen(request, timeout=90) as response:
                    result = json.loads(response.read().decode("utf-8"))
            except HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")[:400]
                raise RuntimeError(
                    f"RunPod returned HTTP {exc.code}: {detail}"
                ) from exc
            except URLError as exc:
                raise RuntimeError(
                    f"Could not reach RunPod inference API: {exc}"
                ) from exc

            answer = result.get("text") if isinstance(result, dict) else None
            if not isinstance(answer, str) or not answer.strip():
                raise RuntimeError("RunPod returned no generated text.")

            return LLMResponse(
                text=answer.strip(),
                raw={"backend": "runpod", "mode": "remote", "device": "gpu"},
            )

        self._ensure_loaded()

        import torch

        # ---------------------------------------------------------
        # Convert messages to chat-template format
        # ---------------------------------------------------------
        chat = [
            {
                "role": m.role,
                "content": m.content,
            }
            for m in messages
        ]

        prompt = self._tokenizer.apply_chat_template(
            chat,
            tokenize=False,
            add_generation_prompt=True,
        )

        # ---------------------------------------------------------
        # Tokenize
        # ---------------------------------------------------------
        inputs = self._tokenizer(
            prompt,
            return_tensors="pt",
        )

        # Explicitly move inputs to the same device used by the model.
        inputs = {
            key: value.to(self._device)
            for key, value in inputs.items()
        }

        # ---------------------------------------------------------
        # Generation
        # ---------------------------------------------------------
        generation_kwargs = {
            "max_new_tokens": CONFIG.llm.max_new_tokens,
            "pad_token_id": self._tokenizer.eos_token_id,
        }

        if CONFIG.llm.temperature > 0:
            generation_kwargs.update(
                {
                    "temperature": CONFIG.llm.temperature,
                    "do_sample": True,
                }
            )
        else:
            generation_kwargs.update(
                {
                    "do_sample": False,
                }
            )

        with torch.no_grad():

            output_ids = self._model.generate(
                **inputs,
                **generation_kwargs,
            )

        # ---------------------------------------------------------
        # Remove prompt tokens
        # ---------------------------------------------------------
        generated = output_ids[0][
            inputs["input_ids"].shape[-1]:
        ]

        text = self._tokenizer.decode(
            generated,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False,
        ).strip()

        return LLMResponse(
            text=text,
            raw={
                "backend": "finetuned",
                "mode": self._mode,
                "device": str(self._device),
            },
        )