import flet as ft
import asyncio, inspect
from edge_tts.srt_composer import Subtitle
from typing import Optional, Callable, Literal

from managers.tts import TextToSpeech, TTSData, TTSConfig
from managers.setup import AppSetupMixin
from components.buttons import ToggleThemeButton, HSKSegmentedButton, GreetNotifIcon
from components.displays import KPTDisplay
from components.popups import LoadingNotification
from components.inputs import SettingSlider, TTSSettings
from utilities.values import is_vani_bday
from utilities.controls import try_update
from utilities.keys import keys
from utilities.mixins import DebugMixin

TtsDataTypes = Literal["word", "example"]

class MainApp(DebugMixin, AppSetupMixin):
    def __init__(self, page: ft.Page):
        self.page = page
        self.status_text = ft.Text("")
        self.initialized: bool = False
        self._disable_ctrls: bool = False
        self._on_disable_ctrls: Optional[Callable[[bool], None]] = None
        self.word_tts_data: TTSData = None
        self.example_tts_data: TTSData = None
    
    @property
    def disable_ctrls(self,) -> bool:
        return self._disable_ctrls
    
    @disable_ctrls.setter
    def disable_ctrls(self, state: bool) -> None:
        self._disable_ctrls = state
        if not self._on_disable_ctrls: return
        if inspect.iscoroutinefunction(self._on_disable_ctrls):
            self.page.run_task(self._on_disable_ctrls, state)
        else:
            self._on_disable_ctrls(state)
    
    # * Other Methods
    def _on_debug_print(self, debug_msg: str):
        self.status_text.value = debug_msg
        try_update(self.status_text)
    
    def _build(self) -> ft.Control:
        async def on_word_listen(_) -> None:
            self.disable_ctrls = True
            await self._play_tts("word")
            self.disable_ctrls = False
        
        async def on_example_listen(_) -> None:
            self.disable_ctrls = True
            await self._play_tts("example")
            self.disable_ctrls = False
        
        self.word_kpt_display = KPTDisplay(
            title="Welcome!", kanji="按下开始", pinyin="Àn xià kāishǐ", translation="Press to start",
            on_listen=on_word_listen
        )
        self.example_kpt_display = KPTDisplay(title="Example", visible=False, on_listen=on_example_listen)
        self.word_kpt_display.listen_button.disabled = True
        self.example_kpt_display.listen_button.disabled = True
        
        self.seg_btn = HSKSegmentedButton(on_change=self._seg_btn_on_change)
        
        self.greet_btn = GreetNotifIcon()
        self.tts_config_btn = ft.PopupMenuItem(
            "TTS Config", ft.Icons.TEXTSMS, on_click=self._on_config, disabled=True
        )
        self.settings_menu_btn = ft.PopupMenuButton(
            tooltip="Show additional actions",
            icon=ft.Icons.SETTINGS,
            items=[
                ft.PopupMenuItem("Reset Preferences", ft.Icons.RESTORE, on_click=self._on_reset),
                ft.PopupMenuItem("Personalization", ft.Icons.PERSON, on_click=self._on_personalization),
                self.tts_config_btn
            ]
        )
        
        # Layouts
        self.button_row = ft.Row(
            controls=[
                ft.Button(
                    content="New Word", on_click=self._generate_word,
                    tooltip="Retrieve a new random word. Works in offline mode."
                ),
                ft.Button(
                    content="New Example", on_click=self._generate_new_example,
                    disabled=self.auth.offline_mode,
                    tooltip=(
                        "Not available in offline mode" if self.auth.offline_mode
                        else "Generate a new example sentence."
                    )
                ),
                ft.Button(
                    content="New Pair", on_click=self._generate_lesson,
                    disabled=self.auth.offline_mode,
                    tooltip=(
                        "Not available in offline mode"
                        if self.auth.offline_mode else
                        "Generate an example sentence alongside a new random word."
                    )
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN, disabled=True
        )
        
        main_content = ft.Column(
            controls=[
                ft.Text(
                    value=(
                        "You are currently offline. Restart the app to reconnect."
                        if self.auth.offline_mode else
                        "Information presented may or may not be accurate."
                    ),
                    size=12, color=ft.Colors.SECONDARY
                ),
                self.word_kpt_display,
                self.example_kpt_display,
                self.button_row,
                self.seg_btn
            ],
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH
        )
        
        return ft.SafeArea(main_content)
    
    def _toggle_disabled(self, state: bool) -> None:
        wifi_req: list[ft.Control] = [
            self.word_kpt_display.listen_button,
            self.example_kpt_display.listen_button
        ]
        other: list[ft.Control] = [
            self.button_row, self.seg_btn, self.tts_config_btn
        ]
        for ctrl in other:
            ctrl.disabled = state
            try_update(ctrl)
        if self.auth.offline_mode: return
        for ctrl in wifi_req:
            ctrl.disabled = state
            try_update(ctrl)
    
    def _get_tts_data(self, data_type: TtsDataTypes) -> tuple[TTSData, ft.Text]:
        if data_type == "word":
            return self.word_tts_data, self.word_kpt_display.text_displays.kanji
        return self.example_tts_data, self.example_kpt_display.text_displays.kanji
    
    # * Callbacks
    async def _play_tts(self, data_type: TtsDataTypes) -> None:
        data, text_control = self._get_tts_data(data_type)
        if data.audio is None or len(data.cues) == 0:
            self._debug_print("Nothing to play")
            return
        await self._play_with_highlight(text_control, data)
    
    async def _generate_tts_data(self, data_type: TtsDataTypes) -> None:
        if self.auth.offline_mode:
            self._debug_print("Can't generate TTS when in offline mode!")
            return
        try:
            if data_type == "word":
                tts = TextToSpeech(self.word_kpt_display.kanji.strip(), config=self.config)
                self.word_tts_data = await tts.get_audio_and_timing()
            else:
                tts = TextToSpeech(self.example_kpt_display.kanji.strip(), config=self.config)
                self.example_tts_data = await tts.get_audio_and_timing()
        except Exception as e:
            self._debug_print(f"TTS Initialization failed: {e}")    
    
    async def _generate_new_example(self, _) -> None:
        if self.auth.offline_mode:
            self._debug_print("Can't generate TTS when in offline mode!")
            return
        self.page.show_dialog(LoadingNotification(text="Generating a new example..."))
        self.disable_ctrls = True
        
        data = await self.lesson_manager.get_lesson_data(self.word_kpt_display.get_dict())
        
        if data.error is None:
            self.example_kpt_display.visible = True
            self.example_kpt_display.set_text(**data.get_example_dict())
            await self._generate_tts_data("example")
            self.page.pop_dialog()
            await self._play_tts("example")
            
        else:
            self._debug_print(f"Cerebras Error: {data.error}")
            notif = ft.SnackBar(
                ft.Text("Cerebras Error: Please wait a bit before trying again.", color=ft.Colors.ON_ERROR),
                duration=ft.Duration(seconds=5), behavior=ft.SnackBarBehavior.FLOATING, bgcolor=ft.Colors.ERROR,
                show_close_icon=True
            )
            self.page.show_dialog(notif)
        
        self.disable_ctrls = False
    
    async def _generate_word(self, _) -> None:
        self.page.show_dialog(LoadingNotification(text="Retrieving a new random word..."))
        self.disable_ctrls = True
        
        data = self.lesson_manager.get_random_word()
        self.word_kpt_display.set_text(**data, title="Word")
        self.example_kpt_display.visible = False
        self.example_kpt_display.update()
        await self._generate_tts_data("word")
        self.page.pop_dialog()
        await self._play_tts("word")
        self.disable_ctrls = False
    
    async def _generate_lesson(self, _) -> None:
        if self.auth.offline_mode:
            self._debug_print("Can't generate TTS when in offline mode!")
            return
        self.page.show_dialog(LoadingNotification(text="Retrieving a new random word and example..."))
        self.disable_ctrls = True
        
        data = await self.lesson_manager.get_lesson_data()
        
        if data.error is None and not self.auth.offline_mode:
            self.word_kpt_display.set_text(**data.get_word_dict(), title="Word")
            self.example_kpt_display.visible = True
            self.example_kpt_display.set_text(**data.get_example_dict())
            
            await self._generate_tts_data("word")
            await self._generate_tts_data("example")
            
            self.page.pop_dialog()
            await self._play_tts("example")
        else:
            self._debug_print(f"Cerebras Error: {data.error}")
            notif = ft.SnackBar(
                ft.Text("Cerebras Error: Please wait a bit before trying again.", color=ft.Colors.ON_ERROR),
                duration=ft.Duration(seconds=3), behavior=ft.SnackBarBehavior.FLOATING, bgcolor=ft.Colors.ERROR
            )
            self.page.show_dialog(notif)
        
        self.disable_ctrls = False
    
    async def _on_reset(self, _) -> None:
        self.page.show_dialog(LoadingNotification(text="Resetting saved preferences..."))
        if await self.prefs.clear():
            msg = "Successfully reset saved preferences!"
        else:
            msg = "Failed resetting saved preferences!"
        self.page.pop_dialog()
        self._debug_print(msg)
        self.page.show_dialog(ft.SnackBar(msg, ft.SnackBarBehavior.FLOATING))
    
    def _prepare_highlight_text(self, text_control: ft.Text, cues: list[Subtitle]) -> None:
        """Create a list of spans, one for each word/character in the cues."""
        text_control.spans = [
            ft.TextSpan(cue.content, style=ft.TextStyle(color=ft.Colors.PRIMARY)) 
            for cue in cues
        ]
        text_control.value = ""
        text_control.update()
    
    async def _play_with_highlight(self, text_control: ft.Text, tts_data: TTSData) -> None:
        prev_value = text_control.value
        self._prepare_highlight_text(text_control, tts_data.cues)
        self.audio_manager.play_sfx(tts_data.audio)
        
        start_time = asyncio.get_event_loop().time()
        for i, cue in enumerate(tts_data.cues):
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
    
    async def _on_personalization(self, _) -> None:
        async def on_save(_) -> None:
            text = tf.value.strip().lower()
            if not text or text.isspace():
                tf.error = "Cannot be empty"
            else:
                tf.error = None
            tf.update()
            self._debug_print(f"Saving name: {text}")
            if await self.prefs.set(keys.name, text):
                msg = f"Saved \"{text}\" as the 'user_name'!"
            else:
                msg = f"Failed to save \"{text}\" as the 'user_name'..."
            self.page.pop_dialog()
            self.page.show_dialog(ft.SnackBar(msg, ft.SnackBarBehavior.FLOATING))
            await self._check_bday(update_tts_data=True, play_tts=True)
        
        current_name = None
        if await self.prefs.contains_key(keys.name):
            current_name = await self.prefs.get(keys.name)
        tf = ft.TextField(
            autofocus=True, max_lines=1, max_length=30, on_submit=on_save,
            value=current_name if current_name else ""
        )
        dialog = ft.AlertDialog(
            title="Enter a Name", content=tf,
            actions=[ft.Button("Save", ft.Icons.SAVE, on_click=on_save)]
        )
        self.page.show_dialog(dialog)
    
    def _seg_btn_on_change(self, e: ft.Event[ft.SegmentedButton]) -> None:
        data_list: list[str] = e.data
        data: int = int(data_list[0])
        self._debug_print(f"Setting hsk level to: {data}")
        self.lesson_manager.current_hsk_level = data
    
    async def _check_bday(
        self, *, update_tts_data: bool = False,
        play_tts: bool = False
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
        if update_tts_data: await self._generate_tts_data("word")
        if play_tts: await self._play_tts("word")
    
    def _on_config(self, _) -> None:
        def _on_reset(_) -> None:
            config = TTSConfig()
            settings_controls.rate_slider.value = config.get_rate_int
            settings_controls.vol_slider.value = config.get_volume_int
            settings_controls.pitch_slider.value = config.get_pitch_int
            try_update(settings_controls)
        
        async def _on_confirm(_) -> None:
            self.config.set_rate(settings_controls.rate_slider.value)
            self.config.set_volume(settings_controls.vol_slider.value)
            self.config.set_pitch(settings_controls.pitch_slider.value)
            self._debug_print(f"Changing TTS config to: {self.config}")
            await self.prefs.set(keys.tts.rate, self.config.rate)
            await self.prefs.set(keys.tts.volume, self.config.volume)
            await self.prefs.set(keys.tts.pitch, self.config.pitch)
            self.page.pop_dialog()
            self.page.show_dialog(
                ft.SnackBar(
                    "Confirmed changes for the Text-to-Speech Configs!",
                    behavior=ft.SnackBarBehavior.FLOATING
                )
            )
            if self.auth.offline_mode: return
            if not self.word_kpt_display.kanji.isspace():
                await self._generate_tts_data("word")
            if not self.example_kpt_display.kanji.isspace():
                await self._generate_tts_data("example")
            if self.example_tts_data.audio and self.example_kpt_display.visible:
                await self._play_tts("example")
            elif self.word_tts_data.audio and self.word_kpt_display.visible:
                await self._play_tts("word")
        
        settings_controls = TTSSettings(config=self.config)
        
        config_dlg = ft.AlertDialog(
            title="TTS Config Settings",
            content=settings_controls,
            actions=[
                ft.Button("Reset", ft.Icons.SETTINGS_BACKUP_RESTORE, on_click=_on_reset),
                ft.Button("Confirm", ft.Icons.CHECK_CIRCLE, on_click=_on_confirm),
                ft.IconButton(
                    ft.Icons.CANCEL, icon_color=ft.Colors.PRIMARY,
                    on_click=lambda _: self.page.pop_dialog()
                )
            ],
            actions_alignment=ft.MainAxisAlignment.CENTER,
            action_button_padding=4
        )
        self.page.show_dialog(config_dlg)
    
    # * Main Method
    async def run(self) -> None:
        if not self.initialized: await self._start_init()
        
        self._debug_print("Starting the app...")
        built_app = self._build()
        await self._check_bday()
        await self._generate_tts_data("word")
        await asyncio.sleep(0.1)
        self.page.controls.clear()
        self.page.add(built_app)
        self.page.appbar = ft.AppBar(
            leading=ft.Icon(ft.Icons.WIFI_OFF if self.auth.offline_mode else ft.Icons.WIFI, size=22),
            title="VaniLingo", actions=[ToggleThemeButton(), self.settings_menu_btn, self.greet_btn]
        )
        self.page.update()
        self._on_disable_ctrls = self._toggle_disabled
        await self._play_tts("word")
        self.disable_ctrls = False
        