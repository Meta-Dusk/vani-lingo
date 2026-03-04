from dataclasses import dataclass

@dataclass
class TTSKeys:
    rate = "tts_rate"
    volume = "tts_volume"
    pitch = "tts_pitch"

@dataclass
class AvailableKeys:
    api_key = "cerebras_api_key"
    tts = TTSKeys()
    name = "user_name"

keys = AvailableKeys()