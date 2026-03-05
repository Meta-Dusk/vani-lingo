import flet as ft

from utilities.keys import keys
from utilities.testers import is_connected
from managers.lesson import LessonManager
from managers.tts import TTSConfig, TTSData
from managers.auth import ClientAuth
from audio.audio_manager import AudioManager
from setup import setup_page, PC_PLATFORMS

class AppSetupMixin:
    def __init__(self):
        self.initialized: bool = False
        self.selected_voice: str = "Xiaoxiao"
    
    def _debug_print(self, msg: str) -> None:
        raise NotImplementedError("This method is implemented in the 'DebugMixin' class")
    
    async def _start_init(self) -> None:
        await self._page_setup()
        self._initial_setup()
        await self._get_prefs()
        await self._setup_auth()
        self._check_connection()
        self._start_client()
        await self._init_data()
        self.initialized = True
    
    def _initial_setup(self) -> None:
        self._debug_print("Starting local services...")
        self.prefs = ft.SharedPreferences()
        self.auth = ClientAuth(self.page, self.prefs)
        self.audio_manager = AudioManager(self.page, sfx_volume=1.0, music_volume=0.5, directional_sfx=False)
        self.config: TTSConfig = TTSConfig()
        self.word_tts_data = TTSData()
        self.example_tts_data = TTSData()
        self._debug_print("Starting local services... OK")
    
    async def _page_setup(self) -> None:
        self._debug_print("Setting up app...")
        setup_page(self.page)
        self._show_loading_screen()
        if self.page.platform in PC_PLATFORMS:
            await self.page.window.center()
        self._debug_print("Setting up app... OK")
    
    def _show_loading_screen(self) -> None:
        size = self.page.width * 0.3
        self.page.add(
            ft.Image("images/vani-lingo-dark.png", width=size, height=size, fit=ft.BoxFit.COVER),
            ft.Row(
                [ft.ProgressRing(width=20, height=20), self.status_text],
                alignment=ft.MainAxisAlignment.CENTER
            )
        )
        self.page.update()
    
    async def _get_prefs(self) -> None:
        if not self.prefs or not self.config:
            self._debug_print("Missing 'prefs' and 'config'.")
            return
        
        self._debug_print("Loading preferences...")    
        if await self.prefs.contains_key(keys.tts.rate):
            self.config.rate = await self.prefs.get(keys.tts.rate)
        if await self.prefs.contains_key(keys.tts.volume):
            self.config.volume = await self.prefs.get(keys.tts.volume)
        if await self.prefs.contains_key(keys.tts.pitch):
            self.config.pitch = await self.prefs.get(keys.tts.pitch)
        if await self.prefs.contains_key(keys.tts.voice):
            self.selected_voice = await self.prefs.get(keys.tts.voice)
        self._debug_print("Loading preferences... OK")
    
    async def _setup_auth(self) -> None:
        if not self.auth:
            raise Exception("Missing 'auth'!")
        
        self._debug_print("Getting API key...")
        if self.auth.get_api_key():
            self._debug_print("Getting API key... OK")
        
        if self.auth.api_key is None:
            self._debug_print("Checking for API key...")
            if await self.prefs.contains_key(keys.api_key):
                self._debug_print("Using saved API key.")
        
        if self.auth.api_key is None:
            self._debug_print("Awaiting API key...")
            await self.auth.api_check()
            self._debug_print("Awaiting API key... OK")
    
    def _check_connection(self) -> None:
        self._debug_print("Checking internet connection...")
        if not is_connected():
            self.auth.offline_mode = True
            return
        self._debug_print("Checking internet connection... OK")
    
    def _start_client(self) -> None:
        self._debug_print("Starting client...")
        self.client = self.auth.get_client()
        self.lesson_manager = LessonManager(self.client)
        if self.client is None:
            self._debug_print("Entering offline mode...")
        else:
            self._debug_print("Starting client... OK")
    
    async def _init_data(self) -> None:
        self._debug_print("Initializing data...")
        await self.lesson_manager.initialize()
        self._debug_print("Initializing data... OK")