import flet as ft
import asyncio

from edge_tts.srt_composer import Subtitle
from setup import setup_page, PC_PLATFORMS
from audio.audio_manager import AudioManager
from managers.tts import TextToSpeech
from managers.auth import ClientAuth
from managers.lesson import LessonManager
from components.buttons import ToggleThemeButton
from components.displays import KPTDisplay
from components.popups import LoadingNotification
from utilities.testers import is_connected

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
        wifi_req_btns = [
            word_kpt_display.listen_button,
            example_kpt_display.listen_button
        ]
        for btn in wifi_req_btns:
            btn: ft.IconButton
            if auth.offline_mode: break
            btn.disabled = block_actions
            btn.update()
        button_row.disabled = block_actions
        button_row.update()
    
    async def play_word(_) -> None:
        nonlocal block_actions
        if word_audio_bytes is None or len(word_audio_cues) == 0:
            debug_print("Nothing to play")
            return
        block_actions = True
        toggle_block()
        await play_with_highlight(
            text_control=word_kpt_display.text_displays.kanji,
            audio_bytes=word_audio_bytes,
            cues=word_audio_cues
        )
        block_actions = False
        toggle_block()
    
    async def play_example(_) -> None:
        nonlocal block_actions
        if example_audio_bytes is None or len(example_audio_cues) == 0:
            debug_print("Nothing to play")
            return
        block_actions = True
        toggle_block()
        await play_with_highlight(
            text_control=example_kpt_display.text_displays.kanji,
            audio_bytes=example_audio_bytes,
            cues=example_audio_cues
        )
        block_actions = False
        toggle_block()
    
    async def get_word_tts(text: str) -> None:
        nonlocal word_audio_bytes, word_audio_cues
        if auth.offline_mode:
            debug_print("Can't generate TTS when in offline mode!")
            return
        try:
            tts = TextToSpeech(text)
            word_audio_bytes, word_audio_cues = await tts.get_audio_and_timing()
        except Exception as e:
            debug_print(f"TTS Initialization failed: {e}")
    
    async def get_example_tts(text: str) -> None:
        nonlocal example_audio_bytes, example_audio_cues
        if auth.offline_mode:
            debug_print("Can't generate TTS when in offline mode!")
            return
        try:
            tts = TextToSpeech(text)
            example_audio_bytes, example_audio_cues = await tts.get_audio_and_timing()
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
        
        if word_audio_bytes and not auth.offline_mode:
            audio_manager.play_sfx(word_audio_bytes)
        
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
            
            if example_audio_bytes:
                audio_manager.play_sfx(example_audio_bytes)
        else:
            debug_print(f"Cerebras Error: {data.error}")
        
        page.pop_dialog()
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
            if wait_time > 0:
                await asyncio.sleep(wait_time)
                
            # Update the UI to highlight the current word
            text_control.spans[i].style.color = ft.Colors.INVERSE_PRIMARY
            text_control.spans[i].style.weight = ft.FontWeight.BOLD
            
            if i > 0:
                text_control.spans[i-1].style.color = ft.Colors.OUTLINE
                text_control.spans[i-1].style.weight = ft.FontWeight.NORMAL
                
            text_control.update()
            
        await asyncio.sleep(cue.end.total_seconds() - cue.start.total_seconds())
        text_control.spans.clear()
        text_control.value = prev_value
        text_control.update()
    
    # UI Components
    word_kpt_display = KPTDisplay(
        title="Welcome!", kanji="按下开始", pinyin="Àn xià kāishǐ", translation="Press to start",
        on_listen=play_word
    )
    example_kpt_display = KPTDisplay(title="Example", visible=False, on_listen=play_example)
    word_kpt_display.listen_button.disabled = auth.offline_mode
    example_kpt_display.listen_button.disabled = auth.offline_mode
    
    change_status("Finishing Setup... 2/2")
    word_audio_bytes: bytes = None
    word_audio_cues: list[Subtitle] = []
    example_audio_bytes: bytes = None
    example_audio_cues: list[Subtitle] = []
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
            button_row
        ],
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH
    )
    
    change_status("Starting App!")
    await asyncio.sleep(0.1)
    page.controls.clear()
    page.add(ft.SafeArea(main_content))
    page.appbar = ft.AppBar(
        leading=ft.Icon(ft.Icons.WIFI_OFF if auth.offline_mode else ft.Icons.WIFI, size=22),
        title="VaniLingo",
        actions=[
            ToggleThemeButton(),
            ft.PopupMenuButton(
                items=[
                    ft.PopupMenuItem("Reset Preferences", ft.Icons.RESTORE, on_click=on_reset),
                    ft.PopupMenuItem("Personalization", ft.Icons.PERSON)
                ],
                tooltip="Show additional actions",
                icon=ft.Icons.SETTINGS
            )
        ],
        tooltip="Additional settings"
    )
    page.update()
    await play_word(None)

ft.run(main)