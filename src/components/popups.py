import flet as ft
from dataclasses import field

@ft.control
class LoadingNotification(ft.SnackBar):
    text: str = ""
    persist: bool = True
    behavior: ft.SnackBarBehavior = ft.SnackBarBehavior.FLOATING
    content: ft.StrOrControl = ""
    
    def build(self):
        self.content = ft.Row(
            controls=[
                ft.ProgressRing(
                    width=20, height=20, stroke_width=2,
                    color=ft.Colors.ON_SECONDARY
                ),
                ft.Text(self.text)
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            tight=True
        )

@ft.control
class BdayDialog(ft.AlertDialog):
    title: ft.StrOrControl = "Happy Birthday, Vani!"
    content: ft.Control = ft.Image("images/bday_cake.png", fit=ft.BoxFit.CONTAIN)
    actions: list[ft.Control] = field(default_factory=lambda: [
        ft.Button(
            "Thank you", icon=ft.Icons.FACE_3_ROUNDED,
            on_click=lambda e: e.page.pop_dialog()
        )
    ])