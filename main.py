import sys
import ctypes
from src.icon_helper import ensure_app_icon
from src.ui import WinAICleanerApp

def elevate_privileges_if_needed():
    """
    Solicita elevação de Administrador automaticamente quando executado como .exe compilado,
    permitindo limpar caches de sistema como C:\Windows\Temp e Prefetch.
    """
    if getattr(sys, "frozen", False):
        try:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            is_admin = False
        if not is_admin:
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, " ".join(sys.argv), None, 1
            )
            sys.exit(0)

if __name__ == "__main__":
    ensure_app_icon()
    elevate_privileges_if_needed()
    app = WinAICleanerApp()
    app.mainloop()
