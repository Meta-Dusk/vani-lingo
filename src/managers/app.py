import asyncio
import flet as ft
from dataclasses import dataclass
from typing import Optional, Literal
from cerebras.cloud.sdk import AsyncCerebras
from edge_tts.srt_composer import Subtitle

from setup import setup_page, PC_PLATFORMS
from utilities.controls import try_update
from utilities.testers import is_connected
from utilities.values import is_vani_bday
from audio.audio_manager import AudioManager
from managers.auth import ClientAuth
from managers.tts import TTSConfig, TTSData, TextToSpeech
from managers.lesson import LessonManager
from components.displays import KPTDisplay
from components.buttons import ToggleThemeButton
from components.popups import LoadingNotification
from components.inputs import SettingSlider

# ! TODO: Refactor! The class doesn't even work properly...

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

@ft.control
class StatusText(ft.Text):
    is_rendered: bool = False
    
    def did_mount(self):
        self.is_rendered = True
    
    def will_unmount(self):
        self.is_rendered = False

@dataclass
class LessonSegment:
    tts_data: TTSData
    text: str

class MainApp:
    def __init__(
        self, page: ft.Page
    ) -> None:
        self.page = page
        self.status_text = StatusText("Starting Setup... 1/2")
        self.prefs: ft.SharedPreferences = None
        self.auth: ClientAuth = None
        self.audio_manager: AudioManager = None
        self.tts_config = TTSConfig()
        self.client: Optional[AsyncCerebras] = None
        self.lesson_manager: LessonManager = None
        self._block_actions: bool = False
        self.word_tts_data = TTSData()
        self.example_tts_data = TTSData()
        self.greet_btn: ft.IconButton = None
        self.word_kpt_display: KPTDisplay = None
        self.example_kpt_display: KPTDisplay = None
    
    @property
    def block_actions(self) -> bool:
        return self._block_actions
    
    @block_actions.setter
    def block_actions(self, toggle: bool) -> None:
        self._block_actions = toggle
        wifi_req_btns: list[ft.Control] = []
        other_controls: list[ft.Control] = []
        for btn in wifi_req_btns:
            if self.auth.offline_mode: break
            btn.disabled = self.block_actions
            try_update(btn)
        for ctrl in other_controls:
            ctrl.disabled = self.block_actions
            try_update(ctrl)
    
    def _get_lesson_segment(self, segment: Literal["word", "example"]) -> None:
        if segment == "word" and self.word_tts_data and self.word_kpt_display:
            return LessonSegment(
                self.word_tts_data,
                self.word_kpt_display.text_displays.kanji
            )
        elif segment == "example" and self.example_tts_data and self.example_kpt_display:
            return LessonSegment(
                self.example_tts_data,
                self.example_kpt_display.text_displays.kanji
            )
    
    def _debug_print(self, msg: str) -> None:
        print(f"[App] {msg}")
        if not self.status_text.is_rendered: return
        self.status_text.value = msg
        try_update(self.status_text)
    
    async def start_setup(self) -> None:
        await self._main_setup()
        await self._get_prefs()
        await self._setup_auth()
        await self._setup_client()
    
    async def _main_setup(self) -> None:
        self._debug_print("Setting up App...")
        setup_page(self.page)
        if self.page.platform in PC_PLATFORMS:
            await self.page.window.center()
        
        self._debug_print("Starting local services...")
        self.prefs = ft.SharedPreferences()
        self.auth = ClientAuth(self.page, self.prefs)
        self.audio_manager = AudioManager(
            self.page, sfx_volume=1.0,
            music_volume=0.5, directional_sfx=False
        )
    
    async def _setup_auth(self) -> None:
        self._debug_print("Getting API key...")
        self.auth.get_api_key()
        if self.auth.api_key is None:
            self._debug_print("Checking for API key...")
            if await self.prefs.contains_key(keys.api_key):
                self._debug_print("Using saved API key...")
                self.auth.api_key = await self.prefs.get(keys.api_key)
        
        if self.auth.api_key is None:
            self._debug_print("Awaiting API key...")
            await self.auth.api_check()
    
    async def _get_prefs(self) -> None:
        self._debug_print("Loading preferences...")
        if await self.prefs.contains_key(keys.tts.rate):
            self.tts_config.rate = await self.prefs.get(keys.tts.rate)
        if await self.prefs.contains_key(keys.tts.volume):
            self.tts_config.volume = await self.prefs.get(keys.tts.volume)
        if await self.prefs.contains_key(keys.tts.pitch):
            self.tts_config.pitch = await self.prefs.get(keys.tts.pitch)
    
    def _check_connection(self) -> None:
        self._debug_print("Checking internet connection...")
        if not is_connected(): self.auth.offline_mode = True
        if not self.word_kpt_display or self.example_kpt_display: return
        self.word_kpt_display.listen_button.disabled = self.auth.offline_mode
        self.example_kpt_display.listen_button.disabled = self.auth.offline_mode
        try_update(self.word_kpt_display, self.example_kpt_display)
    
    async def _setup_client(self) -> None:
        self._check_connection()
        self._debug_print("Starting client...")
        self.client = self.auth.get_client()
        self.lesson_manager = LessonManager(self.client)
        if self.client is None:
            self._debug_print("Entering offline mode...")
        
        self._debug_print("Initializing data...")
        await self.lesson_manager.initialize()
    
    async def _animate_tts(self, lesson_segment: LessonSegment) -> None:
        data = lesson_segment.tts_data
        if data.audio is None or len(data.cues) == 0:
            self._debug_print("Nothing to play.")
            return
        await self._play_with_highlight(text_control=lesson_segment.text, **data)
    
    async def _get_tts_data(
        self, data_type: Literal["word", "example"], text: str
    ) -> None:
        if self.auth.offline_mode:
            self._debug_print("Can't generate TTS when in offline mode!")
            return
        try:
            tts = TextToSpeech(text, config=self.tts_config)
            if data_type == "word":
                self.word_tts_data = tts.get_audio_and_timing()
            elif data_type == "example":
                self.example_tts_data = tts.get_audio_and_timing()
        except Exception as e:
            self._debug_print(f"TTS Initialization failed: {e}")
    
    async def _generate_lesson(self, data_type: Literal["word", "example"]) -> None:
        self.page.show_dialog(LoadingNotification(text="Retrieving a new random word..."))
        self.block_actions = True
        
        if data_type == "word":
            data = self.lesson_manager.get_random_word()
            self.word_kpt_display.set_text(**data, title="Word")
            self.example_kpt_display.visible = False
            try_update(self.example_kpt_display)
            await self._get_tts_data("word", data.get("kanji").strip())
            if self.word_tts_data.audio and not self.auth.offline_mode:
                self.audio_manager.play_sfx(self.word_tts_data.audio)
            
            self.page.pop_dialog()
            await self._animate_tts(self._get_lesson_segment("word"))
        
        elif data_type == "example":
            data = await self.lesson_manager.get_lesson_data()
            if data.error is None and not self.auth.offline_mode:
                self.word_kpt_display.set_text(
                    data.kanji, data.pinyin, data.translation,
                    title="Word"
                )
                self.example_kpt_display.visible = True
                self.example_kpt_display.set_text(
                    data.example, data.example_pinyin, data.example_en
                )
                
                await self._get_tts_data("word", data.kanji.strip())
                await self._get_tts_data("example", data.example.strip())
                
                if self.example_tts_data.audio:
                    self.audio_manager.play_sfx(self.example_tts_data.audio)
                self.page.pop_dialog()
                await self._animate_tts(self._get_lesson_segment("example"))
        self.block_actions = False
    
    async def _on_reset(self, _) -> None:
        self.page.show_dialog(LoadingNotification(text="Resetting saved preferences..."))
        if await self.prefs.clear():
            msg = "Successfully reset saved preferences!"
        else:
            msg = "Failed resetting saved preferences!"
        self.page.pop_dialog()
        self._debug_print(msg)
        self.page.show_dialog(ft.SnackBar(msg, ft.SnackBarBehavior.FLOATING))
    
    def _prepare_highlight_text(
        self, text_control: ft.Text, cues: list[Subtitle]
    ) -> None:
        # Create a list of spans, one for each word/character in the cues
        text_control.spans = [
            ft.TextSpan(cue.content, style=ft.TextStyle(color=ft.Colors.PRIMARY)) 
            for cue in cues
        ]
        text_control.value = "" # Clear the main value so only spans show
        text_control.update()
    
    async def _play_with_highlight(
        self, text_control: ft.Text,
        audio_bytes: bytes, cues: list[Subtitle]
    ) -> None:
        prev_value = text_control.value
        self._prepare_highlight_text(text_control, cues)
        
        self.audio_manager.play_sfx(audio_bytes)
        
        start_time = asyncio.get_event_loop().time()
        for i, cue in enumerate(cues):
            # Calculate how long to wait before highlighting this word
            wait_time = (cue.start.total_seconds()) - (asyncio.get_event_loop().time() - start_time)
            if wait_time > 0: await asyncio.sleep(wait_time)
                
            # Update the UI to highlight the current word
            text_control.spans[i].style.color = ft.Colors.INVERSE_PRIMARY
            text_control.spans[i].style.weight = ft.FontWeight.BOLD
            
            if i > 0: # Color finished words differently
                text_control.spans[i-1].style.color = ft.Colors.OUTLINE
                text_control.spans[i-1].style.weight = ft.FontWeight.NORMAL
                
            text_control.update()
            
        await asyncio.sleep(cue.end.total_seconds() - cue.start.total_seconds())
        text_control.spans.clear()
        text_control.value = prev_value
        text_control.update()
    
    def _seg_btn_on_change(self, e: ft.Event[ft.SegmentedButton]) -> None:
        data_list: list[str] = e.data
        data: int = int(data_list[0])
        self._debug_print(f"Setting hsk level to: {data}")
        self.lesson_manager.current_hsk_level = data
    
    async def _check_bday(
        self, *, update_tts_data: bool = False, play_tts: bool = False
    ) -> None:
        name: Optional[str] = None
        if await self.prefs.contains_key(keys.name):
            name = await self.prefs.get(keys.name)
        if (
            not is_vani_bday() or
            name is None or
            name.isspace() or
            not name.strip().lower() == "vani"
        ): return
        self.word_kpt_display.set_text(
            kanji="生日快乐, Vani!",
            pinyin="Shēngrì kuàilè, Vani!",
            translation="Happy birthday, Vani!",
            title="Hello Vani"
        )
        self.greet_btn.visible = True
        try_update(self.greet_btn)
        if update_tts_data: await self._get_tts_data("word", self.word_kpt_display.kanji)
        if play_tts: await self._animate_tts(self._get_lesson_segment("word"))
    
    def _open_greeting(self, e: ft.Event[ft.IconButton]) -> None:
        dialog = ft.AlertDialog(
            title="Happy Birthday, Vani!",
            content=ft.Image("images/bday_cake.png", fit=ft.BoxFit.CONTAIN),
            actions=[
                ft.Button(
                    "Thank you", icon=ft.Icons.FACE_3_ROUNDED,
                    on_click=lambda _: self.page.pop_dialog()
                )
            ]
        )
        e.control.badge = None
        try: e.control.update()
        except RuntimeError: pass
        self.page.show_dialog(dialog)
    
    def _on_config(self, _) -> None:
        def on_reset(_) -> None:
            rate_slider.value = -50
            volume_slider.value = 20
            pitch_slider.value = 0
            settings_controls.update()
        
        async def on_confirm(_) -> None:
            self.tts_config.set_rate(rate_slider.value)
            self.tts_config.set_volume(volume_slider.value)
            self.tts_config.set_pitch(pitch_slider.value)
            self._debug_print(f"Changing TTS config to: {self.tts_config}")
            await self.prefs.set(keys.tts.rate, self.tts_config.rate)
            await self.prefs.set(keys.tts.volume, self.tts_config.volume)
            await self.prefs.set(keys.tts.pitch, self.tts_config.pitch)
            self.page.pop_dialog()
            self.page.show_dialog(
                ft.SnackBar(
                    "Confirmed changes for the Text-to-Speech Configs!",
                    behavior=ft.SnackBarBehavior.FLOATING
                )
            )
            if self.auth.offline_mode: return
            if not self.word_kpt_display.kanji.isspace():
                await self._get_tts_data("word", self.word_kpt_display.kanji)
            if not self.example_kpt_display.kanji.isspace():
                await self._get_tts_data("example", self.example_kpt_display.kanji)
            if self.example_tts_data.audio:
                await self._animate_tts(self._get_lesson_segment("example"))
            elif self.word_tts_data.audio:
                await self._animate_tts(self._get_lesson_segment("word"))
        
        rate_slider = SettingSlider(value=self.tts_config.get_rate_int)
        volume_slider = SettingSlider(value=self.tts_config.get_volume_int)
        pitch_slider = SettingSlider(value=self.tts_config.get_pitch_int)
        spacer_val: ft.Number = 70
        
        settings_controls = ft.Column(
            controls=[
                ft.Row([ft.Text("Rate", width=spacer_val), rate_slider]),
                ft.Row([ft.Text("Volume", width=spacer_val), volume_slider]),
                ft.Row([ft.Text("Pitch", width=spacer_val), pitch_slider])
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER, tight=True
        )
        
        config_dlg = ft.AlertDialog(
            modal=True, title="TTS Config Settings",
            content=settings_controls,
            actions=[
                ft.Button("Reset", ft.Icons.SETTINGS_BACKUP_RESTORE, on_click=on_reset),
                ft.Button("Confirm", ft.Icons.CHECK_CIRCLE, on_click=on_confirm),
                ft.Button("Cancel", ft.Icons.CANCEL, on_click=lambda _: self.page.pop_dialog())
            ],
            actions_alignment=ft.MainAxisAlignment.CENTER,
            action_button_padding=4
        )
        self.page.show_dialog(config_dlg)
    
    def _on_personalization(self, _) -> None:        
        async def on_save(_) -> None:
            text = tf.value.strip().lower()
            if not text or text.isspace():
                tf.error = "Cannot be empty"
            else:
                tf.error = None
            tf.update()
            self._debug_print(f"Saving name: {text}")
            if await self.prefs.set("user_name", text):
                msg = f"Saved \"{text}\" as the 'user_name'!"
            else:
                msg = f"Failed to save \"{text}\" as the 'user_name'..."
            self.page.pop_dialog()
            self.page.show_dialog(ft.SnackBar(msg, ft.SnackBarBehavior.FLOATING))
            await self._check_bday(update_tts_data=True, play_tts=True)
        
        tf = ft.TextField(
            autofocus=True, max_lines=1, max_length=30, on_submit=on_save
        )
        dialog = ft.AlertDialog(
            title="Enter a Name", content=tf,
            actions=[ft.Button("Save", ft.Icons.SAVE, on_click=on_save)]
        )
        self.page.show_dialog(dialog)
    
    async def build(self) -> None:
        async def on_listen_word(_) -> None:
            await self._animate_tts(self._get_lesson_segment("word"))
        
        async def on_listen_example(_) -> None:
            await self._animate_tts(self._get_lesson_segment("example"))
        
        self.word_kpt_display = KPTDisplay(
            title="Welcome!", kanji="按下开始", pinyin="Àn xià kāishǐ", translation="Press to start",
            on_listen=on_listen_word
        )
        self.example_kpt_display = KPTDisplay(title="Example", visible=False, on_listen=on_listen_example)
        
        seg_btn = ft.SegmentedButton(
            allow_multiple_selection=False,
            selected_icon=ft.Icons.CHECK_SHARP,
            selected=["1"],
            segments=[
                ft.Segment(value="1", label="HSK 1", icon=ft.Icons.LOOKS_ONE_SHARP),
                ft.Segment(value="2", label="HSK 2", icon=ft.Icons.LOOKS_TWO_SHARP),
                ft.Segment(value="3", label="HSK 3", icon=ft.Icons.LOOKS_3_SHARP)
            ],
            on_change=self._seg_btn_on_change
        )
        greet_btn = ft.IconButton(
            ft.Icons.NOTIFICATION_IMPORTANT, visible=False,
            on_click=self._open_greeting,
            badge=ft.Badge(small_size=10)
        )
        tts_config_btn = ft.PopupMenuItem(
            "TTS Config", ft.Icons.TEXTSMS,
            on_click=self._on_config
        )
        settings_menu_btn = ft.PopupMenuButton(
            tooltip="Show additional actions",
            icon=ft.Icons.SETTINGS,
            items=[
                ft.PopupMenuItem("Reset Preferences", ft.Icons.RESTORE, on_click=self._on_reset),
                ft.PopupMenuItem("Personalization", ft.Icons.PERSON, on_click=self._on_personalization),
                tts_config_btn
            ]
        )
        
        async def generate_word(_) -> None:
            await self._generate_lesson("word")
        
        async def generate_example(_) -> None:
            await self._generate_lesson("example")
        
        button_row = ft.Row(
            controls=[
                ft.Button(
                    content="New Word", on_click=generate_word,
                    tooltip="Retrieve a new random word. Works in offline mode."
                ),
                ft.Button(
                    content="New Example", on_click=generate_example,
                    disabled=self.auth.offline_mode, tooltip=(
                        "Not available in offline mode" if self.auth.offline_mode
                        else "Generate an example sentence alongside a new random word."
                    )
                )
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
        )
        
        main_content = ft.Column(
            controls=[
                ft.Text(
                    value=(
                        "You are currently offline. Restart the app to reconnect." if self.auth.offline_mode
                        else "Information presented may or may not be accurate."
                    ),
                    size=12, color=ft.Colors.SECONDARY
                ),
                self.word_kpt_display,
                self.example_kpt_display,
                button_row,
                seg_btn
            ],
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH
        )
        
        self._debug_print("Starting App!")
        await asyncio.sleep(0.1)
        self.page.controls.clear()
        self.page.add(ft.SafeArea(main_content))
        self.page.appbar = ft.AppBar(
            leading=ft.Icon(ft.Icons.WIFI_OFF if self.auth.offline_mode else ft.Icons.WIFI, size=22),
            title="VaniLingo", actions=[ToggleThemeButton(), settings_menu_btn, greet_btn]
        )
        self.page.update()
        await self._animate_tts(self._get_lesson_segment("word"))
        

if __name__ == "__main__":
    async def main(page: ft.Page) -> None:
        app = MainApp(page)
        await app.start_setup()
        await app.build()
        
    ft.run(main, assets_dir="../assets")