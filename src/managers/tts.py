import edge_tts, re
from typing import Literal, Optional

class TextToSpeech(edge_tts.Communicate):
    """A simple class for producing TTS audio samples."""
    def __init__(
        self, text: str, voice: str = "zh-CN-XiaoxiaoNeural",
        *, rate: str = "-50%", volume: str = "+20%", pitch: str = "+0Hz",
        boundary: Literal['WordBoundary', 'SentenceBoundary'] = "WordBoundary",
        connect_timeout: Optional[int] = 10, receive_timeout: Optional[int] = 60
    ) -> None:
        """A pre-defined TTS method."""
        super().__init__(
            text, voice, rate=rate, volume=volume, pitch=pitch, boundary=boundary,
            connector=None, proxy=None, connect_timeout=connect_timeout,
            receive_timeout=receive_timeout
        )
        self.text = text
        
    async def get_audio_and_timing(self):
        """Returns audio bytes that can be played in an `Audio` control."""
        audio_data = bytearray()
        submaker = edge_tts.SubMaker()
        
        current_pos = 0
        
        async for chunk in self.stream():
            if chunk["type"] == "audio":
                audio_data.extend(chunk["data"]) # 'data' contains the raw bytes
            elif chunk["type"] in ["WordBoundary", "SentenceBoundary"]:
                text_to_find = chunk["text"]
            
                # 1. Find the starting position of this word in the original text
                # We search starting from current_pos to avoid matching previous occurrences
                start_idx = self.text.find(text_to_find, current_pos)
                
                if start_idx != -1:
                    # 2. Identify the end of the word
                    end_idx = start_idx + len(text_to_find)
                    
                    # 3. Look ahead for trailing punctuation/symbols
                    # We stop when we hit a 'word character' (isalnum) or whitespace
                    while end_idx < len(self.text):
                        char = self.text[end_idx]
                        if not (char.isalnum() or char.isspace()):
                            end_idx += 1
                        else:
                            break
                    
                    # 4. Capture everything from the previous word's end to the current word's end.
                    # This ensures leading punctuation (like brackets) is also included.
                    chunk["text"] = self.text[current_pos:end_idx]
                    current_pos = end_idx
                
                # This records exactly when each word starts and ends
                submaker.feed(chunk)
                
        return bytes(audio_data), submaker.cues
    
    async def __call__(self):
        """Calls `.get_audio_bytes()`"""
        return await self.get_audio_and_timing()