import edge_tts
from typing import Literal, Optional

class TextToSpeech(edge_tts.Communicate):
    """A simple class for producing TTS audio samples."""
    def __init__(
        self, text: str, voice: str = "zh-CN-XiaoxiaoNeural",
        *, rate: str = "-50%", volume: str = "+20%", pitch: str = "+0Hz",
        boundary: Literal['WordBoundary', 'SentenceBoundary'] = "SentenceBoundary",
        connect_timeout: Optional[int] = 10, receive_timeout: Optional[int] = 60
    ) -> None:
        """A pre-defined TTS method."""
        super().__init__(
            text, voice, rate=rate, volume=volume, pitch=pitch, boundary=boundary,
            connector=None, proxy=None, connect_timeout=connect_timeout,
            receive_timeout=receive_timeout
        )
        
    async def get_audio_bytes(self) -> bytes:
        """Returns audio bytes that can be played in an `Audio` control."""
        audio_data = bytearray()
        
        async for chunk in self.stream():
            if chunk["type"] == "audio":
                audio_data.extend(chunk["data"]) # 'data' contains the raw bytes
                
        return bytes(audio_data)
    
    async def __call__(self):
        """Calls `.get_audio_bytes()`"""
        return await self.get_audio_bytes()