import random, json, os, asyncio
from cerebras.cloud.sdk import AsyncCerebras
from typing import Optional, TypedDict
from dataclasses import dataclass

from utilities.file_management import load_json_file

class HSKWordDict(TypedDict):
    kanji: str
    pinyin: str
    translation: str

class ExampleDataDict(TypedDict):
    example: str
    example_pinyin: str
    example_en: str

@dataclass
class LessonDataclass:
    kanji: str
    pinyin: str
    translation: str
    example: Optional[str] = None
    example_pinyin: Optional[str] = None
    example_en: Optional[str] = None
    error: Optional[str] = None

class LessonManager:
    def __init__(self, client: Optional[AsyncCerebras]) -> None:
        self.client = client
        self.hsk_data: list[HSKWordDict] = []
        self._lesson_error_data = LessonDataclass(
            kanji="!", pinyin="", translation="", error="Data not loaded"
        )
        self._word_error_data: list[HSKWordDict] = [
            {"kanji": "水", "pinyin": "shuǐ", "translation": "water"}
        ]
    
    def _debug_print(self, msg: str) -> None:
        print(f"[LessonManager]: {msg}")
    
    async def initialize(self, hsk_type: int = 1):
        """Loads data and prepares the app."""
        await asyncio.to_thread(self.load_hsk_data, f"hsk{hsk_type}.json")
        entry_len = len(self.hsk_data)
        entry_text = f"{"entries" if entry_len > 1 else "entry"}"
        self._debug_print(f"Generated HSK-{hsk_type}: {entry_len} {entry_text}.")
    
    def load_hsk_data(self, file_name: str = "hsk1.json") -> list[HSKWordDict]:
        hsk_data = load_json_file(os.path.join("hsk_data", file_name))
        if hsk_data:
            self.hsk_data = hsk_data
            return self.hsk_data
        
        # Final Fallback if all paths fail
        self._debug_print("CRITICAL: HSK data file not found in any expected locations.")
        self.hsk_data = self._word_error_data
        return self.hsk_data
    
    def get_random_word(self) -> HSKWordDict:
        if not self.hsk_data: return self._word_error_data
        return random.choice(self.hsk_data)
    
    async def get_lesson_data(self) -> LessonDataclass:
        if not self.hsk_data or self.client is None: return self._lesson_error_data
            
        base_word = random.choice(self.hsk_data)
        sample_word = base_word.get("kanji", None)
        if sample_word is None: return self._lesson_error_data
        
        system_prompt = (
            "You are a Chinese teacher. Return ONLY a JSON object. "
            "CRITICAL: Do not use Unicode escape sequences. Use raw UTF-8 Chinese characters. "
            "If you cannot return valid Chinese, return an empty string. "
            "Format: {'example': 'Chinese here', 'example_pinyin': 'Pinyin here', 'example_en': 'English here'} "
            "As for the 'example_pinyin', make sure to use English equivalent for punctuations. "
            "An example would be using '.' instead of '。'. Don't forget about the intonations, where an example "
            "Kanji '水' should have Pinyin of 'shuǐ'."
        )
        user_prompt = f"Create a very simple beginner sentence using the word '{sample_word}'."
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-oss-120b",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                stream=False,
                response_format={"type": "json_object"}
            )
            content_raw = response.choices[0].message.content
            self._debug_print(f"\nReceived: {json.dumps(json.loads(content_raw), ensure_ascii=False, indent=2)}")
            
            content: ExampleDataDict = json.loads(content_raw.encode("utf-8").decode("utf-8"))
            self._debug_print(f"Generated: {json.dumps(content, ensure_ascii=False, indent=2)}\n")
            
            return LessonDataclass(**base_word, **content)
        
        except Exception as e:
            return LessonDataclass(**base_word, error=str(e))