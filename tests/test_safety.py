import os
import time
import pytest
from src.scanner import SystemScanner
from src.ai_engine import AIEngine, validate_ai_response
from src.targets import get_cleanup_targets, TEMP_EXCLUDE_EXTENSIONS
from src.report_generator import generate_html_report
from src.logger import setup_logging
from src.icon_helper import ensure_app_icon, resource_path


def _setup(tmp_path, monkeypatch, targets):
    monkeypatch.setattr("src.scanner.get_cleanup_targets", lambda: targets)
    monkeypatch.setattr("src.ai_engine.AIEngine._check_ollama", lambda self: False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "localappdata"))
    scanner = SystemScanner()
    scanner.scan()
    return scanner


def _target(path, category="Cat", **extra):
    base = {
        "category": category, "path": str(path), "description": "d",
        "risk": "SAFE", "profiles": ["Geral (Completo)"],
    }
    base.update(extra)
    return base


def test_targets_have_no_malformed_keys():
    for t in get_cleanup_targets():
        assert all(k == k.strip() for k in t)


def test_risk_is_propagated_to_scan_results(tmp_path, monkeypatch):
    d = tmp_path / "a"
    d.mkdir()
    (d / "f.bin").write_bytes(b"x" * 100)
    scanner = _setup(tmp_path, monkeypatch, [_target(d, risk="REVIEW")])
    assert scanner.scan_results[0]["risk"] == "REVIEW"


def test_min_age_filter_skips_recent_files(tmp_path, monkeypatch):
    d = tmp_path / "a"
    d.mkdir()
    old, new = d / "old.tmp", d / "new.tmp"
    old.write_bytes(b"o" * 10)
    new.write_bytes(b"n" * 10)
    past = time.time() - 3 * 86400
    os.utime(old, (past, past))
    scanner = _setup(tmp_path, monkeypatch, [_target(d, min_age_days=1)])
    paths = [p for p, _ in scanner.scan_results[0]["files"]]
    assert str(old) in paths and str(new) not in paths


def test_excluded_extensions_are_never_collected(tmp_path, monkeypatch):
    d = tmp_path / "a"
    d.mkdir()
    tmp_file = d / "cache.tmp"
    lock_file = d / "app.lock"
    pid_file = d / "service.pid"
    tmp_file.write_bytes(b"t" * 50)
    lock_file.write_bytes(b"l" * 50)
    pid_file.write_bytes(b"p" * 50)
    scanner = _setup(
        tmp_path,
        monkeypatch,
        [_target(d, exclude_extensions=TEMP_EXCLUDE_EXTENSIONS)],
    )
    paths = [p for p, _ in scanner.scan_results[0]["files"]]
    assert str(tmp_file) in paths
    assert str(lock_file) not in paths
    assert str(pid_file) not in paths


def test_active_service_forces_skip_decision(tmp_path, monkeypatch):
    d = tmp_path / "wua"
    d.mkdir()
    (d / "update.cab").write_bytes(b"u" * 1024)
    monkeypatch.setattr(
        "src.scanner.SystemScanner.is_service_running",
        staticmethod(lambda name: name == "wuauserv"),
    )
    scanner = _setup(
        tmp_path,
        monkeypatch,
        [_target(d, category="Cache do Windows Update", active_service="wuauserv")],
    )
    assert scanner.scan_results[0]["ai_decision"] == "SKIP"
    assert "wuauserv" in scanner.scan_results[0]["ai_explanation"]


def test_symlinks_are_never_followed(tmp_path, monkeypatch):
    import subprocess
    outside = tmp_path / "outside"
    outside.mkdir()
    secret = outside / "secret.txt"
    secret.write_bytes(b"s" * 50)
    d = tmp_path / "a"
    d.mkdir()
    (d / "real.tmp").write_bytes(b"r" * 10)
    link_path = d / "link"
    try:
        os.symlink(outside, link_path, target_is_directory=True)
    except (OSError, NotImplementedError):
        # No Windows sem modo desenvolvedor, junctions (mklink /J) funcionam sem privilégio admin
        res = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link_path), str(outside)],
            capture_output=True,
        )
        if res.returncode != 0:
            pytest.skip("Sem suporte para symlink/junction neste ambiente")
    scanner = _setup(tmp_path, monkeypatch, [_target(d)])
    scanner.execute_cleanup(["Cat"], dry_run=False)
    assert secret.exists()


def test_file_modified_after_scan_is_preserved(tmp_path, monkeypatch):
    d = tmp_path / "a"
    d.mkdir()
    f = d / "f.tmp"
    f.write_bytes(b"x" * 100)
    scanner = _setup(tmp_path, monkeypatch, [_target(d)])
    f.write_bytes(b"x" * 500)  # alterado depois da análise
    data = scanner.execute_cleanup(["Cat"], dry_run=False)
    assert f.exists()
    assert data["deleted_files_count"] == 0
    assert data["skipped_locked_count"] == 1
    assert data["details"][0]["skip_reasons"].get("modificado após a análise") == 1


def test_file_same_size_mtime_bump_is_preserved(tmp_path, monkeypatch):
    d = tmp_path / "a"
    d.mkdir()
    f = d / "f.tmp"
    f.write_bytes(b"a" * 100)
    past = time.time() - 10
    os.utime(f, (past, past))
    scanner = _setup(tmp_path, monkeypatch, [_target(d)])
    future = time.time() + 5
    os.utime(f, (future, future))
    data = scanner.execute_cleanup(["Cat"], dry_run=False)
    assert f.exists()
    assert data["deleted_files_count"] == 0
    assert data["skipped_locked_count"] == 1


def test_review_category_goes_to_quarantine(tmp_path, monkeypatch):
    d = tmp_path / "a"
    d.mkdir()
    f = d / "dump.dmp"
    f.write_bytes(b"x" * 1024)
    scanner = _setup(tmp_path, monkeypatch, [_target(d, risk="REVIEW")])
    data = scanner.execute_cleanup(["Cat"], dry_run=False)
    assert not f.exists()
    assert data["quarantined_count"] == 1
    assert data["deleted_files_count"] == 0
    qroot = tmp_path / "localappdata" / "WinAI-Cleaner" / "quarantine"
    assert any(p.name == "dump.dmp" for p in qroot.rglob("*"))


def test_review_dry_run_does_not_move_files(tmp_path, monkeypatch):
    d = tmp_path / "a"
    d.mkdir()
    f = d / "dump.dmp"
    f.write_bytes(b"x" * 1024)
    scanner = _setup(tmp_path, monkeypatch, [_target(d, risk="REVIEW")])
    scanner.execute_cleanup(["Cat"], dry_run=True)
    assert f.exists()


def test_expired_quarantine_is_purged(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    old = tmp_path / "WinAI-Cleaner" / "quarantine" / "20200101_000000"
    old.mkdir(parents=True)
    (old / "x.bin").write_bytes(b"1")
    past = time.time() - 30 * 86400
    os.utime(old, (past, past))
    SystemScanner.purge_old_quarantine()
    assert not old.exists()


def test_empty_subdirs_removed_after_real_cleanup(tmp_path, monkeypatch):
    d = tmp_path / "a"
    sub = d / "sub"
    sub.mkdir(parents=True)
    (sub / "f.tmp").write_bytes(b"x" * 10)
    scanner = _setup(tmp_path, monkeypatch, [_target(d)])
    scanner.execute_cleanup(["Cat"], dry_run=False)
    assert d.exists() and not sub.exists()


def test_ai_response_validation():
    assert validate_ai_response({"decision": "SAFE", "explanation": "ok"})
    assert validate_ai_response({"decision": "DELETE_ALL", "explanation": "x"}) is None
    assert validate_ai_response({"decision": "SAFE"}) is None
    assert validate_ai_response("texto") is None
    long = validate_ai_response({"decision": "SKIP", "explanation": "a" * 1000})
    assert len(long["explanation"]) == 300


def test_ai_invalid_llm_output_falls_back_to_heuristic(monkeypatch):
    monkeypatch.setattr("src.ai_engine.AIEngine._check_ollama", lambda self: True)
    monkeypatch.setattr(
        "src.ai_engine.AIEngine._ask_ollama", lambda self, c, p, s, risk="SAFE": None
    )
    result = AIEngine().evaluate_category("Windows Prefetch", "C:\\x")
    assert result["engine"].startswith("Heurística")


def test_ai_review_heuristic_mentions_quarantine(monkeypatch):
    monkeypatch.setattr("src.ai_engine.AIEngine._check_ollama", lambda self: False)
    result = AIEngine().evaluate_category("Relatórios de Falha (Crash Dumps)", "C:\\x", risk="REVIEW")
    assert "quarentena" in result["explanation"]


def test_ai_results_are_cached(monkeypatch):
    monkeypatch.setattr("src.ai_engine.AIEngine._check_ollama", lambda self: True)
    calls = []

    def fake(self, c, p, s, risk="SAFE"):
        calls.append((c, risk))
        return {"decision": "SAFE", "explanation": "ok"}

    monkeypatch.setattr("src.ai_engine.AIEngine._ask_ollama", fake)
    engine = AIEngine()
    engine.evaluate_category("A", "p")
    engine.evaluate_category("A", "p")
    assert calls == [("A", "SAFE")]


def test_report_shows_quarantine_and_escapes_html(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    d = tmp_path / "a"
    d.mkdir()
    (d / "dump.dmp").write_bytes(b"x" * 1024)
    scanner = _setup(tmp_path, monkeypatch, [_target(d, category="Cat <xss>", risk="REVIEW")])
    data = scanner.execute_cleanup(["Cat <xss>"], dry_run=False)
    path = generate_html_report(data, profile_name="<script>alert(1)</script>", open_browser=False)
    html = open(path, encoding="utf-8").read()
    assert "quarentena" in html and "REVISAR" in html
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "Cat &lt;xss&gt;" in html


def test_setup_logging_and_icon_helper(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    log = setup_logging(str(tmp_path / "logs"))
    log.info("teste log")
    for h in list(log.handlers):
        h.close()
        log.removeHandler(h)
    assert (tmp_path / "logs" / "winai.log").exists()

    icon_path = ensure_app_icon()
    assert os.path.exists(icon_path)
    assert resource_path("assets/icon.ico").endswith("icon.ico")


def test_ui_queue_scan_and_risk_selection(tmp_path, monkeypatch):
    from src.ui import WinAICleanerApp

    d_safe = tmp_path / "safe"
    d_review = tmp_path / "review"
    d_skip = tmp_path / "skip"
    for d in (d_safe, d_review, d_skip):
        d.mkdir()
        (d / "f.tmp").write_bytes(b"x" * 1024)

    targets = [
        _target(d_safe, category="SafeCat", risk="SAFE"),
        _target(d_review, category="ReviewCat", risk="REVIEW"),
        _target(d_skip, category="Cache do Windows Update", active_service="wuauserv"),
    ]
    monkeypatch.setattr("src.scanner.get_cleanup_targets", lambda: targets)
    monkeypatch.setattr("src.ai_engine.AIEngine._check_ollama", lambda self: False)
    monkeypatch.setattr(
        "src.scanner.SystemScanner.check_system_busy",
        staticmethod(lambda: (False, "Sistema livre")),
    )
    monkeypatch.setattr(
        "src.scanner.SystemScanner.is_service_running",
        staticmethod(lambda name: name == "wuauserv"),
    )

    try:
        app = WinAICleanerApp()
    except Exception as exc:
        pytest.skip(f"Ambiente sem display gráfico: {exc}")

    try:
        app.start_scan()
        deadline = time.time() + 10
        while time.time() < deadline and not app.last_results:
            app.update()
            time.sleep(0.02)

        assert len(app.last_results) == 3
        assert app.checkboxes["SafeCat"].get() is True
        assert app.checkboxes["ReviewCat"].get() is False
        assert app.checkboxes["Cache do Windows Update"].get() is False

        app.dry_run_var.set(True)
        app.on_dry_run_toggle()
        assert "Dry-Run" in app.clean_btn.cget("text")
    finally:
        app.destroy()
