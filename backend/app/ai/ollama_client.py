"""Ollama HTTP client for local AI reasoning (Phase 5)."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

import httpx

from ..config import OLLAMA_MODEL, OLLAMA_TIMEOUT_SECONDS, OLLAMA_URL

logger = logging.getLogger(__name__)


class OllamaUnavailable(Exception):
    pass


class OllamaClient:
    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None):
        self.base_url = (base_url or OLLAMA_URL).rstrip("/")
        self.model = model or OLLAMA_MODEL

    def is_available(self) -> bool:
        try:
            with httpx.Client(timeout=5) as client:
                resp = client.get(f"{self.base_url}/api/tags")
                resp.raise_for_status()
                return True
        except Exception:
            return False

    def generate(self, prompt: str, temperature: float = 0.3, max_tokens: int = 400) -> Optional[str]:
        """Generate a text response. Returns None when Ollama is unreachable."""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        try:
            with httpx.Client(timeout=OLLAMA_TIMEOUT_SECONDS) as client:
                resp = client.post(f"{self.base_url}/api/generate", json=payload)
                resp.raise_for_status()
                data = resp.json()
            return str(data.get("response", "")).strip() or None
        except Exception as exc:
            logger.warning("ollama generate failed: %s", exc)
            return None

    def generate_json(self, prompt: str, temperature: float = 0.3, max_tokens: int = 800) -> Optional[Dict[str, Any]]:
        text = self.generate(prompt, temperature=temperature, max_tokens=max_tokens)
        if not text:
            return None
        # Extract first JSON object/array from the text (LLMs often add preamble).
        start = len(text)
        end = -1
        for opener, closer in ("{}", "[]"):
            idx = text.find(opener)
            if idx != -1:
                start = min(start, idx)
                end = text.rfind(closer)
        try:
            candidate = text[start:end + 1] if end >= 0 else None
            if candidate is None:
                raise ValueError("no json block")
            parsed = json.loads(candidate)
            return parsed if isinstance(parsed, dict) else None
        except Exception:
            logger.warning("ollama returned non-JSON output")
            return None


ollama_client = OllamaClient()
