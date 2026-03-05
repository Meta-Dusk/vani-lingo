import flet as ft
import asyncio, inspect
from edge_tts.srt_composer import Subtitle
from typing import Optional, Callable

from managers.tts import TextToSpeech, TTSData
from managers.setup import AppSetupMixin
from components.buttons import ToggleThemeButton
from components.displays import KPTDisplay
from components.popups import LoadingNotification
from components.inputs import SettingSlider
from utilities.values import is_vani_bday
from utilities.controls import try_update
from utilities.keys import keys
from utilities.mixins import DebugMixin

class MainApp(DebugMixin, AppSetupMixin):
    def __init__(self, page: ft.Page):
        self.page = page
        self.status_text = ft.Text("")
        self.initialized: bool = False
        self._disable_ctrls: bool = False
        self._on_disable_ctrls: Optional[Callable[[bool], None]] = None
    
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
        self.word_kpt_display = KPTDisplay(
            title="Welcome!", kanji="按下开始", pinyin="Àn xià kāishǐ", translation="Press to start",
            on_listen=self._play_word
        )
        self.example_kpt_display = KPTDisplay(
            title="Example", visible=False,
            on_listen=self._play_example
        )
        self.word_kpt_display.listen_button.disabled = True
        self.example_kpt_display.listen_button.disabled = True
        
        self.seg_btn = ft.SegmentedButton(
            allow_multiple_selection=False, selected_icon=ft.Icons.CHECK_SHARP,
            selected=["1"],
            on_change=self._seg_btn_on_change,
            disabled=True,
            segments=[
                ft.Segment(value="1", label="HSK 1", icon=ft.Icons.LOOKS_ONE_SHARP),
                ft.Segment(value="2", label="HSK 2", icon=ft.Icons.LOOKS_TWO_SHARP),
                ft.Segment(value="3", label="HSK 3", icon=ft.Icons.LOOKS_3_SHARP)
            ]
        )
        
        self.greet_btn = ft.IconButton(
            ft.Icons.NOTIFICATION_IMPORTANT, visible=False,
            on_click=self._open_greeting,
            badge=ft.Badge(small_size=10)
        )
        self.tts_config_btn = ft.PopupMenuItem(
            "TTS Config", ft.Icons.TEXTSMS,
            on_click=self._on_config,
            disabled=True
        )
        self.settings_menu_btn = ft.PopupMenuButton(
            tooltip="Show additional actions",
            icon=ft.Icons.SETTINGS,
            items=[
                ft.PopupMenuItem(
                    "Reset Preferences", ft.Icons.RESTORE,
                    on_click=self._on_reset
                ),
                ft.PopupMenuItem(
                    "Personalization", ft.Icons.PERSON,
                    on_click=self._on_personalization
                ),
                self.tts_config_btn
            ]
        )
        
        # Layouts
        self.button_row = ft.Row(
            controls=[
                ft.Button(
                    content="New Word",
                    on_click=self.generate_word,
                    tooltip="Retrieve a new random word. Works in offline mode."
                ),
                ft.Button(
                    content="New Example",
                    on_click=self._generate_new_example,
                    disabled=self.auth.offline_mode,
                    tooltip=(
                        "Not available in offline mode" if self.auth.offline_mode
                        else "Generate a new example sentence."
                    )
                ),
                ft.Button(
                    content="New Pair",
                    on_click=self.generate_lesson,
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
    
    # * Callbacks
    async def _play_word(self, _) -> None:
        data = self.word_tts_data
        if data.audio is None or len(data.cues) == 0:
            self._debug_print("Nothing to play")
            return
        await self._play_with_highlight(
            text_control=self.word_kpt_display.text_displays.kanji,
            tts_data=data
        )
    
    async def _play_example(self, _) -> None:
        data = self.example_tts_data
        if data.audio is None or len(data.cues) == 0:
            self._debug_print("Nothing to play")
            return
        await self._play_with_highlight(
            text_control=self.example_kpt_display.text_displays.kanji,
            tts_data=data
        )
    
    async def _get_word_tts(self, text: str) -> None:
        if self.auth.offline_mode:
            self._debug_print("Can't generate TTS when in offline mode!")
            return
        try:
            tts = TextToSpeech(text, config=self.config)
            self.word_tts_data = await tts.get_audio_and_timing()
        except Exception as e:
            self._debug_print(f"TTS Initialization failed: {e}")
    
    async def _get_example_tts(self, text: str) -> None:
        if self.auth.offline_mode:
            self._debug_print("Can't generate TTS when in offline mode!")
            return
        try:
            tts = TextToSpeech(text, config=self.config)
            self.example_tts_data = await tts.get_audio_and_timing()
        except Exception as e:
            self._debug_print(f"TTS Initialization failed: {e}")
    
    async def _generate_new_example(self, _) -> None:
        self.page.show_dialog(LoadingNotification(text="Generating a new example..."))
        if self.auth.offline_mode: return
        
        self.disable_ctrls = True
        
        data = await self.lesson_manager.get_lesson_data(self.word_kpt_display.get_dict())
        
        if data.error is None:
            self.example_kpt_display.visible = True
            self.example_kpt_display.set_text(data.example, data.example_pinyin, data.example_en)
            await self._get_example_tts(data.example.strip())
            self.page.pop_dialog()
            
            try:
                tts = TextToSpeech(self.example_kpt_display.kanji, config=self.config)
                self.example_tts_data = await tts.get_audio_and_timing()
                await self._play_example(_)
            except Exception as e:
                self._debug_print(f"TTS Initialization failed: {e}")
            
        else:
            self._debug_print(f"Cerebras Error: {data.error}")
            notif = ft.SnackBar(
                ft.Text("Cerebras Error: Please wait a bit before trying again.", color=ft.Colors.ON_ERROR),
                duration=ft.Duration(seconds=3), behavior=ft.SnackBarBehavior.FLOATING, bgcolor=ft.Colors.ERROR
            )
            self.page.show_dialog(notif)
        
        self.disable_ctrls = False
    
    async def generate_word(self, _) -> None:
        self.page.show_dialog(LoadingNotification(text="Retrieving a new random word..."))
        self.disable_ctrls = True
        
        data = self.lesson_manager.get_random_word()
        self.word_kpt_display.set_text(**data, title="Word")
        self.example_kpt_display.visible = False
        self.example_kpt_display.update()
        
        await self._get_word_tts(data.get("kanji").strip())
        
        if self.word_tts_data.audio and not self.auth.offline_mode:
            self.audio_manager.play_sfx(self.word_tts_data.audio)
        
        self.page.pop_dialog()
        await self._play_word(_)
        self.disable_ctrls = False
    
    async def generate_lesson(self, _) -> None:
        self.page.show_dialog(LoadingNotification(text="Retrieving a new random word and example..."))
        self.disable_ctrls = True
        
        data = await self.lesson_manager.get_lesson_data()
        
        if data.error is None and not self.auth.offline_mode:
            self.word_kpt_display.set_text(data.kanji, data.pinyin, data.translation, title="Word")
            self.example_kpt_display.visible = True
            self.example_kpt_display.set_text(data.example, data.example_pinyin, data.example_en)
            
            await self._get_word_tts(data.kanji.strip())
            await self._get_example_tts(data.example.strip())
            
            if self.example_tts_data.audio:
                self.audio_manager.play_sfx(self.example_tts_data.audio)
            self.page.pop_dialog()
        else:
            self._debug_print(f"Cerebras Error: {data.error}")
            notif = ft.SnackBar(
                ft.Text("Cerebras Error: Please wait a bit before trying again.", color=ft.Colors.ON_ERROR),
                duration=ft.Duration(seconds=3), behavior=ft.SnackBarBehavior.FLOATING, bgcolor=ft.Colors.ERROR
            )
            self.page.show_dialog(notif)
        
        await self._play_example(_)
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
        # Create a list of spans, one for each word/character in the cues
        text_control.spans = [
            ft.TextSpan(cue.content, style=ft.TextStyle(color=ft.Colors.PRIMARY)) 
            for cue in cues
        ]
        text_control.value = "" # Clear the main value so only spans show
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
    
    def _on_personalization(self, _) -> None:        
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
        
        tf = ft.TextField(
            autofocus=True, max_lines=1, max_length=30, on_submit=on_save
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
    
    async def _check_bday(self, *, update_tts_data: bool = False, play_tts: bool = False) -> None:
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
        if update_tts_data: await self._get_word_tts(self.word_kpt_display.kanji)
        if play_tts: await self._play_word(None)
    
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
        def _on_reset(_) -> None:
            rate_slider.value = -50
            volume_slider.value = 20
            pitch_slider.value = 0
            settings_controls.update()
        
        async def _on_confirm(_) -> None:
            self.config.set_rate(rate_slider.value)
            self.config.set_volume(volume_slider.value)
            self.config.set_pitch(pitch_slider.value)
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
                await self._get_word_tts(self.word_kpt_display.kanji)
            if not self.example_kpt_display.kanji.isspace():
                await self._get_example_tts(self.example_kpt_display.kanji)
            if self.example_tts_data.audio: await self._play_example(_)
            elif self.word_tts_data.audio: await self._play_word(_)
        
        rate_slider = SettingSlider(value=self.config.get_rate_int)
        volume_slider = SettingSlider(value=self.config.get_volume_int)
        pitch_slider = SettingSlider(value=self.config.get_pitch_int)
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
            title="TTS Config Settings",
            content=settings_controls,
            actions=[
                ft.Button("Reset", ft.Icons.SETTINGS_BACKUP_RESTORE, on_click=_on_reset),
                ft.Button("Confirm", ft.Icons.CHECK_CIRCLE, on_click=_on_confirm),
                ft.IconButton(ft.Icons.CANCEL, on_click=lambda _: self.page.pop_dialog(), icon_color=ft.Colors.PRIMARY)
            ],
            actions_alignment=ft.MainAxisAlignment.CENTER,
            action_button_padding=4
        )
        self.page.show_dialog(config_dlg)
    
    # * Main Method
    async def run(self) -> None:
        if not self.initialized:
            self._debug_print("App not yet initialized!")
            return
        
        self._debug_print("Starting the app...")
        built_app = self._build()
        await self._check_bday()
        await self._get_word_tts(self.word_kpt_display.kanji)
        await asyncio.sleep(0.1)
        self.page.controls.clear()
        self.page.add(built_app)
        self.page.appbar = ft.AppBar(
            leading=ft.Icon(ft.Icons.WIFI_OFF if self.auth.offline_mode else ft.Icons.WIFI, size=22),
            title="VaniLingo", actions=[ToggleThemeButton(), self.settings_menu_btn, self.greet_btn]
        )
        self.page.update()
        self._on_disable_ctrls = self._toggle_disabled
        await self._play_word(None)
        self.disable_ctrls = False
        