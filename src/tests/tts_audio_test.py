import flet as ft

from tests.test_handler import test_page
from managers.tts import TextToSpeech
from audio.audio_manager import AudioManager

@test_page("TTS Audio Test")
def main(page: ft.Page) -> None:
    audio_manager = AudioManager(page, sfx_volume=1.0)
    current_tts_bytes: bytes = None
    
    def on_click(_) -> None:
        if current_tts_bytes:
            print("Playing TTS audio sample again...")
            audio_manager.play_sfx(current_tts_bytes)
        else:
            print("No generated audio sample to play.")
    
    async def on_submit(e: ft.Event[ft.TextField]) -> None:
        nonlocal current_tts_bytes
        if e.data in [None, "", " "]:
            e.control.error = "Cannot be empty"
            e.control.update()
            return
        elif e.control.error:
            e.control.error = None
            e.control.update()
        
        print(f"Generating TTS audio for: \"{e.data}\"")
        audio_manager.play_sfx(await TextToSpeech(e.data).get_audio_bytes())
        print("Playing TTS audio sample!")
    
    page.add(
        ft.Button("Replay TTS", on_click=on_click),
        ft.TextField(
            hint_text="Type anything", max_length=30, max_lines=1,
            on_submit=on_submit, autofocus=True
        )
    )

ft.run(main, assets_dir="../assets")