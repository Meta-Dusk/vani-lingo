import flet as ft
import os, json, asyncio
from dotenv import load_dotenv
from typing import Optional
from cerebras.cloud.sdk import AsyncCerebras

from components.inputs import KeyField

class ClientAuth:
    def __init__(
        self, page: ft.Page, prefs: ft.SharedPreferences,
        *, debug: bool = False, offline_mode: bool = False
    ):
        self.page = page
        self.prefs = prefs
        self.debug = debug
        self.offline_mode = offline_mode
        self.api_key: Optional[str] = None
        self.client: Optional[AsyncCerebras] = None
    
    def _debug_print(self, msg: str) -> None:
        if not self.debug: return
        print(f"[ClientAuth] {msg}")
    
    def get_client(self) -> Optional[AsyncCerebras]:
        if self.offline_mode:
            self._debug_print("Client is in offline mode!")
            return None
        client = AsyncCerebras(api_key=self.api_key)
        self.client = client
        return client
    
    def get_api_key(self) -> Optional[str]:
        if self.offline_mode:
            self._debug_print("Client is in offline mode!")
            return None
        
        self._debug_print("Getting API key...")
        key = os.getenv("CEREBRAS_API_KEY")
        if key:
            self.api_key = key
            return key
        
        try:
            # Build the path relative to THIS file (main.py)
            base_dir = os.path.dirname(__file__)
            secret_path = os.path.join(base_dir, "assets", "secret.json")
            
            # Fallback: Flet sometimes sets a specific environment variable for assets
            if not os.path.exists(secret_path):
                flet_assets = os.getenv("FLET_ASSETS_DIR", "assets")
                secret_path = os.path.join(base_dir, flet_assets, "secret.json")
                
            with open(secret_path, "r", encoding="utf-8") as f:
                secret = json.load(f)
                key = secret.get("CEREBRAS_API_KEY")
                self.api_key = key
                return key
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self._debug_print(f"Asset lookup failed: {e}")
            pass
        
        load_dotenv()
        key = os.getenv("CEREBRAS_API_KEY")
        self.api_key = key
        return key
    
    async def is_api_key_valid(self, client: AsyncCerebras) -> bool:
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
        if self.offline_mode:
            self._debug_print("Client is in offline mode!")
            return None
        
        self._debug_print("Opening API Check dialog!")
        validated_event = asyncio.Event()
        validated_key: Optional[str] = None
        
        async def validate(_) -> None:
            nonlocal validated_key
            kf.reset_error()
            
            if kf.value in [None, "", " "]:
                kf.set_error("Key Cannot be Empty")
                return
            
            if await self.is_api_key_valid(AsyncCerebras(api_key=kf.value)):
                validated_key = kf.value
                kf.reset_error()
                await self.prefs.set("cerebras_api_key", kf.value)
                self.page.pop_dialog()
                validated_event.set()
            else:
                kf.set_error("Invalid Key")
        
        def on_cancel(_) -> None:
            nonlocal validated_key
            self._debug_print("Entering offline mode!")
            validated_key = None
            validated_event.set()
        
        kf = KeyField(on_click=validate)
        
        modal_dialog = ft.AlertDialog(
            modal=True,
            title="Authentication Required",
            content=kf,
            actions=[
                ft.Button("Validate", on_click=validate),
                ft.Button("Enter Offline Mode", on_click=on_cancel)
            ],
        )
        
        self.page.show_dialog(modal_dialog)
        
        # Dialog will only close once key is validated
        await validated_event.wait()
        self.api_key = validated_key
        return validated_key