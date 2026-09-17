import os
import logging
import asyncio
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pathlib import Path
import httpx

logger = logging.getLogger(__name__)

class BaseASREngine(ABC):
    """Abstract base class for Speech-to-Text ASR engines."""

    @abstractmethod
    async def transcribe(self, audio_path: str, language: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Transcribe audio file into normalized timeline segments:
        [{"start": float, "end": float, "text": str}]
        """
        pass

class LocalFasterWhisperEngine(BaseASREngine):
    """
    Local offline Whisper ASR engine based on faster-whisper / ctranslate2 (PRD Section 34).
    Lazy-loads dependencies to ensure non-blocking startup even if weights or PyTorch are absent.
    """
    def __init__(self, model_size: str = "base", device: str = "cpu", compute_type: str = "int8"):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model = None

    def _load_model(self):
        if self._model is not None:
            return self._model
        try:
            from faster_whisper import WhisperModel
        except ImportError as e:
            raise RuntimeError(
                "未检测到本地 Faster-Whisper 环境。请在 Python 环境中安装: pip install faster-whisper "
                "或在设置中切换为远程 Whisper API 模式。"
            ) from e

        logger.info(f"Loading local faster-whisper model: {self.model_size} on {self.device} ({self.compute_type})...")
        self._model = WhisperModel(self.model_size, device=self.device, compute_type=self.compute_type)
        return self._model

    async def transcribe(self, audio_path: str, language: Optional[str] = None) -> List[Dict[str, Any]]:
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_transcribe, audio_path, language)

    def _sync_transcribe(self, audio_path: str, language: Optional[str] = None) -> List[Dict[str, Any]]:
        model = self._load_model()
        segments, info = model.transcribe(audio_path, language=language, beam_size=5)
        results = []
        for s in segments:
            results.append({
                "start": round(s.start, 2),
                "end": round(s.end, 2),
                "text": s.text.strip()
            })
        return results

class RemoteWhisperAPIEngine(BaseASREngine):
    """
    Remote ASR engine connecting to OpenAI-compatible audio transcription endpoints
    (e.g., OpenAI /v1/audio/transcriptions, Groq, local FastWhisperServer, or custom proxy).
    """
    def __init__(self, base_url: str = "https://api.openai.com/v1", api_key: str = "", model: str = "whisper-1"):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    async def transcribe(self, audio_path: str, language: Optional[str] = None) -> List[Dict[str, Any]]:
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        endpoint = f"{self.base_url}/audio/transcriptions"
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        filename = Path(audio_path).name
        async with httpx.AsyncClient(timeout=120.0) as client:
            with open(audio_path, "rb") as f:
                files = {"file": (filename, f, "audio/mpeg")}
                data = {
                    "model": self.model,
                    "response_format": "verbose_json"
                }
                if language:
                    data["language"] = language

                resp = await client.post(endpoint, headers=headers, data=data, files=files)
                if resp.status_code != 200:
                    raise RuntimeError(f"Remote ASR request failed ({resp.status_code}): {resp.text}")

                res_json = resp.json()

            segments_raw = res_json.get("segments", [])
            if segments_raw:
                return [
                    {
                        "start": round(float(s.get("start", 0.0)), 2),
                        "end": round(float(s.get("end", 0.0)), 2),
                        "text": s.get("text", "").strip()
                    }
                    for s in segments_raw if s.get("text", "").strip()
                ]

            # Fallback if only full text returned
            full_text = res_json.get("text", "").strip()
            if full_text:
                return [{"start": 0.0, "end": 0.0, "text": full_text}]
            return []

def get_asr_engine(settings: Optional[Dict[str, Any]] = None) -> Optional[BaseASREngine]:
    """
    Factory to construct the configured ASR engine. Returns None if ASR is disabled.
    """
    if settings is None:
        from engine.config import load_settings
        settings = load_settings()

    asr_cfg = settings.get("asr", {})
    if not asr_cfg.get("enabled", False):
        return None

    mode = asr_cfg.get("mode", "remote")
    if mode == "local":
        model_size = asr_cfg.get("model_size", "base")
        device = asr_cfg.get("device", "cpu")
        return LocalFasterWhisperEngine(model_size=model_size, device=device)
    elif mode == "remote":
        base_url = asr_cfg.get("remote_base_url") or "https://api.openai.com/v1"
        api_key = asr_cfg.get("remote_api_key") or os.getenv("OPENAI_API_KEY", "")
        model = asr_cfg.get("remote_model", "whisper-1")
        return RemoteWhisperAPIEngine(base_url=base_url, api_key=api_key, model=model)

    return None
