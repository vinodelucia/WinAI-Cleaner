import os
import pytest
from src.scanner import SystemScanner
from src.report_generator import generate_html_report

@pytest.fixture
def mock_environment(tmp_path, monkeypatch):
    """
    Cria um diretório temporário isolado simulando caches do Windows e da Adobe,
    e substitui get_cleanup_targets para que os testes nunca toquem no sistema real.
    """
    temp_cache_dir = tmp_path / "MockUserTemp"
    temp_cache_dir.mkdir()

    # Cria 2 arquivos temporários simulados (1 MB cada)
    file1 = temp_cache_dir / "render_cache_01.cfa"
    file2 = temp_cache_dir / "temp_log_02.tmp"
    file1.write_bytes(b"0" * (1024 * 1024))
    file2.write_bytes(b"1" * (1024 * 1024))

    # Cria diretório com filtro de prefixo (simulando thumbcache do Explorer)
    explorer_dir = tmp_path / "MockExplorer"
    explorer_dir.mkdir()
    thumb_file = explorer_dir / "thumbcache_256.db"
    keep_file = explorer_dir / "desktop.ini"
    thumb_file.write_bytes(b"T" * (512 * 1024))  # 0.5 MB
    keep_file.write_bytes(b"K" * 1024)           # Não deve ser incluído pelo filtro

    mock_targets = [
        {
            "category": "Adobe Media Cache Files",
            "path": str(temp_cache_dir),
            "description": "Cache simulado da Adobe",
            "risk": "SAFE",
            "profiles": ["Geral (Completo)", "Edição de Vídeo"]
        },
        {
            "category": "Cache de Miniaturas (Explorer)",
            "path": str(explorer_dir),
            "description": "Miniaturas simuladas",
            "risk": "SAFE",
            "filter_prefix": "thumbcache_",
            "profiles": ["Geral (Completo)"]
        }
    ]

    # Desativa chamada de rede ao Ollama durante os testes unitários para velocidade máxima
    monkeypatch.setattr("src.scanner.get_cleanup_targets", lambda: mock_targets)
    monkeypatch.setattr("src.ai_engine.AIEngine._check_ollama", lambda self: False)

    return {
        "temp_dir": temp_cache_dir,
        "file1": file1,
        "file2": file2,
        "thumb_file": thumb_file,
        "keep_file": keep_file
    }

def test_scan_detects_files_and_respects_prefix(mock_environment):
    scanner = SystemScanner()
    results = scanner.scan()

    assert len(results) == 2

    adobe_res = next(r for r in results if r["category"] == "Adobe Media Cache Files")
    assert adobe_res["file_count"] == 2
    assert adobe_res["size_mb"] == 2.0
    assert adobe_res["ai_decision"] == "SAFE"

    explorer_res = next(r for r in results if r["category"] == "Cache de Miniaturas (Explorer)")
    assert explorer_res["file_count"] == 1
    assert explorer_res["size_mb"] == 0.5
    # Garante que o arquivo desktop.ini foi ignorado pelo filter_prefix
    scanned_paths = [fp for fp, _ in explorer_res["files"]]
    assert str(mock_environment["keep_file"]) not in scanned_paths

def test_dry_run_mode_never_deletes_files(mock_environment):
    scanner = SystemScanner()
    scanner.scan()

    cleanup_data = scanner.execute_cleanup(
        selected_categories=["Adobe Media Cache Files", "Cache de Miniaturas (Explorer)"],
        dry_run=True
    )

    assert cleanup_data["dry_run"] is True
    assert cleanup_data["deleted_files_count"] == 3
    assert cleanup_data["total_freed_mb"] == 2.5

    # Verifica que NENHUM arquivo foi apagado do disco no modo Dry-Run
    assert mock_environment["file1"].exists()
    assert mock_environment["file2"].exists()
    assert mock_environment["thumb_file"].exists()

def test_real_cleanup_deletes_target_files_only(mock_environment):
    scanner = SystemScanner()
    scanner.scan()

    cleanup_data = scanner.execute_cleanup(
        selected_categories=["Adobe Media Cache Files", "Cache de Miniaturas (Explorer)"],
        dry_run=False
    )

    assert cleanup_data["dry_run"] is False
    assert cleanup_data["deleted_files_count"] == 3
    assert cleanup_data["total_freed_mb"] == 2.5

    # Arquivos de cache devem ter sido removidos
    assert not mock_environment["file1"].exists()
    assert not mock_environment["file2"].exists()
    assert not mock_environment["thumb_file"].exists()

    # Arquivo fora do filtro (desktop.ini) deve continuar intacto
    assert mock_environment["keep_file"].exists()

def test_locked_files_are_skipped_gracefully(mock_environment, monkeypatch):
    scanner = SystemScanner()
    scanner.scan()

    # Simula erro de permissão/arquivo em uso pelo Windows (PermissionError / OSError)
    original_remove = os.remove
    def mock_remove_locked(path):
        if "render_cache_01.cfa" in str(path):
            raise PermissionError("Arquivo em uso pelo Adobe Premiere Pro")
        return original_remove(path)

    monkeypatch.setattr("os.remove", mock_remove_locked)

    cleanup_data = scanner.execute_cleanup(
        selected_categories=["Adobe Media Cache Files"],
        dry_run=False
    )

    assert cleanup_data["deleted_files_count"] == 1
    assert cleanup_data["skipped_locked_count"] == 1
    assert cleanup_data["total_freed_mb"] == 1.0
    assert mock_environment["file1"].exists()      # O arquivo bloqueado foi preservado sem travar o app
    assert not mock_environment["file2"].exists()  # O arquivo livre foi removido normalmente

def test_html_report_generation(mock_environment, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    scanner = SystemScanner()
    scanner.scan()

    cleanup_data = scanner.execute_cleanup(
        selected_categories=["Adobe Media Cache Files"],
        dry_run=True
    )

    report_path = generate_html_report(
        cleanup_data,
        profile_name="Edição de Vídeo",
        open_browser=False
    )

    assert os.path.exists(report_path)
    with open(report_path, "r", encoding="utf-8") as f:
        html = f.read()

    assert "SIMULAÇÃO (DRY-RUN)" in html
    assert "Edição de Vídeo" in html
    assert "Adobe Media Cache Files" in html
