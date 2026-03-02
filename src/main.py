import flet as ft
import asyncio
from edge_tts.srt_composer import Subtitle

from setup import setup_page, PC_PLATFORMS
from audio.audio_manager import AudioManager
from managers.tts import TextToSpeech, TTSData
from managers.auth import ClientAuth
from managers.lesson import LessonManager
from components.buttons import ToggleThemeButton
from components.displays import KPTDisplay
from components.popups import LoadingNotification
from utilities.testers import is_connected
from utilities.values import is_vani_bday


# TODO: Clean up
async def main(page: ft.Page) -> None:
    setup_page(page)
    status_txt = ft.Text("Starting Setup... 1/2")
    page.add(ft.ProgressRing(width=100, height=100), status_txt)
    if page.platform in PC_PLATFORMS:
        await page.window.center()
    
    def debug_print(text: str) -> None:
        print(f"[Main]: {text}")
    
    def change_status(text: str) -> None:
        nonlocal status_txt
        debug_print(text)
        status_txt.value = text
        status_txt.update()
    
    change_status("Starting local services...")
    prefs = ft.SharedPreferences()
    auth = ClientAuth(page, prefs)
    audio_manager = AudioManager(page, sfx_volume=1.0, music_volume=0.5, directional_sfx=False)
    block_actions: bool = False
    
    change_status("Getting API key...")
    auth.get_api_key()
    
    if auth.api_key is None:
        change_status("Checking for API key...")
        if await prefs.contains_key("cerebras_api_key"):
            change_status("Using saved API key...")
            auth.api_key = await prefs.get(key="cerebras_api_key")
    
    if auth.api_key is None:
        change_status("Awaiting API key...")
        await auth.api_check()
    
    change_status("Checking internet connection...")
    if not is_connected():
        auth.offline_mode = True
    
    change_status("Starting client...")
    client = auth.get_client()
    lesson_manager = LessonManager(client)
    if client is None:
        change_status("Entering offline mode...")
    
    change_status("Initializing Data...")
    await lesson_manager.initialize()
    
    # Callbacks
    def toggle_block() -> None:
        wifi_req_btns: list[ft.IconButton] = [
            word_kpt_display.listen_button,
            example_kpt_display.listen_button
        ]
        other_controls: list[ft.Control] = [
            button_row,
            seg_btn
        ]
        for btn in wifi_req_btns:
            if auth.offline_mode: break
            btn.disabled = block_actions
            btn.update()
        for control in other_controls:
            control.disabled = block_actions
            control.update()
    
    async def play_word(_) -> None:
        nonlocal block_actions
        if word_tts_data.audio is None or len(word_tts_data.cues) == 0:
            debug_print("Nothing to play")
            return
        block_actions = True
        toggle_block()
        await play_with_highlight(
            text_control=word_kpt_display.text_displays.kanji,
            audio_bytes=word_tts_data.audio,
            cues=word_tts_data.cues
        )
        block_actions = False
        toggle_block()
    
    async def play_example(_) -> None:
        nonlocal block_actions
        if example_tts_data.audio is None or len(example_tts_data.cues) == 0:
            debug_print("Nothing to play")
            return
        block_actions = True
        toggle_block()
        await play_with_highlight(
            text_control=example_kpt_display.text_displays.kanji,
            audio_bytes=example_tts_data.audio,
            cues=example_tts_data.cues
        )
        block_actions = False
        toggle_block()
    
    async def get_word_tts(text: str) -> None:
        nonlocal word_tts_data
        if auth.offline_mode:
            debug_print("Can't generate TTS when in offline mode!")
            return
        try:
            tts = TextToSpeech(text)
            word_tts_data = await tts.get_audio_and_timing()
        except Exception as e:
            debug_print(f"TTS Initialization failed: {e}")
    
    async def get_example_tts(text: str) -> None:
        nonlocal example_tts_data
        if auth.offline_mode:
            debug_print("Can't generate TTS when in offline mode!")
            return
        try:
            tts = TextToSpeech(text)
            example_tts_data = await tts.get_audio_and_timing()
        except Exception as e:
            debug_print(f"TTS Initialization failed: {e}")
    
    async def generate_word(_) -> None:
        nonlocal block_actions
        page.show_dialog(LoadingNotification(text="Retrieving a new random word..."))
        block_actions = True
        toggle_block()
        
        data = lesson_manager.get_random_word()
        word_kpt_display.set_text(**data, title="Word")
        example_kpt_display.visible = False
        example_kpt_display.update()
        
        await get_word_tts(data.get("kanji").strip())
        
        if word_tts_data.audio and not auth.offline_mode:
            audio_manager.play_sfx(word_tts_data.audio)
        
        page.pop_dialog()
        block_actions = False
        toggle_block()
        await play_word(_)
    
    async def generate_lesson(_) -> None:
        nonlocal block_actions
        page.show_dialog(LoadingNotification(text="Retrieving a new random word and example..."))
        block_actions = True
        toggle_block()
        
        data = await lesson_manager.get_lesson_data()
        
        if data.error is None and not auth.offline_mode:
            word_kpt_display.set_text(data.kanji, data.pinyin, data.translation, title="Word")
            example_kpt_display.visible = True
            example_kpt_display.set_text(data.example, data.example_pinyin, data.example_en)
            
            await get_word_tts(data.kanji.strip())
            await get_example_tts(data.example.strip())
            
            if example_tts_data.audio:
                audio_manager.play_sfx(example_tts_data.audio)
            page.pop_dialog()
        else:
            debug_print(f"Cerebras Error: {data.error}")
            notif = ft.SnackBar(
                ft.Text("Cerebras Error: Please wait a bit before trying again.", color=ft.Colors.ON_ERROR),
                duration=ft.Duration(seconds=3), behavior=ft.SnackBarBehavior.FLOATING, bgcolor=ft.Colors.ERROR
            )
            page.show_dialog(notif)
        
        block_actions = False
        toggle_block()
        await play_example(_)
    
    async def on_reset(_) -> None:
        page.show_dialog(LoadingNotification(text="Resetting saved preferences..."))
        if await prefs.clear():
            msg = "Successfully reset saved preferences!"
        else:
            msg = "Failed resetting saved preferences!"
        page.pop_dialog()
        debug_print(msg)
        page.show_dialog(ft.SnackBar(msg, ft.SnackBarBehavior.FLOATING))
    
    def prepare_highlight_text(text_control: ft.Text, cues: list[Subtitle]):
        # Create a list of spans, one for each word/character in the cues
        text_control.spans = [
            ft.TextSpan(cue.content, style=ft.TextStyle(color=ft.Colors.PRIMARY)) 
            for cue in cues
        ]
        text_control.value = "" # Clear the main value so only spans show
        text_control.update()
    
    async def play_with_highlight(text_control: ft.Text, audio_bytes: bytes, cues: list[Subtitle]):
        prev_value = text_control.value
        prepare_highlight_text(text_control, cues)
        
        audio_manager.play_sfx(audio_bytes)
        
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
    
    def on_personalization(_) -> None:        
        async def on_save(_) -> None:
            text = tf.value.strip().lower()
            if not text or text.isspace():
                tf.error = "Cannot be empty"
            else:
                tf.error = None
            tf.update()
            debug_print(f"Saving name: {text}")
            if await prefs.set("user_name", text):
                msg = f"Saved \"{text}\" as the 'user_name'!"
            else:
                msg = f"Failed to save \"{text}\" as the 'user_name'..."
            page.pop_dialog()
            page.show_dialog(ft.SnackBar(msg, ft.SnackBarBehavior.FLOATING))
            await check_bday(update_tts_data=True, play_tts=True)
        
        tf = ft.TextField(
            autofocus=True, max_lines=1, max_length=30, on_submit=on_save
        )
        dialog = ft.AlertDialog(
            title="Enter a Name", content=tf,
            actions=[ft.Button("Save", ft.Icons.SAVE, on_click=on_save)]
        )
        page.show_dialog(dialog)
    
    def seg_btn_on_change(e: ft.Event[ft.SegmentedButton]) -> None:
        data_list: list[str] = e.data
        data: int = int(data_list[0])
        debug_print(f"Setting hsk level to: {data}")
        lesson_manager.current_hsk_level = data
    
    async def check_bday(
        *, update_tts_data: bool = False, play_tts: bool = False
    ) -> None:
        nonlocal settings_menu_btn, greet_btn
        name: str = await prefs.get("user_name")
        if not is_vani_bday() or not name.strip().lower() == "vani": return
        word_kpt_display.set_text(
            kanji="生日快乐, Vani!",
            pinyin="Shēngrì kuàilè, Vani!",
            translation="Happy birthday, Vani!",
            title="Hello Vani"
        )
        greet_btn.visible = True
        try: greet_btn.update()
        except RuntimeError: pass
        if update_tts_data: await get_word_tts(word_kpt_display.kanji)
        if play_tts: await play_word(None)
    
    def open_greeting(e: ft.Event[ft.IconButton]) -> None:
        nonlocal settings_menu_btn
        dialog = ft.AlertDialog(
            title="Happy Birthday, Vani!",
            content=ft.Image("images/bday_cake.png", fit=ft.BoxFit.CONTAIN),
            actions=[
                ft.Button(
                    "Thank you", icon=ft.Icons.FACE_3_ROUNDED,
                    on_click=lambda _: page.pop_dialog()
                )
            ]
        )
        e.control.badge = None
        try: e.control.update()
        except RuntimeError: pass
        page.show_dialog(dialog)
    
    # UI Components
    word_kpt_display = KPTDisplay(
        title="Welcome!", kanji="按下开始", pinyin="Àn xià kāishǐ", translation="Press to start",
        on_listen=play_word
    )
    example_kpt_display = KPTDisplay(title="Example", visible=False, on_listen=play_example)
    word_kpt_display.listen_button.disabled = auth.offline_mode
    example_kpt_display.listen_button.disabled = auth.offline_mode
    seg_btn = ft.SegmentedButton(
        allow_multiple_selection=False,
        selected_icon=ft.Icons.CHECK_SHARP,
        selected=["1"],
        segments=[
            ft.Segment(value="1", label="HSK 1", icon=ft.Icons.LOOKS_ONE_SHARP),
            ft.Segment(value="2", label="HSK 2", icon=ft.Icons.LOOKS_TWO_SHARP),
            ft.Segment(value="3", label="HSK 3", icon=ft.Icons.LOOKS_3_SHARP)
        ],
        on_change=seg_btn_on_change
    )
    
    greet_btn = ft.IconButton(
        ft.Icons.NOTIFICATION_IMPORTANT, visible=False,
        on_click=open_greeting, badge=ft.Badge(small_size=10)
    )
    settings_menu_btn = ft.PopupMenuButton(
        tooltip="Show additional actions",
        icon=ft.Icons.SETTINGS,
        items=[
            ft.PopupMenuItem("Reset Preferences", ft.Icons.RESTORE, on_click=on_reset),
            ft.PopupMenuItem("Personalization", ft.Icons.PERSON, on_click=on_personalization)
        ]
    )
    
    change_status("Finishing Setup... 2/2")
    await check_bday()
    word_tts_data = TTSData()
    example_tts_data = TTSData()
    await get_word_tts(word_kpt_display.kanji)
    
    # Layouts
    button_row = ft.Row(
        controls=[
            ft.Button(
                content="New Word", on_click=generate_word,
                tooltip="Retrieve a new random word. Works in offline mode."
            ),
            ft.Button(
                content="New Example", on_click=generate_lesson, disabled=auth.offline_mode,
                tooltip=(
                    "Not available in offline mode" if auth.offline_mode
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
                    "You are currently offline. Restart the app to reconnect." if auth.offline_mode
                    else "Information presented may or may not be accurate."
                ),
                size=12, color=ft.Colors.SECONDARY
            ),
            word_kpt_display,
            example_kpt_display,
            button_row,
            seg_btn
        ],
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH
    )
    
    change_status("Starting App!")
    await asyncio.sleep(0.1)
    page.controls.clear()
    page.add(ft.SafeArea(main_content))
    page.appbar = ft.AppBar(
        leading=ft.Icon(ft.Icons.WIFI_OFF if auth.offline_mode else ft.Icons.WIFI, size=22),
        title="VaniLingo", actions=[ToggleThemeButton(), settings_menu_btn, greet_btn]
    )
    page.update()
    await play_word(None)

ft.run(main)