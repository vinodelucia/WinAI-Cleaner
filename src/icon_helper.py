import os
import sys
from PIL import Image, ImageDraw

def resource_path(relative_path: str) -> str:
    """
    Resolve o caminho de arquivos estáticos tanto em modo de desenvolvimento
    quanto dentro do executável único gerado pelo PyInstaller (_MEIPASS).
    """
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def ensure_app_icon() -> str:
    """
    Gera programaticamente um ícone moderno (.ico) estilo Windows 11 se ele não existir,
    garantindo que o repositório funcione sem depender de arquivos binários externos.
    """
    icon_rel_path = os.path.join("assets", "icon.ico")
    bundled_path = resource_path(icon_rel_path)
    if os.path.exists(bundled_path):
        return bundled_path

    os.makedirs("assets", exist_ok=True)
    size = 256
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Fundo arredondado escuro moderno (Slate 900 com borda Cyan)
    draw.rounded_rectangle(
        [(16, 16), (size - 16, size - 16)],
        radius=56,
        fill=(15, 23, 42, 255),
        outline=(56, 189, 248, 255),
        width=10
    )

    # Desenho estilizado de faísca/limpeza IA no centro
    center = size // 2
    points = [
        (center, 48),
        (center + 24, center - 24),
        (size - 48, center),
        (center + 24, center + 24),
        (center, size - 48),
        (center - 24, center + 24),
        (48, center),
        (center - 24, center - 24),
    ]
    draw.polygon(points, fill=(56, 189, 248, 255))

    # Círculo central verde indicando segurança
    r = 22
    draw.ellipse(
        [(center - r, center - r), (center + r, center + r)],
        fill=(74, 222, 128, 255)
    )

    img.save(
        icon_rel_path,
        format="ICO",
        sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    )
    return os.path.abspath(icon_rel_path)
