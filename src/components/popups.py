import flet as ft

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