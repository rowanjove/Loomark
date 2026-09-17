import re
import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
import yt_dlp
import httpx

logger = logging.getLogger(__name__)

def parse_vtt_or_srv_text(raw_text: str) -> List[Dict[str, Any]]:
    """Parse WebVTT or plain timestamped text into normalized segments."""
    segments = []
    # Pattern for VTT timestamp: 00:01:23.456 --> 00:01:25.789
    time_pat = re.compile(
        r'(?:(\d{1,2}):)?(\d{2}):(\d{2})[.,](\d{3})\s*-->\s*(?:(\d{1,2}):)?(\d{2}):(\d{2})[.,](\d{3})'
    )

    def to_seconds(h, m, s, ms):
        hours = int(h) if h else 0
        return round(hours * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0, 2)

    lines = raw_text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        match = time_pat.search(line)
        if match:
            start_sec = to_seconds(match.group(1), match.group(2), match.group(3), match.group(4))
            end_sec = to_seconds(match.group(5), match.group(6), match.group(7), match.group(8))

            # Collect following non-empty lines as text
            text_lines = []
            i += 1
            while i < len(lines) and lines[i].strip() and "-->" not in lines[i]:
                # Clean html tags e.g. <c> </c>
                clean = re.sub(r'<[^>]+>', '', lines[i]).strip()
                if clean:
                    text_lines.append(clean)
                i += 1
            segment_text = " ".join(text_lines).strip()
            if segment_text:
                segments.append({
                    "start": start_sec,
                    "end": end_sec,
                    "text": segment_text
                })
        else:
            i += 1

    return segments

def postprocess_subtitles(segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Clean and optimize subtitle stream (PRD Section 35):
    - Remove duplicate consecutive lines
    - Merge adjacent tiny fragments
    - Normalize whitespace and punctuation
    """
    if not segments:
        return []

    # 1. Deduplicate consecutive identical texts
    deduped = []
    for s in segments:
        text = s.get("text", "").strip()
        if not text:
            continue
        if deduped and deduped[-1]["text"] == text:
            deduped[-1]["end"] = max(deduped[-1]["end"], s.get("end", deduped[-1]["end"]))
        else:
            deduped.append({
                "start": float(s.get("start", 0.0)),
                "end": float(s.get("end", 0.0)),
                "text": text
            })

    # 2. Merge very short sentence fragments (< 1.2 seconds apart)
    merged = []
    for s in deduped:
        if merged and (s["start"] - merged[-1]["end"] <= 0.8) and (len(merged[-1]["text"]) < 20):
            merged[-1]["end"] = s["end"]
            merged[-1]["text"] = f"{merged[-1]['text']} {s['text']}".strip()
        else:
            merged.append(s)

    return merged

class MediaSubtitleExtractor:
    """
    Video & Subtitle Extractor integrating yt-dlp (PRD Sections 31-35).
    Extracts video title, channel, duration, and official or automatic subtitles,
    followed by timeline segment normalization and post-processing.
    """
    def __init__(self):
        self.ydl_opts = {
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": ["zh-Hans", "zh-Hant", "zh", "en", "all"],
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False
        }

    async def extract_media_info(self, url: str) -> Optional[Dict[str, Any]]:
        """Run yt-dlp extraction in an executor thread to prevent blocking async loop."""
        loop = asyncio.get_event_loop()
        try:
            info = await loop.run_in_executor(None, self._sync_extract, url)
            if not info:
                return None

            # Fetch and parse subtitle streams asynchronously
            parsed_subtitles = await self._resolve_subtitles(info.get("subtitles_raw", {}))

            # If no subtitles found and ASR is configured, attempt ASR fallback (PRD Section 34)
            if not parsed_subtitles:
                from engine.extractors.asr_engine import get_asr_engine
                asr_engine = get_asr_engine()
                if asr_engine:
                    logger.info(f"No subtitle tracks found for {url}. Attempting ASR speech recognition fallback...")
                    asr_subs = await self._transcribe_with_asr(url, asr_engine, info.get("duration", 0))
                    if asr_subs:
                        parsed_subtitles["asr"] = asr_subs

            info["subtitles_parsed"] = parsed_subtitles
            return info
        except Exception as e:
            logger.warning(f"yt-dlp extract failed for {url}: {e}")
            return None

    async def _transcribe_with_asr(self, url: str, asr_engine, duration: int) -> List[Dict[str, Any]]:
        """Download lightweight audio stream and transcribe via ASR engine."""
        import tempfile
        import os
        from pathlib import Path

        # Limit max duration to 30 mins to protect local resources
        if duration > 1800:
            logger.warning(f"Video duration ({duration}s) exceeds 30m limit for automated ASR. Skipping.")
            return []

        temp_dir = tempfile.mkdtemp(prefix="loomark_asr_")
        audio_out = str(Path(temp_dir) / "audio.mp3")

        loop = asyncio.get_event_loop()
        try:
            # Download audio stream using yt-dlp
            download_opts = {
                "format": "bestaudio/best",
                "outtmpl": str(Path(temp_dir) / "audio.%(ext)s"),
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "64",
                }],
                "quiet": True,
                "no_warnings": True
            }

            def _sync_dl():
                with yt_dlp.YoutubeDL(download_opts) as ydl:
                    ydl.download([url])

            await loop.run_in_executor(None, _sync_dl)

            # Find actual audio file (could be .mp3 or original extension)
            files = list(Path(temp_dir).glob("*"))
            if not files:
                return []

            target_audio = str(files[0])
            raw_segments = await asr_engine.transcribe(target_audio)
            return postprocess_subtitles(raw_segments)
        except Exception as e:
            logger.warning(f"ASR audio transcription failed for {url}: {e}")
            return []
        finally:
            # Clean up temporary audio files
            try:
                for f in Path(temp_dir).glob("*"):
                    f.unlink(missing_ok=True)
                os.rmdir(temp_dir)
            except Exception:
                pass

    def _sync_extract(self, url: str) -> Optional[Dict[str, Any]]:
        with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                return None

            title = info.get("title", "")
            uploader = info.get("uploader") or info.get("channel") or ""
            duration = info.get("duration", 0)
            description = info.get("description", "")
            webpage_url = info.get("webpage_url", url)

            # Raw subtitles
            subtitles_data = info.get("subtitles") or info.get("automatic_captions") or {}
            available_langs = list(subtitles_data.keys())

            return {
                "title": title,
                "uploader": uploader,
                "duration": duration,
                "description": description,
                "url": webpage_url,
                "available_languages": available_langs,
                "subtitles_raw": subtitles_data
            }

    async def _resolve_subtitles(self, raw_subs_dict: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """Fetch remote subtitle format and parse into normalized [{start, end, text}]."""
        results = {}
        if not raw_subs_dict:
            return results

        # Preferred language list
        preferred = ["zh-Hans", "zh", "zh-Hant", "en"]
        selected_langs = [l for l in preferred if l in raw_subs_dict] or list(raw_subs_dict.keys())[:2]

        async with httpx.AsyncClient(timeout=10.0) as client:
            for lang in selected_langs:
                formats = raw_subs_dict.get(lang, [])
                if not formats:
                    continue

                # Prioritize vtt or json3 format
                best_fmt = next((f for f in formats if f.get("ext") in ("vtt", "json3")), formats[0])
                sub_url = best_fmt.get("url")
                if not sub_url:
                    continue

                try:
                    res = await client.get(sub_url)
                    if res.status_code == 200:
                        raw_content = res.text
                        if best_fmt.get("ext") == "json3" or raw_content.strip().startswith("{"):
                            data = json.loads(raw_content)
                            events = data.get("events", [])
                            raw_segments = []
                            for ev in events:
                                if "segs" in ev:
                                    t = "".join(s.get("utf8", "") for s in ev["segs"]).strip()
                                    start = round(ev.get("tStartMs", 0) / 1000.0, 2)
                                    dur = round(ev.get("dDurationMs", 0) / 1000.0, 2)
                                    if t:
                                        raw_segments.append({"start": start, "end": start + dur, "text": t})
                            results[lang] = postprocess_subtitles(raw_segments)
                        else:
                            # WebVTT parser
                            raw_segments = parse_vtt_or_srv_text(raw_content)
                            results[lang] = postprocess_subtitles(raw_segments)
                except Exception as e:
                    logger.debug(f"Failed to fetch/parse subtitle for {lang}: {e}")

        return results
