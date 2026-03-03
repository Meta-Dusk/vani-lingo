import edge_tts
from edge_tts.srt_composer import Subtitle
from typing import Literal, Optional
from dataclasses import dataclass, field

from utilities.values import clamp

@dataclass
class TTSData:
    audio: bytes = None
    cues: list[Subtitle] = field(default_factory=list)

@dataclass
class TTSConfig:
    rate: str = "-50%"
    volume: str = "+20%"
    pitch: str = "+0Hz"
    
    def set_rate(self, rate: int = 0) -> None:
        rate = int(clamp(rate, -100, 100))
        self.rate = f"{rate:+}%"
    
    def set_volume(self, volume: int = 0) -> None:
        volume = int(clamp(volume, -100, 100))
        self.volume = f"{volume:+}%"
    
    def set_pitch(self, pitch: int = 0) -> None:
        pitch = int(clamp(pitch, -100, 100))
        self.pitch = f"{pitch:+}Hz"
    
    @property
    def get_rate_int(self) -> int:
        return int(self.rate.strip("%+"))
    
    @property
    def get_volume_int(self) -> int:
        return int(self.volume.strip("%+"))
    
    @property
    def get_pitch_int(self) -> int:
        return int(self.pitch.strip("Hz+"))
    
    # This enables **self unpacking
    def keys(self):
        return ("rate", "volume", "pitch")
    
    def __getitem__(self, key):
        if key in self.keys():
            return getattr(self, key)
        raise KeyError(f"Invalid config key: {key}")

class TextToSpeech(edge_tts.Communicate):
    """A simple class for producing TTS audio samples."""
    def __init__(
        self, text: str, voice: str = "zh-CN-XiaoxiaoNeural",
        *, config: TTSConfig = TTSConfig(),
        boundary: Literal['WordBoundary', 'SentenceBoundary'] = "WordBoundary",
        connect_timeout: Optional[int] = 10, receive_timeout: Optional[int] = 60
    ) -> None:
        super().__init__(
            text, voice, **config, boundary=boundary, connector=None, proxy=None,
            connect_timeout=connect_timeout, receive_timeout=receive_timeout
        )
        self.text = text
    
    def _debug_print(self, msg: str) -> None:
        print(f"[TextToSpeech] {msg}")
    
    async def get_audio_and_timing(self) -> TTSData:
        """Returns audio bytes and a list of `Subtitle` objects."""
        audio_data = bytearray()
        submaker = edge_tts.SubMaker()
        self._debug_print(f"Attempting to make TTSData for: {self.text}")
        current_pos = 0
        
        async for chunk in self.stream():
            if chunk["type"] == "audio":
                audio_data.extend(chunk["data"]) # 'data' contains the raw bytes
            elif chunk["type"] in ["WordBoundary", "SentenceBoundary"]:
                text_to_find = chunk["text"]
            
                # Find the starting position of this word in the original text
                # We search starting from current_pos to avoid matching previous occurrences
                start_idx = self.text.find(text_to_find, current_pos)
                
                if start_idx != -1:
                    # Identify the end of the word
                    end_idx = start_idx + len(text_to_find)
                    
                    # Look ahead for trailing punctuation/symbols
                    # We stop when we hit a 'word character' (isalnum) or whitespace
                    while end_idx < len(self.text):
                        char = self.text[end_idx]
                        if not (char.isalnum() or char.isspace()):
                            end_idx += 1
                        else:
                            break
                    
                    # Capture everything from the previous word's end to the current word's end.
                    # This ensures leading punctuation (like brackets) is also included.
                    chunk["text"] = self.text[current_pos:end_idx]
                    current_pos = end_idx
                
                # This records exactly when each word starts and ends
                submaker.feed(chunk)
                
        return TTSData(bytes(audio_data), submaker.cues)