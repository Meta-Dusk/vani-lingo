import flet as ft
from managers.app import MainApp

async def main(page: ft.Page) -> None:
    app = MainApp(page)
    await app.run()

ft.run(main)