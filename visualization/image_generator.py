"""
Phase 3 — Visualization: Concept Art (optional, "Core Features" in the proposal).

Genuine image generation (SDXL locally, or DALL-E via API) needs either a
GPU with several GB of VRAM free or an API key + internet access, neither
of which this scaffolding assumes you have set up yet. This module is a
clearly-marked stub: it returns a message explaining what's missing rather
than silently doing nothing, and both real implementations are sketched in
comments so wiring one in is a ~10 line change.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ImageResult:
    available: bool
    message: str
    image_bytes: bytes | None = None


def generate_concept_image(prompt: str) -> ImageResult:
    """Returns ImageResult(available=False, ...) until you wire in a backend.

    To enable local SDXL (needs a GPU + `diffusers`):
        from diffusers import StableDiffusionXLPipeline
        import torch
        pipe = StableDiffusionXLPipeline.from_pretrained(
            "stabilityai/stable-diffusion-xl-base-1.0", torch_dtype=torch.float16
        ).to("cuda")
        image = pipe(prompt=prompt).images[0]
        # convert PIL image to PNG bytes and return it as image_bytes below

    To enable DALL-E via OpenAI (needs OPENAI_API_KEY + internet):
        from openai import OpenAI
        client = OpenAI()
        result = client.images.generate(model="dall-e-3", prompt=prompt, n=1, size="1024x1024")
        # download result.data[0].url and return its bytes as image_bytes below
    """
    return ImageResult(
        available=False,
        message=(
            "Concept-art generation isn't configured yet. This mode was detected "
            "correctly by the router, but no image backend (local SDXL or DALL-E) "
            "is wired in — see visualization/image_generator.py for the two "
            "options and how to enable one."
        ),
    )
