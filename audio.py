"""
ZOEY — audio.py
Fixed: Female fallback voice for pyttsx3 + detailed ElevenLabs status logs.
"""

import os
import sys
import subprocess
import socket
import tempfile
import time
import wave

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", "4")

import numpy as np
import sounddevice as sd
from dotenv import load_dotenv
from faster_whisper import WhisperModel

import config
import privacy

load_dotenv(override=True)


def get_mic_name() -> str:
    try:
        device_idx = getattr(config, "MIC_DEVICE_INDEX", None)
        if device_idx is None:
            info = sd.query_devices(kind="input")
        else:
            info = sd.query_devices(device_idx, "input")
        return info.get("name", "Default Microphone")
    except Exception:
        return "Default Microphone"


def load_whisper_model() -> WhisperModel:
    print(f"Loading Whisper speech model ({config.WHISPER_MODEL_SIZE})...")
    return WhisperModel(
        config.WHISPER_MODEL_SIZE,
        device="cpu",
        compute_type="int8",
        cpu_threads=config.WHISPER_CPU_THREADS,
    )


def record_and_transcribe(whisper_model: WhisperModel, duration_seconds: float, level_callback=None) -> str:
    sample_rate = config.SAMPLE_RATE
    total_frames = int(duration_seconds * sample_rate)
    chunk_size = int(sample_rate * 0.05)

    frames = []
    recorded_frames = 0

    try:
        device_idx = getattr(config, "MIC_DEVICE_INDEX", None)
        with sd.InputStream(
            samplerate=sample_rate,
            channels=1,
            dtype="float32",
            device=device_idx,
        ) as stream:
            while recorded_frames < total_frames:
                to_read = min(chunk_size, total_frames - recorded_frames)
                chunk, _ = stream.read(to_read)
                frames.append(chunk)
                recorded_frames += len(chunk)

                if level_callback:
                    peak = float(np.max(np.abs(chunk))) if len(chunk) > 0 else 0.0
                    level_callback(peak)

        if level_callback:
            level_callback(0.0)

    except Exception as e:
        raise RuntimeError(f"Microphone error: {e}")

    audio_flat = np.concatenate(frames, axis=0).flatten()

    peak_volume = float(np.max(np.abs(audio_flat))) if len(audio_flat) > 0 else 0.0
    if peak_volume < 0.03:
        return ""

    segments, _ = whisper_model.transcribe(
        audio_flat,
        language="en",
        condition_on_previous_text=False,
        no_speech_threshold=0.6,
    )

    text = " ".join(segment.text for segment in segments).strip()
    return text.lower()


def load_tts_engine():
    """Initializes local offline voice engine and forces a female voice (Microsoft Zira)."""
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty("rate", 185)
        
        # Look for Windows female voices (Zira, Hazel, Catherine, etc.)
        voices = engine.getProperty("voices")
        for voice in voices:
            v_name = voice.name.lower()
            if "zira" in v_name or "hazel" in v_name or "female" in v_name or "catherine" in v_name:
                engine.setProperty("voice", voice.id)
                break
        return engine
    except Exception:
        return None


def _play_audio_file(file_path: str):
    if file_path.lower().endswith(".wav"):
        try:
            with wave.open(file_path, "rb") as wf:
                channels = wf.getnchannels()
                sample_rate = wf.getframerate()
                sample_width = wf.getsampwidth()
                frames = wf.readframes(wf.getnframes())
            if sample_width == 2:
                audio = np.frombuffer(frames, dtype=np.int16)
                if channels > 1:
                    audio = audio.reshape(-1, channels)
                audio_f = (audio.astype(np.float32) / 32768.0).copy()
                sd.play(audio_f, samplerate=sample_rate)
                sd.wait()
                return
        except Exception:
            pass
    try:
        import pygame
        pygame.mixer.init()
        pygame.mixer.music.load(file_path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.05)
        pygame.mixer.quit()
    except Exception:
        try:
            from playsound import playsound
            playsound(file_path)
        except Exception as e:
            raise RuntimeError(f"Audio playback failed: {e}")


def _speak_elevenlabs(text: str, log=None) -> None:
    import requests

    api_key = os.getenv("ELEVENLABS_API_KEY") or getattr(config, "ELEVENLABS_API_KEY", "")
    voice_id = os.getenv("ELEVENLABS_VOICE_ID") or getattr(config, "ELEVENLABS_VOICE_ID", "pFZP5JQG7iQjIQuC4Bku")
    model_id = getattr(config, "ELEVENLABS_MODEL_ID", "eleven_flash_v2_5")

    if not api_key:
        raise RuntimeError("ELEVENLABS_API_KEY is missing from .env")
    if not privacy.allow_external("voice"):
        raise RuntimeError("Cloud voice is blocked by PRIVACY_MODE=local")

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload = {
        "text": privacy.sanitize_text(text),
        "model_id": model_id,
        "voice_settings": {"stability": 0.4, "similarity_boost": 0.8},
    }

    res = requests.post(url, headers=headers, json=payload, timeout=20)
    if res.status_code != 200:
        raise RuntimeError(f"ElevenLabs API Error {res.status_code}: {res.text}")

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        f.write(res.content)
        temp_path = f.name

    try:
        _play_audio_file(temp_path)
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass


def _can_use_elevenlabs() -> bool:
    if bool(getattr(config, "OFFLINE_MODE", False)):
        return False
    api_key = os.getenv("ELEVENLABS_API_KEY") or getattr(config, "ELEVENLABS_API_KEY", "")
    if not api_key:
        return False
    try:
        socket.create_connection(("api.elevenlabs.io", 443), timeout=1.5).close()
        return True
    except Exception:
        return False


def _speak_piper(text: str, log=None) -> None:
    exe = os.getenv("PIPER_EXE") or getattr(config, "PIPER_EXE", "piper")
    model = os.getenv("PIPER_MODEL") or getattr(config, "PIPER_MODEL", "")
    if not model:
        raise RuntimeError("PIPER_MODEL is missing")

    length_scale = getattr(config, "PIPER_LENGTH_SCALE", 1.0)
    noise_scale = getattr(config, "PIPER_NOISE_SCALE", 0.667)
    noise_w = getattr(config, "PIPER_NOISE_W", 0.8)
    sentence_silence = getattr(config, "PIPER_SENTENCE_SILENCE", 0.2)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        wav_path = f.name

    args = [
        exe,
        "--model",
        model,
        "--output_file",
        wav_path,
        "--length_scale",
        str(length_scale),
        "--noise_scale",
        str(noise_scale),
        "--noise_w",
        str(noise_w),
        "--sentence_silence",
        str(sentence_silence),
    ]

    try:
        res = subprocess.run(
            args,
            input=text,
            text=True,
            encoding="utf-8",
            errors="ignore",
            capture_output=True,
            check=True,
        )
        if res.stderr and log:
            log(res.stderr.strip(), "debug")
        _play_audio_file(wav_path)
    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or "").strip()
        raise RuntimeError(stderr or f"Piper exited with code {e.returncode}")
    finally:
        try:
            os.remove(wav_path)
        except OSError:
            pass


def _speak_pyttsx3(engine, text: str) -> None:
    if engine is None:
        return
    engine.say(text)
    engine.runAndWait()


def speak(pyttsx3_engine, text: str, mute: bool = False, log=None) -> None:
    if mute or not text:
        return

    tts_provider = getattr(config, "TTS_PROVIDER", "elevenlabs")

    if log:
        log(f"Voice provider: {tts_provider}", "voice")

    if tts_provider == "auto":
        if _can_use_elevenlabs():
            try:
                _speak_elevenlabs(text, log=log)
                return
            except Exception as e:
                msg = f"ElevenLabs failed ({e}). Using offline voice."
                if log:
                    log(msg, "warn")
                else:
                    print(f"\n⚠️ {msg}")

        try:
            _speak_piper(text, log=log)
            return
        except Exception as e:
            msg = f"Piper failed ({e}). Using offline fallback voice."
            if log:
                log(msg, "warn")
            else:
                print(f"\n⚠️ {msg}")
            if pyttsx3_engine is None:
                if log:
                    log("Offline fallback voice engine is unavailable.", "warn")
                return
            _speak_pyttsx3(pyttsx3_engine, text)
            return

    if tts_provider == "piper":
        try:
            _speak_piper(text, log=log)
            return
        except Exception as e:
            msg = f"Piper failed ({e}). Using offline fallback voice."
            if log:
                log(msg, "warn")
            else:
                print(f"\n⚠️ {msg}")

    if tts_provider == "elevenlabs":
        try:
            _speak_elevenlabs(text, log=log)
            return
        except Exception as e:
            msg = f"ElevenLabs failed ({e}). Using offline female voice fallback."
            if log:
                log(msg, "warn")
            else:
                print(f"\n⚠️ {msg}")

    # Offline backup (Microsoft Zira)
    _speak_pyttsx3(pyttsx3_engine, text)
