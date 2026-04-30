import os
from typing import Optional
from openai import OpenAI


class SpeechProcessor:
    def __init__(self, api_key: Optional[str] = None):
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        if not (api_key or os.getenv("OPENAI_API_KEY")):
            raise ValueError("OPENAI_API_KEY is missing. Put it in .env or pass api_key=...")

    def transcribe(
        self,
        audio_file_path: str,
        language: str = "ar",
        prompt: Optional[str] = None,
        temperature: float = 0.0,
        model: str = "whisper-1",
    ) -> str:
        """
        Transcribes audio file to text using OpenAI Whisper.

        Args:
            audio_file_path: Path to audio file (.mp3/.wav/.m4a/.ogg/...).
            language: BCP-47-ish language hint, e.g. "ar" or "en". (Helps accuracy)
            prompt: Optional prompt to bias transcription (names/places/terms).
            temperature: 0.0 is most deterministic.
            model: default "whisper-1".

        Returns:
            Transcript as plain text.

        Raises:
            FileNotFoundError: if file doesn't exist.
            ValueError: if file extension unsupported.
            RuntimeError: if transcription fails.
        """
        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"Audio file not found: {audio_file_path}")

        ext = os.path.splitext(audio_file_path)[1].lower()
        allowed = {".mp3", ".wav", ".m4a", ".ogg", ".webm", ".mp4", ".mpeg", ".mpga", ".flac"}
        if ext not in allowed:
            raise ValueError(
                f"Unsupported audio extension '{ext}'. Allowed: {sorted(allowed)}"
            )

        try:
            with open(audio_file_path, "rb") as audio_file:
                # Whisper transcription endpoint
                result = self.client.audio.transcriptions.create(
                    model=model,
                    file=audio_file,
                    response_format="text",
                    language=language,
                    prompt=prompt,
                    temperature=temperature,
                )

            # response_format="text" typically returns plain string already,
            # but we normalize just in case.
            if isinstance(result, str):
                return result.strip()
            return str(result).strip()

        except Exception as e:
            raise RuntimeError(f"Transcription failed for '{audio_file_path}': {e}") from e