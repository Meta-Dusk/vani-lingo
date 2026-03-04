import flet as ft
from enum import Enum

class FontStyles(Enum):
    NOTO_SANS_SC = "NotoSansSC Variable Font"

FONT_STYLES = {
    FontStyles.NOTO_SANS_SC: "assets/fonts/NotoSansSC-VariableFont_wght.ttf",
}

PC_PLATFORMS = [ft.PagePlatform.WINDOWS, ft.PagePlatform.LINUX, ft.PagePlatform.MACOS]
MOBILE_PLATFORMS = [ft.PagePlatform.ANDROID, ft.PagePlatform.IOS]

def setup_page(page: ft.Page) -> None:
    page.title = "VaniLingo"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.fonts = FONT_STYLES
    page.theme_mode = ft.ThemeMode.DARK
    page.theme = ft.Theme(color_scheme_seed=ft.Colors.RED_900, font_family=FontStyles.NOTO_SANS_SC)
    if page.platform == ft.PagePlatform.WINDOWS:
        page.window.width = 450
        page.window.height = 700