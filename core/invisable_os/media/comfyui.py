"""ComfyUI client — submit a workflow, poll for completion, download the output.

Implements the real ComfyUI HTTP API (``/prompt`` → ``/history/{id}`` → ``/view``)
used for Flux images and Wan/Hunyuan/LTX video. A built-in text-to-image workflow is
provided; point ``COMFYUI_WORKFLOW`` at a JSON file to use your own graph (with
``%PROMPT%``/``%SEED%``/``%WIDTH%``/``%HEIGHT%`` placeholders).

The client never sleeps when the result is already available (so tests with a mocked
transport are instant), and raises on failure so the renderer can fall back to
dry-run rather than crashing the pipeline.
"""

from __future__ import annotations

import json
import os
import time

import httpx

from invisable_os.media.fsutil import write_bytes


def build_workflow(
    prompt: str,
    *,
    width: int = 1024,
    height: int = 1024,
    seed: int = 0,
    checkpoint: str = "",
    negative: str = "",
    prefix: str = "invisable",
) -> dict:
    """Return a standard ComfyUI text-to-image prompt graph.

    Honours ``COMFYUI_WORKFLOW`` (a JSON template with %PROMPT%/%SEED%/%WIDTH%/
    %HEIGHT% placeholders) when set; otherwise builds a vanilla SD/Flux graph.
    """
    template_path = os.getenv("COMFYUI_WORKFLOW", "")
    if template_path and os.path.isfile(template_path):
        with open(template_path, encoding="utf-8") as f:
            raw = f.read()
        raw = (
            raw.replace("%PROMPT%", json.dumps(prompt)[1:-1])
            .replace("%SEED%", str(seed))
            .replace("%WIDTH%", str(width))
            .replace("%HEIGHT%", str(height))
        )
        return json.loads(raw)

    ckpt = checkpoint or os.getenv("COMFYUI_CHECKPOINT", "v1-5-pruned-emaonly.safetensors")
    return {
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "seed": seed, "steps": 20, "cfg": 7.0, "sampler_name": "euler",
                "scheduler": "normal", "denoise": 1.0,
                "model": ["4", 0], "positive": ["6", 0], "negative": ["7", 0],
                "latent_image": ["5", 0],
            },
        },
        "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": ckpt}},
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": width, "height": height, "batch_size": 1},
        },
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["4", 1]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": negative, "clip": ["4", 1]}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": prefix, "images": ["8", 0]}},
    }


class ComfyUIClient:
    def __init__(self, base_url: str, client: httpx.Client | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = client or httpx.Client(timeout=30.0)

    def submit(self, graph: dict) -> str:
        resp = self._client.post(f"{self.base_url}/prompt", json={"prompt": graph})
        resp.raise_for_status()
        prompt_id = resp.json().get("prompt_id")
        if not prompt_id:
            raise RuntimeError("ComfyUI did not return a prompt_id")
        return prompt_id

    def wait(self, prompt_id: str, *, max_attempts: int = 120, interval: float = 1.0) -> dict:
        for attempt in range(max_attempts):
            resp = self._client.get(f"{self.base_url}/history/{prompt_id}")
            resp.raise_for_status()
            history = resp.json()
            entry = history.get(prompt_id)
            if entry and entry.get("outputs"):
                return entry["outputs"]
            if attempt + 1 < max_attempts:
                time.sleep(interval)
        raise TimeoutError(f"ComfyUI render {prompt_id} did not complete")

    def fetch(self, image_ref: dict) -> bytes:
        resp = self._client.get(
            f"{self.base_url}/view",
            params={
                "filename": image_ref.get("filename", ""),
                "subfolder": image_ref.get("subfolder", ""),
                "type": image_ref.get("type", "output"),
            },
        )
        resp.raise_for_status()
        return resp.content

    @staticmethod
    def first_image(outputs: dict) -> dict | None:
        for node in outputs.values():
            for image in node.get("images", []) or []:
                return image
        return None

    def generate(self, prompt: str, out_path: str, *, width: int = 1024, height: int = 1024,
                 seed: int = 0, **kw) -> str:
        """Run a full text-to-image job and write the result to ``out_path``."""
        graph = build_workflow(prompt, width=width, height=height, seed=seed, **kw)
        outputs = self.wait(self.submit(graph))
        image = self.first_image(outputs)
        if image is None:
            raise RuntimeError("ComfyUI returned no images")
        return write_bytes(out_path, self.fetch(image))
