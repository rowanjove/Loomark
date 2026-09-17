import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from engine.extractors.asr_engine import (
    BaseASREngine,
    LocalFasterWhisperEngine,
    RemoteWhisperAPIEngine,
    get_asr_engine
)
from engine.extractors.media_subtitle import MediaSubtitleExtractor

def test_get_asr_engine_disabled():
    engine = get_asr_engine({"asr": {"enabled": False}})
    assert engine is None

def test_get_asr_engine_remote():
    settings = {
        "asr": {
            "enabled": True,
            "mode": "remote",
            "remote_base_url": "https://api.openai.com/v1",
            "remote_api_key": "test-key"
        }
    }
    engine = get_asr_engine(settings)
    assert isinstance(engine, RemoteWhisperAPIEngine)
    assert engine.base_url == "https://api.openai.com/v1"
    assert engine.api_key == "test-key"

def test_local_faster_whisper_lazy_load():
    engine = LocalFasterWhisperEngine(model_size="tiny", device="cpu")
    # If faster-whisper is not installed in current env, calling _load_model raises RuntimeError with helpful guide
    try:
        import faster_whisper
        # If installed, it loads
        assert engine.model_size == "tiny"
    except ImportError:
        with pytest.raises(RuntimeError) as exc:
            engine._load_model()
        assert "未检测到本地 Faster-Whisper 环境" in str(exc.value)

@pytest.mark.asyncio
async def test_media_subtitle_asr_fallback():
    extractor = MediaSubtitleExtractor()

    # Mock yt-dlp extracting video info with NO subtitles
    raw_info = {
        "title": "Silent Video Demo",
        "uploader": "Test Channel",
        "duration": 60,
        "description": "Video with no subtitles",
        "url": "https://example.com/video",
        "available_languages": [],
        "subtitles_raw": {}
    }

    # Mock ASR engine
    mock_asr = MagicMock(spec=BaseASREngine)
    mock_asr.transcribe = AsyncMock(return_value=[
        {"start": 1.0, "end": 4.5, "text": "这是 ASR 模型自动转写的语音片段。"}
    ])

    with patch.object(extractor, "_sync_extract", return_value=raw_info):
        with patch("engine.extractors.asr_engine.get_asr_engine", return_value=mock_asr):
            with patch.object(extractor, "_transcribe_with_asr", return_value=[
                {"start": 1.0, "end": 4.5, "text": "这是 ASR 模型自动转写的语音片段。"}
            ]):
                res = await extractor.extract_media_info("https://example.com/video")
                assert res is not None
                assert "asr" in res["subtitles_parsed"]
                assert len(res["subtitles_parsed"]["asr"]) == 1
                assert "ASR 模型自动转写" in res["subtitles_parsed"]["asr"][0]["text"]
