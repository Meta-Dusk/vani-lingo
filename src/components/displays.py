import flet as ft
from dataclasses import dataclass
from typing import Optional

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
    
    def build(self):
        self.padding = 16
        self.border = ft.Border.all(2, ft.Colors.ON_PRIMARY_CONTAINER)
        self.border_radius = 16
        self.bgcolor = ft.Colors.PRIMARY_CONTAINER
        self.text_displays = TextDisplays(
            title=ft.Text(value=self.title, size=24, color=ft.Colors.TERTIARY),
            kanji=ft.Text(value=self.kanji, size=32, weight=ft.FontWeight.BOLD, color=ft.Colors.PRIMARY),
            pinyin=ft.Text(value=self.pinyin, size=24, italic=True, color=ft.Colors.PRIMARY),
            translation=ft.Text(value=self.translation, size=16, color=ft.Colors.SECONDARY)
        )
        self.listen_button = ft.IconButton(ft.Icons.VOLUME_UP, on_click=self.on_listen)
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
        dps = self.text_displays
        dps.kanji.value = kanji
        dps.pinyin.value = pinyin
        dps.translation.value = translation
        if title: dps.title.value = title
        try: self.update()
        except RuntimeError: pass