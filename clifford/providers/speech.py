"""Offline Vosk streaming transcription; audio and partial transcripts are not persisted."""

import json
import threading
from pathlib import Path

from .llm import ProviderError


class LocalSpeech:
    def __init__(self, settings):
        self.path = Path(settings.vosk_model_path)
        self.model = None
        self.lock = threading.Lock()

    def available(self):
        return (self.path / "am/final.mdl").is_file() and (self.path / "conf/model.conf").is_file()

    def recognizer(self):
        if not self.available():
            raise ProviderError("speech_model_not_installed")
        from vosk import KaldiRecognizer, Model, SetLogLevel

        with self.lock:
            if self.model is None:
                SetLogLevel(-1)
                try:
                    self.model = Model(str(self.path))
                except Exception:
                    raise ProviderError("speech_model_invalid") from None
        return KaldiRecognizer(self.model, 16000)

    @staticmethod
    def accept(recognizer, audio):
        final = recognizer.AcceptWaveform(audio)
        data = json.loads(recognizer.Result() if final else recognizer.PartialResult())
        return {"text": data.get("text" if final else "partial", ""), "final": bool(final)}
