import flet as ft
from typing import Optional

@ft.control
class KeyField(ft.TextField):
    autofocus: bool = True
    password: bool = True
    can_reveal_password: bool = True
    hint_text: Optional[str] = "Enter Cerebras Key"
    
    def _try_update(self) -> None:
        try: self.update
        except RuntimeError: pass
    
    def set_error(self, text: Optional[str]) -> None:
        self.error = text
        self._try_update()
    
    def reset_error(self) -> None:
        self.error = None
        self._try_update()