import flet as ft
from enum import Enum
from typing import Optional, Callable

class Menus(Enum):
    MAIN = "Main Menu"
    CLASSIC = "Classic Menu"
    Q_AND_A = "Question and Answer Menu"
    NONE = "Empty"

class MenuManager:
    def __init__(self, page: ft.Page):
        self.page = page
        self._current_menu: Menus = Menus.NONE
        self._menu_handlers: dict[Menus, Optional[Callable[[], ft.Control]]] = {
            Menus.MAIN: None,
            Menus.CLASSIC: None,
            Menus.Q_AND_A: None,
        }
    
    @property
    def current_menu(self) -> Menus:
        return self._current_menu
    
    @current_menu.setter
    def current_menu(self, menu: Menus) -> None:
        self._current_menu = menu
        handler = self._menu_handlers.get(menu)
        if handler:
            self.page.controls.clear()
            self.page.add(handler())
            self.page.update()