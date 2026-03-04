import flet as ft
from typing import Optional


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