"""Accept transcripts from browser speech recognition or the simulated CLI."""


class SpeechService:
    def transcribe(self, voice_input: str) -> str:
        if not isinstance(voice_input, str):
            raise ValueError("Voice input must be a transcript string.")
        return voice_input
