import flet as ft
from dataclasses import dataclass, field
from typing import Optional

from utilities.controls import try_update
from managers.lesson import HSKWordDict

@dataclass
class TextDisplays:
    title: ft.Text = ft.Text()
    kanji: ft.Text = ft.Text()
    pinyin: ft.Text = ft.Text()
    translation: ft.Text = ft.Text()
    
@ft.control
class KPTDisplay(ft.Container):
    title: str = ""
    kanji: str = ""
    pinyin: str = ""
    translation: str = ""
    on_listen: Optional[ft.ControlEventHandler[ft.IconButton]] = None
    padding: Optional[ft.PaddingValue] = 16
    border: Optional[ft.Border] = field(default_factory=lambda: ft.Border.all(2, ft.Colors.ON_PRIMARY_CONTAINER))
    border_radius: Optional[ft.BorderRadiusValue] = 16
    bgcolor: Optional[ft.ColorValue] = ft.Colors.PRIMARY_CONTAINER
    
    def init(self):
        self.listen_button = ft.IconButton(
            icon=ft.Icons.VOLUME_UP, on_click=self.on_listen,
            style=ft.ButtonStyle(
                color={
                    ft.ControlState.DEFAULT: ft.Colors.TERTIARY,
                    ft.ControlState.DISABLED: ft.Colors.with_opacity(0.38, ft.Colors.ON_SURFACE)
                }
            )
        )
        self.text_displays = TextDisplays(
            title=ft.Text(value=self.title, size=24, color=ft.Colors.TERTIARY),
            kanji=ft.Text(value=self.kanji, size=32, weight=ft.FontWeight.BOLD, color=ft.Colors.PRIMARY),
            pinyin=ft.Text(value=self.pinyin, size=24, italic=True, color=ft.Colors.PRIMARY),
            translation=ft.Text(value=self.translation, size=16, color=ft.Colors.SECONDARY)
        )
    
    def build(self):
        self.content = ft.Column(
            controls=[
                ft.Row(
                    [self.text_displays.title, self.listen_button],
                    alignment=ft.MainAxisAlignment.CENTER
                ),
                self.text_displays.kanji,
                self.text_displays.pinyin,
                self.text_displays.translation
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )
    
    def set_text(self, kanji: str, pinyin: str, translation: str, title: str = None) -> None:
        self.kanji = kanji
        self.pinyin = pinyin
        self.translation = translation
        self.text_displays.kanji.value = kanji
        self.text_displays.pinyin.value = pinyin
        self.text_displays.translation.value = translation
        if title:
            self.title = title
            self.text_displays.title.value = title
        try_update(self)
    
    def get_dict(self) -> HSKWordDict:
        return HSKWordDict(
            kanji=self.kanji,
            pinyin=self.pinyin,
            translation=self.translation
        )
    
    def clear_text(self) -> None:
        self.kanji = ""
        self.pinyin = ""
        self.translation = ""
        try_update(self)

@ft.control
class StatusText(ft.Column):
    alignment: ft.MainAxisAlignment = ft.MainAxisAlignment.CENTER
    horizontal_alignment: ft.CrossAxisAlignment = ft.CrossAxisAlignment.CENTER
    text: str = ""
    tight: bool = True
    visible: bool = False
    
    def init(self):
        self.text_control = ft.Text(self.text, color=ft.Colors.SECONDARY)
        self.loader = ft.ProgressRing(color=ft.Colors.SECONDARY)
    
    def build(self):
        self.controls = [self.text_control, self.loader]
    
    def set_text(self, text: str) -> None:
        self.text_control.value = text
        self.visible = True
        try_update(self, self.text_control)
    
    def clear_text(self) -> None:
        self.text_control.value = ""
        self.visible = False
        try_update(self, self.text_control)