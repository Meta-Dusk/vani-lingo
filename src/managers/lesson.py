import random, json, os, asyncio
from cerebras.cloud.sdk import AsyncCerebras
from typing import Optional, TypedDict
from dataclasses import dataclass, field

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
    
    def get_word_dict(self) -> HSKWordDict:
        return HSKWordDict(
            kanji=self.kanji,
            pinyin=self.pinyin,
            translation=self.translation
        )
    
    def get_example_dict(self) -> ExampleDataDict:
        return HSKWordDict(
            kanji=self.example,
            pinyin=self.example_pinyin,
            translation=self.example_en
        )

@dataclass
class HSKTypes:
    hsk_1: list[HSKWordDict] = field(default_factory=list)
    hsk_2: list[HSKWordDict] = field(default_factory=list)
    hsk_3: list[HSKWordDict] = field(default_factory=list)

class LessonManager:
    def __init__(self, client: Optional[AsyncCerebras]) -> None:
        self.client = client
        self.hsk_data: HSKTypes = HSKTypes()
        self._lesson_error_data = LessonDataclass(
            kanji="!", pinyin="", translation="", error="Data not loaded"
        )
        self._word_error_data: list[HSKWordDict] = [
            {"kanji": "水", "pinyin": "shuǐ", "translation": "water"}
        ]
        self.current_hsk_level: int = 1
    
    def _debug_print(self, msg: str) -> None:
        print(f"[LessonManager]: {msg}")
    
    async def initialize(self, hsk_type: Optional[int] = None, load_all: bool = True):
        """Loads data and prepares the app."""
        self._debug_print("Initializing data...")
        if not load_all and hsk_type:
            await asyncio.to_thread(self.load_hsk_data, hsk_type)
            
        elif load_all:
            self._debug_print("Loading all data...")
            for i in range(1, 4, 1):
                await asyncio.to_thread(self.load_hsk_data, i)
        self._debug_print("...Finished!")
    
    def load_hsk_data(self, hsk_type: int = 1) -> list[HSKWordDict]:
        hsk_data: list[HSKWordDict] = load_json_file(os.path.join("hsk_data", f"hsk{hsk_type}.json"))
        if not hsk_data: return self._word_error_data
        match hsk_type:
            case 1:
                self.hsk_data.hsk_1 = hsk_data
                entry_len = len(self.hsk_data.hsk_1)
                entry_text = f"{"entries" if entry_len > 1 else "entry"}"
                self._debug_print(f"Loaded HSK-{hsk_type}: {entry_len} {entry_text}.")
                return self.hsk_data.hsk_1
            case 2:
                self.hsk_data.hsk_2 = hsk_data
                entry_len = len(self.hsk_data.hsk_2)
                entry_text = f"{"entries" if entry_len > 1 else "entry"}"
                self._debug_print(f"Loaded HSK-{hsk_type}: {entry_len} {entry_text}.")
                return self.hsk_data.hsk_2
            case 3:
                self.hsk_data.hsk_3 = hsk_data
                entry_len = len(self.hsk_data.hsk_3)
                entry_text = f"{"entries" if entry_len > 1 else "entry"}"
                self._debug_print(f"Loaded HSK-{hsk_type}: {entry_len} {entry_text}.")
                return self.hsk_data.hsk_3
        
        # Final Fallback if all paths fail
        self._debug_print("CRITICAL: HSK data file not found in any expected locations.")
        self.hsk_data = self._word_error_data
        return self.hsk_data
    
    def get_random_word(self) -> HSKWordDict:
        if not self.hsk_data: return self._word_error_data
        self._debug_print(f"Getting a random word from hsk{self.current_hsk_level}...")
        return random.choice(self.get_hsk_data())
    
    def get_hsk_data(self, hsk_level: Optional[int] = None) -> list[HSKWordDict]:
        hsk_index = hsk_level if hsk_level else self.current_hsk_level
        match hsk_index:
            case 1: return self.hsk_data.hsk_1
            case 2: return self.hsk_data.hsk_2
            case 3: return self.hsk_data.hsk_3
            case _: return self._word_error_data
    
    async def get_lesson_data(self, base_word: HSKWordDict = None) -> LessonDataclass:
        if not self.hsk_data or self.client is None: return self._lesson_error_data
            
        base_word = self.get_random_word() if base_word is None else base_word
        sample_word = base_word.get("kanji", None)
        if sample_word is None: return self._lesson_error_data
        self._debug_print(f"Attempting to generate example sentence for hsk{self.current_hsk_level}...")
        
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
            content: ExampleDataDict = json.loads(content_raw.encode("utf-8").decode("utf-8"))
            self._debug_print(f"Generated: {json.dumps(content, ensure_ascii=False, indent=2)}")
            return LessonDataclass(**base_word, **content)
        
        except Exception as e:
            return LessonDataclass(**base_word, error=str(e))