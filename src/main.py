import flet as ft
import asyncio

from setup import setup_page, FontStyles, PC_PLATFORMS
from audio.audio_manager import AudioManager
from managers.tts import TextToSpeech
from managers.auth import ClientAuth
from managers.app import MainApp
from components.buttons import ToggleThemeButton
from components.displays import KPTDisplay

async def main(page: ft.Page) -> None:
    setup_page(page)
    status_txt = ft.Text("Starting Setup... 1/2")
    page.add(ft.ProgressRing(width=100, height=100), status_txt)
    if page.platform in PC_PLATFORMS:
        await page.window.center()
    
    def change_status(text: str) -> None:
        nonlocal status_txt
        print(f"[App] {text}")
        status_txt.value = text
        status_txt.update()
    
    change_status("Starting local services...")
    prefs = ft.SharedPreferences()
    auth = ClientAuth(page, prefs)
    audio_manager = AudioManager(page)
    
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
    
    change_status("Starting client...")
    client = auth.get_client()
    app = MainApp(client)
    if client is None:
        change_status("Entering offline mode...")
    
    change_status("Initializing Data...")
    await app.initialize()
    
    # Callbacks
    def play_word(_) -> None:
        if word_audio_bytes is None: return
        audio_manager.play_sfx(word_audio_bytes)
    
    def play_example(_) -> None:
        if example_audio_bytes is None: return
        audio_manager.play_sfx(example_audio_bytes)
    
    async def generate_word(_) -> None:
        nonlocal word_audio_bytes
        loading_ring.visible = True
        button_row.disabled = True
        loading_ring.update()
        button_row.update()
        
        data = app.get_random_word()
        word_kpt_display.set_text(**data, title="Word")
        example_kpt_display.visible = False
        example_kpt_display.update()
        
        word_to_speak = data.get("kanji").strip()
        word_audio_bytes = await TextToSpeech(word_to_speak).get_audio_bytes()
        
        if word_audio_bytes:
            audio_manager.play_sfx(word_audio_bytes)
        
        loading_ring.visible = False
        button_row.disabled = False
        loading_ring.update()
        button_row.update()
    
    async def generate_lesson(_) -> None:
        nonlocal word_audio_bytes, example_audio_bytes
        loading_ring.visible = True
        button_row.disabled = True
        loading_ring.update()
        button_row.update()
        
        data = await app.get_lesson_data()
        
        if data.error is None:
            word_kpt_display.set_text(data.kanji, data.pinyin, data.translation, title="Word")
            example_kpt_display.visible = True
            example_kpt_display.set_text(data.example, data.example_pinyin, data.example_en)
            
            word_to_speak = str(data.kanji).strip()
            word_audio_bytes = await TextToSpeech(word_to_speak).get_audio_bytes()
            
            example_to_speak = str(data.example).strip()
            example_audio_bytes = await TextToSpeech(example_to_speak).get_audio_bytes()
            
            if example_audio_bytes:
                audio_manager.play_sfx(example_audio_bytes)
                
            loading_ring.visible = False
            button_row.disabled = False
            loading_ring.update()
            button_row.update()
            
        else:
            loading_ring.visible = False
            button_row.disabled = False
            loading_ring.update()
            button_row.update()
            print(f"Cerebras Error: {data.error}")
    
    async def on_reset(_) -> None:
        page.show_dialog(
            ft.SnackBar(
                "Resetting saved preferences...",
                ft.SnackBarBehavior.FLOATING
            )
        )
        if await prefs.clear():
            msg = "Successfully reset saved preferences!"
        else:
            msg = "Failed resetting saved preferences!"
        page.pop_dialog()
        print(msg)
        page.show_dialog(ft.SnackBar(msg, ft.SnackBarBehavior.FLOATING))
    
    # UI Components
    word_kpt_display = KPTDisplay(
        title="Welcome!", kanji="按下开始", pinyin="Àn xià kāishǐ", translation="Press to start",
        on_listen=play_word
    )
    example_kpt_display = KPTDisplay(title="Example", visible=False, on_listen=play_example)
    loading_ring = ft.ProgressRing(visible=False)
    
    change_status("Finishing Setup... 2/2")
    word_audio_bytes = await TextToSpeech(word_kpt_display.kanji).get_audio_bytes()
    example_audio_bytes: bytes = None
    
    # Layouts
    button_row = ft.Row(
        controls=[
            loading_ring,
            ft.Button("New Word", on_click=generate_word),
            ft.Button("New Example", on_click=generate_lesson, visible=not auth.offline_mode),
            ft.IconButton(ft.Icons.RESTORE, on_click=on_reset)
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN
    )
    
    main_content = ft.Column(
        controls=[
            ft.Text(
                "You are currently offline.", size=12,
                color=ft.Colors.SECONDARY, visible=auth.offline_mode
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
        title="VaniLingo",
        actions=[ToggleThemeButton()]
    )
    page.update()
    audio_manager.play_sfx(word_audio_bytes)

ft.run(main)