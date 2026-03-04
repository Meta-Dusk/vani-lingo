import flet as ft

def try_update(*controls: ft.Control) -> None:
    for control in controls:
        try: control.update()
        except RuntimeError: pass