import os
import io
import time
import numpy as np
from typing import Dict, Any, Optional, Union
from backend.app.core.logging import logger

class SpeechRecognitionProvider:
    """
    Local Speech Recognition Provider powered by OpenAI Whisper.
    Performs on-device speech-to-text conversion for voice queries.
    Supports WAV, MP3, OGG, WEBM, FLAC with automatic audio normalization.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(SpeechRecognitionProvider, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, model_size: Optional[str] = None):
        from backend.app.core.config import settings
        target_model = model_size or getattr(settings, "WHISPER_MODEL", "base")
        if getattr(self, "_initialized", False) and getattr(self, "model_size", None) == target_model and self.model is not None:
            return

        self.model_size = target_model
        self.model = None
        self._load_model()
        self._initialized = True

    def _load_model(self):
        try:
            import whisper
            logger.info(f"Loading Whisper '{self.model_size}' speech recognition model...")
            self.model = whisper.load_model(self.model_size)
            logger.info("Whisper model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            self.model = None

    def _load_audio_to_numpy(self, audio_source: Union[str, bytes]) -> np.ndarray:
        """
        Converts audio file or byte buffer into a 16kHz mono float32 numpy array.
        Uses soundfile first (pure Python/C, no external ffmpeg required for WAV/FLAC/OGG),
        falling back to whisper.load_audio if needed.
        """
        import soundfile as sf

        data = None
        sr = 16000

        if isinstance(audio_source, bytes):
            buffer = io.BytesIO(audio_source)
            try:
                data, sr = sf.read(buffer, dtype="float32")
            except Exception as e:
                logger.warning(f"soundfile failed to decode audio bytes: {e}")
                # Save to temp file and try
                import tempfile
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                    tmp.write(audio_source)
                    tmp_path = tmp.name
                try:
                    data, sr = sf.read(tmp_path, dtype="float32")
                finally:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
        elif isinstance(audio_source, str):
            if not os.path.exists(audio_source):
                raise FileNotFoundError(f"Audio file not found: {audio_source}")
            try:
                data, sr = sf.read(audio_source, dtype="float32")
            except Exception as e:
                logger.warning(f"soundfile failed to read {audio_source}: {e}")
                import whisper
                data = whisper.load_audio(audio_source)
                return data

        if data is None:
            raise ValueError("Could not decode audio from source")

        # Convert stereo to mono
        if len(data.shape) > 1:
            data = data.mean(axis=1)

        # Resample to 16kHz if necessary
        if sr != 16000:
            from scipy import signal
            num_samples = int(len(data) * 16000 / sr)
            data = signal.resample(data, num_samples).astype(np.float32)

        return data

    def transcribe(self, audio_source: Union[str, bytes], language: Optional[str] = None) -> Dict[str, Any]:
        """
        Transcribe audio into text.
        Returns:
            {
                "text": "...",
                "language": "en",
                "duration_seconds": float,
                "is_empty": bool,
                "latency_ms": float
            }
        """
        from backend.app.core.config import settings
        target_lang = language if language is not None else getattr(settings, "WHISPER_LANGUAGE", "en")
        whisper_lang = target_lang if target_lang else None

        start_time = time.time()

        if self.model is None:
            self._load_model()
            if self.model is None:
                raise RuntimeError("Whisper speech recognition model is not available.")

        # Load audio into numpy array
        try:
            audio_array = self._load_audio_to_numpy(audio_source)
        except Exception as e:
            logger.error(f"Audio decoding error: {e}")
            raise ValueError(f"Invalid or corrupted audio file: {e}")

        # Check for silence or empty audio
        duration_sec = len(audio_array) / 16000.0
        if duration_sec < 0.2:
            logger.warning(f"Audio rejected: duration {duration_sec:.2f}s is below minimum 0.2s threshold (samples: {len(audio_array)})")
            return {
                "text": "",
                "language": target_lang or "en",
                "duration_seconds": round(duration_sec, 2),
                "is_empty": True,
                "latency_ms": round((time.time() - start_time) * 1000.0, 2)
            }

        max_amplitude = float(np.max(np.abs(audio_array)))
        rms_amplitude = float(np.sqrt(np.mean(audio_array**2))) if len(audio_array) > 0 else 0.0

        if max_amplitude < 1e-4:
            logger.info(f"Audio is silent (duration: {duration_sec:.2f}s, max_amplitude: {max_amplitude:.6f} < 1e-4, RMS: {rms_amplitude:.6f})")
            return {
                "text": "",
                "language": target_lang or "en",
                "duration_seconds": round(duration_sec, 2),
                "is_empty": True,
                "latency_ms": round((time.time() - start_time) * 1000.0, 2)
            }

        # Normalize volume if quiet (peak amplitude < 0.70)
        # to ensure optimal Whisper attention and prevent false no-speech drop
        if max_amplitude > 1e-4 and max_amplitude < 0.70:
            scale_factor = min(0.85 / max_amplitude, 15.0)
            audio_array = audio_array * scale_factor
            logger.info(f"Normalized quiet audio (original peak: {max_amplitude:.4f}, new peak: {np.max(np.abs(audio_array)):.4f}, gain: {scale_factor:.1f}x)")

        # Transcribe with Whisper
        try:
            result = self.model.transcribe(
                audio_array,
                language=whisper_lang,
                fp16=False,
                task="transcribe",
                condition_on_previous_text=False
            )
            raw_text = result.get("text", "").strip()
            latency_ms = (time.time() - start_time) * 1000.0

            if not raw_text:
                logger.info(f"Whisper produced empty transcript for {duration_sec:.2f}s audio (max_amp={max_amplitude:.4f}, rms={rms_amplitude:.4f})")
            else:
                logger.info(f"Transcribed audio ({duration_sec:.1f}s, max_amp={max_amplitude:.4f}, rms={rms_amplitude:.4f}) in {latency_ms:.1f}ms: '{raw_text}'")

            return {
                "text": raw_text,
                "language": result.get("language", target_lang or "en"),
                "duration_seconds": round(duration_sec, 2),
                "is_empty": len(raw_text) == 0,
                "latency_ms": round(latency_ms, 2)
            }
        except Exception as e:
            logger.error(f"Whisper transcription error: {e}")
            raise RuntimeError(f"Speech transcription failed: {e}")
