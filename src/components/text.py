import flet as ft
from typing import Optional
from dataclasses import field


@ft.control
class PrimaryTextSpan(ft.TextSpan):
    style: Optional[ft.TextStyle] = field(default_factory=lambda: ft.TextStyle(color=ft.Colors.PRIMARY))