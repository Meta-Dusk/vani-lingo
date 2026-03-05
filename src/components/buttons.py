import flet as ft
from typing import Optional
from dataclasses import field

from utilities.controls import try_update
from components.popups import BdayDialog

@ft.control
class ToggleThemeButton(ft.IconButton):
    icon: Optional[ft.IconDataOrControl] = ft.Icons.DARK_MODE
    adaptive: Optional[bool] = True
    
    def init(self):
        self.on_click = self.on_toggle_theme
    
    def did_mount(self):
        self.icon = (
            ft.Icons.DARK_MODE if
            self.page.theme_mode == ft.ThemeMode.DARK
            else ft.Icons.LIGHT_MODE
        )
    
    def on_toggle_theme(self, _) -> None:
        if self.page.theme_mode == ft.ThemeMode.DARK:
            self.page.theme_mode = ft.ThemeMode.LIGHT
            self.icon = ft.Icons.LIGHT_MODE
        else:
            self.page.theme_mode = ft.ThemeMode.DARK
            self.icon = ft.Icons.DARK_MODE
        self.page.update()

@ft.control
class HSKSegmentedButton(ft.SegmentedButton):
    allow_multiple_selection: bool = False
    selected_icon: ft.IconDataOrControl = ft.Icons.CHECK_SHARP
    selected: list[str] = field(default_factory=lambda: ["1"])
    disabled: bool = True
    segments: list[ft.Segment] = field(default_factory=lambda: [
        ft.Segment(value="1", label="HSK 1", icon=ft.Icons.LOOKS_ONE_SHARP),
        ft.Segment(value="2", label="HSK 2", icon=ft.Icons.LOOKS_TWO_SHARP),
        ft.Segment(value="3", label="HSK 3", icon=ft.Icons.LOOKS_3_SHARP)
    ])

@ft.control
class GreetNotifIcon(ft.IconButton):
    icon: ft.IconDataOrControl = ft.Icons.NOTIFICATION_IMPORTANT
    visible: bool = False
    badge: Optional[ft.BadgeValue] = ft.Badge(small_size=10)
    
    def did_mount(self):
        self.on_click = self._on_click
        
    def _on_click(self, e: ft.Event[ft.IconButton]) -> None:
        e.control.badge = None
        try_update(e.control)
        e.page.show_dialog(BdayDialog())