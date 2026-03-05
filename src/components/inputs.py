import flet as ft
from typing import Optional
from dataclasses import field

from utilities.controls import try_update
from managers.tts import TTSConfig

@ft.control
class KeyField(ft.TextField):
    autofocus: bool = True
    password: bool = True
    can_reveal_password: bool = True
    hint_text: Optional[str] = "Enter Cerebras Key"
    
    def set_error(self, text: Optional[str]) -> None:
        self.error = text
        try_update(self)
    
    def reset_error(self) -> None:
        self.error = None
        try_update(self)
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
            try_update(e.control)
        
        self.on_change = _on_change

@ft.control
class TTSSettings(ft.Column):
    config: TTSConfig = field(default_factory=TTSConfig)
    spacer_width: ft.Number = 70
    horizontal_alignment: ft.CrossAxisAlignment = ft.CrossAxisAlignment.CENTER
    alignment: ft.MainAxisAlignment = ft.MainAxisAlignment.CENTER
    tight: bool = True
    
    def init(self):
        self.rate_slider = SettingSlider(value=self.config.get_rate_int)
        self.vol_slider = SettingSlider(value=self.config.get_volume_int)
        self.pitch_slider = SettingSlider(value=self.config.get_pitch_int)
        self.controls = [
            ft.Row([ft.Text("Rate", width=self.spacer_width), self.rate_slider]),
            ft.Row([ft.Text("Volume", width=self.spacer_width), self.vol_slider]),
            ft.Row([ft.Text("Pitch", width=self.spacer_width),self.pitch_slider])
        ]