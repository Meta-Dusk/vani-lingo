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

ft.Slider()

@ft.control
class SettingSlider(ft.Slider):
    min: ft.Number = -100
    max: ft.Number = 100
    value: ft.Number = 0
    label: Optional[str] = f"{value:+}"
    divisions: Optional[int] = 200
    expand: Optional[bool | int] = True
    
    def init(self):
        def _on_change(e: ft.Event[ft.Slider]) -> None:
            data: int = int(e.data)
            e.control.label = f"{data:+}"
            try: e.control.update()
            except RuntimeError: pass
        
        self.on_change = _on_change