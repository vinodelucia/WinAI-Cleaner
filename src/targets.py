import os
from pathlib import Path

PROFILES = [
    "Geral (Completo)",
    "Modo Gamer",
    "Edição de Vídeo",
    "Básico do Sistema"
]

TEMP_EXCLUDE_EXTENSIONS = [".lock", ".lck", ".pid"]


def get_cleanup_targets():
    """
    Mapeamento de diretórios seguros de cache e arquivos temporários do Windows,
    classificados por perfis de uso (Gamer, Edição de Vídeo/Adobe, Básico e Geral).
    """
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    app_data = os.environ.get("APPDATA", "")
    win_dir = os.environ.get("WINDIR", r"C:\Windows")
    temp_dir = os.environ.get("TEMP", "")

    targets = [
        {
            "category": "Temporários do Usuário",
            "path": temp_dir,
            "description": "Arquivos temporários gerados por aplicativos em uso diário (apenas com mais de 1 dia).",
            "min_age_days": 1,
            "exclude_extensions": TEMP_EXCLUDE_EXTENSIONS,
            "risk": "SAFE",
            "profiles": ["Geral (Completo)", "Modo Gamer", "Edição de Vídeo", "Básico do Sistema"]
        },
        {
            "category": "Temporários do Sistema (Windows)",
            "path": os.path.join(win_dir, "Temp"),
            "description": "Caches temporários de serviços internos do sistema operacional (apenas com mais de 1 dia).",
            "min_age_days": 1,
            "exclude_extensions": TEMP_EXCLUDE_EXTENSIONS,
            "risk": "SAFE",
            "profiles": ["Geral (Completo)", "Básico do Sistema"]
        },
        {
            "category": "Windows Prefetch",
            "path": os.path.join(win_dir, "Prefetch"),
            "description": "Índices antigos de pré-carregamento de aplicativos sem uso há mais de 7 dias.",
            "min_age_days": 7,
            "risk": "SAFE",
            "profiles": ["Geral (Completo)", "Modo Gamer", "Básico do Sistema"]
        },
        {
            "category": "Cache do Windows Update",
            "path": os.path.join(win_dir, "SoftwareDistribution", "Download"),
            "description": "Instaladores de atualizações do Windows já concluídas. Ignorado automaticamente se o serviço wuauserv estiver ativo.",
            "min_age_days": 1,
            "active_service": "wuauserv",
            "risk": "SAFE",
            "profiles": ["Geral (Completo)", "Básico do Sistema"]
        },
        {
            "category": "DirectX Shader Cache",
            "path": os.path.join(local_app_data, "D3DSCache"),
            "description": "Shaders gráficos compilados antigos de jogos e motores 3D.",
            "risk": "SAFE",
            "profiles": ["Geral (Completo)", "Modo Gamer", "Edição de Vídeo"]
        },
        {
            "category": "NVIDIA DXCache (Shaders de GPU)",
            "path": os.path.join(local_app_data, "NVIDIA", "DXCache"),
            "description": "Cache de shaders DirectX da placa de vídeo NVIDIA para evitar stuttering.",
            "risk": "SAFE",
            "profiles": ["Geral (Completo)", "Modo Gamer", "Edição de Vídeo"]
        },
        {
            "category": "Relatórios de Falha (Crash Dumps)",
            "path": os.path.join(local_app_data, "CrashDumps"),
            "description": "Despejos de memória gerados quando jogos ou programas fecham com erro.",
            "risk": "REVIEW",
            "profiles": ["Geral (Completo)", "Modo Gamer", "Edição de Vídeo", "Básico do Sistema"]
        },
        {
            "category": "Adobe Media Cache Files",
            "path": os.path.join(app_data, "Adobe", "Common", "Media Cache Files"),
            "description": "Arquivos pesados de cache de áudio e vídeo (.cfa, .pek) do Premiere e After Effects.",
            "risk": "SAFE",
            "profiles": ["Geral (Completo)", "Edição de Vídeo"]
        },
        {
            "category": "Adobe Media Cache Database",
            "path": os.path.join(app_data, "Adobe", "Common", "Media Cache"),
            "description": "Índices antigos de projetos de vídeo já renderizados da suíte Adobe.",
            "risk": "REVIEW",
            "profiles": ["Geral (Completo)", "Edição de Vídeo"]
        },
        {
            "category": "Cache de Miniaturas (Explorer)",
            "path": os.path.join(local_app_data, "Microsoft", "Windows", "Explorer"),
            "description": "Caches de miniaturas antigas do Windows Explorer (arquivos thumbcache).",
            "risk": "SAFE",
            "filter_prefix": "thumbcache_",
            "profiles": ["Geral (Completo)", "Edição de Vídeo", "Básico do Sistema"]
        }
    ]

    valid_targets = []
    for t in targets:
        if t["path"] and Path(t["path"]).exists():
            valid_targets.append(t)
    return valid_targets
