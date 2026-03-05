import flet as ft
import os, asyncio
from dotenv import load_dotenv
from typing import Optional
from cerebras.cloud.sdk import AsyncCerebras

from components.inputs import KeyField
from components.displays import StatusText
from utilities.file_management import load_json_file

class ClientAuth:
    def __init__(
        self, page: ft.Page, prefs: ft.SharedPreferences,
        *, debug: bool = False, offline_mode: bool = False
    ) -> None:
        self.page = page
        self.prefs = prefs
        self.debug = debug
        self.offline_mode = offline_mode
        self.api_key: Optional[str] = None
        self.client: Optional[AsyncCerebras] = None
    
    def _debug_print(self, msg: str) -> None:
        if not self.debug: return
        print(f"[ClientAuth]: {msg}")
    
    def get_client(self) -> Optional[AsyncCerebras]:
        if self.offline_mode or self.api_key is None:
            self._debug_print("Client is in offline mode!")
            return None
        client = AsyncCerebras(api_key=self.api_key, timeout=20.0)
        self.client = client
        return client
    
    def get_api_key(self) -> Optional[str]:
        """Searches for the API key in three possible locations."""
        if self.offline_mode:
            self._debug_print("Client is in offline mode!")
            return None
        
        self._debug_print("Getting API key... 1/3 (Checking local env)")
        key = os.getenv("CEREBRAS_API_KEY")
        if key:
            self.api_key = key
            return key
        
        self._debug_print("Getting API key... 2/3 (Checking local files)")
        key = load_json_file("secret.json")
        if key:
            key: dict[str, str]
            self.api_key = key.get("CEREBRAS_API_KEY")
            return key
        
        self._debug_print("Getting API key... 3/3 (Loading envs)")
        load_dotenv()
        key = os.getenv("CEREBRAS_API_KEY")
        self.api_key = key
        return key
    
    async def is_api_key_valid(self, client: AsyncCerebras) -> bool:
        """
        Checks if provided API key is valid by sending a small
        API request to the server.
        """
        if self.offline_mode:
            self._debug_print("Client is in offline mode!")
            return False
        
        try:
            # A tiny request to "probe" the server
            await client.chat.completions.create(
                model="llama3.1-8b", 
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=1 
            )
            self._debug_print("API key is valid!")
            return True
        except Exception as e:
            # If it returns a 401 Unauthorized, the key is invalid
            self._debug_print(f"Validation failed: {e}")
            return False
        
    async def api_check(self) -> Optional[str]:
        """Prompts the user for the API key."""
        if self.offline_mode:
            self._debug_print("Client is in offline mode!")
            return None
        
        self._debug_print("Opening API Check dialog!")
        validated_event = asyncio.Event()
        validated_key: Optional[str] = None
        
        async def on_validate(_) -> None:
            nonlocal validated_key
            kf.reset_error()
            status_txt.set_text("Validating...")
            
            if not kf.value or not kf.value.strip() or kf.value.isspace():
                status_txt.clear_text()
                kf.set_error("Key Cannot be Empty")
                return
            
            if await self.is_api_key_valid(AsyncCerebras(api_key=kf.value)):
                validated_key = kf.value
                kf.reset_error()
                await self.prefs.set("cerebras_api_key", kf.value)
                self.page.pop_dialog()
                validated_event.set()
                status_txt.set_text("Validated Key!")
            else:
                status_txt.clear_text()
                kf.set_error("Invalid Key")
        
        def on_offline_mode(_) -> None:
            nonlocal validated_key
            self._debug_print("Entering offline mode!")
            status_txt.set_text("Entering offline mode...")
            validated_key = None
            self.page.pop_dialog()
            self.offline_mode = True
            validated_event.set()
        
        kf = KeyField(on_click=on_validate)
        status_txt = StatusText()
        
        modal_dialog = ft.AlertDialog(
            modal=True,
            title="Authentication Required",
            content=ft.Column(
                controls=[kf, status_txt],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                tight=True
            ),
            actions=[
                ft.Button("Validate", on_click=on_validate),
                ft.Button("Enter Offline Mode", on_click=on_offline_mode)
            ],
        )
        
        self.page.show_dialog(modal_dialog)
        
        # Dialog will only close once key is validated
        await validated_event.wait()
        self.api_key = validated_key
        return validated_key