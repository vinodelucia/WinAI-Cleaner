import os
import re
import stat
import time
import shutil
import ctypes
import logging
import psutil
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from src.targets import get_cleanup_targets
from src.ai_engine import AIEngine

logger = logging.getLogger("winai")

FILE_ATTRIBUTE_REPARSE_POINT = 0x400
QUARANTINE_DAYS = 7
MB = 1024 * 1024


def quarantine_root() -> str:
    base = os.environ.get("LOCALAPPDATA") or os.path.abspath(".")
    return os.path.join(base, "WinAI-Cleaner", "quarantine")


def _is_reparse(st: os.stat_result) -> bool:
    """Detecta links simbólicos e junctions (reparse points) do Windows."""
    return stat.S_ISLNK(st.st_mode) or bool(
        getattr(st, "st_file_attributes", 0) & FILE_ATTRIBUTE_REPARSE_POINT
    )


def _is_within(path: str, root: str) -> bool:
    try:
        real_path = os.path.normcase(os.path.realpath(path))
        real_root = os.path.normcase(os.path.realpath(root))
        return os.path.commonpath([real_path, real_root]) == real_root
    except ValueError:
        return False


class SystemScanner:
    def __init__(self):
        self.ai = AIEngine()
        self.scan_results = []

    @staticmethod
    def is_admin() -> bool:
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception as exc:
            logger.debug("Verificação de administrador indisponível: %s", exc)
            return False

    @staticmethod
    def is_service_running(service_name: str) -> bool:
        """Verifica de forma segura se um serviço Windows está em execução."""
        if not hasattr(psutil, "win_service_get"):
            return False
        try:
            service = psutil.win_service_get(service_name)
            return service.status() == "running"
        except Exception as exc:
            logger.debug("Consulta ao serviço '%s' indisponível: %s", service_name, exc)
            return False

    @staticmethod
    def check_system_busy() -> tuple[bool, str]:
        cpu_usage = psutil.cpu_percent(interval=0.4)
        if cpu_usage >= 85.0:
            return True, f"Uso de CPU elevado ({cpu_usage}%). Recomendado aguardar renderizações ou jogos fecharem."
        return False, f"Sistema livre (CPU em {cpu_usage}%)."

    @staticmethod
    def _can_simulate_delete(filepath: str) -> bool:
        """
        No Modo Simulação (Dry-Run), verifica se o arquivo está livre de bloqueios de outros processos
        sem apagar um único byte do disco.
        """
        if not os.access(filepath, os.W_OK):
            return False
        try:
            with open(filepath, "ab"):
                pass
            return True
        except OSError as exc:
            logger.info("Simulação: arquivo bloqueado %s (%s)", filepath, exc)
            return False

    @staticmethod
    def _iter_files(
        root: str,
        prefix: str | None,
        cutoff: float | None,
        exclude_extensions: tuple[str, ...] = (),
    ):
        """
        Varredura eficiente com os.scandir (reaproveita o stat). Ignora links simbólicos,
        junctions, extensões protegidas e arquivos mais novos que o corte de idade.
        """
        prefix_l = prefix.lower() if prefix else None
        excluded = tuple(ext.lower() for ext in exclude_extensions)
        stack = [root]
        while stack:
            current = stack.pop()
            try:
                with os.scandir(current) as it:
                    entries = list(it)
            except OSError as exc:
                logger.info("Sem acesso a %s: %s", current, exc)
                continue
            for entry in entries:
                try:
                    st = entry.stat(follow_symlinks=False)
                    if _is_reparse(st):
                        continue
                    if entry.is_dir(follow_symlinks=False):
                        stack.append(entry.path)
                        continue
                    if not entry.is_file(follow_symlinks=False):
                        continue
                    name_l = entry.name.lower()
                    if prefix_l and not name_l.startswith(prefix_l):
                        continue
                    if excluded and name_l.endswith(excluded):
                        continue
                    if cutoff is not None and st.st_mtime > cutoff:
                        continue
                    yield entry.path, st.st_size, st.st_mtime
                except OSError as exc:
                    logger.info("Ignorando %s: %s", entry.path, exc)

    def _scan_target(self, target: dict) -> dict | None:
        prefix = target.get("filter_prefix")
        min_age = target.get("min_age_days", 0)
        cutoff = time.time() - min_age * 86400 if min_age else None
        exclude_exts = tuple(target.get("exclude_extensions", ()))

        files_found = []
        total_bytes = 0
        sample_file = ""
        max_mtime = 0.0
        extensions = Counter()
        for fp, size, mtime in self._iter_files(target["path"], prefix, cutoff, exclude_exts):
            files_found.append((fp, size))
            total_bytes += size
            if mtime > max_mtime:
                max_mtime = mtime
            extensions[os.path.splitext(fp)[1].lower() or "(sem extensão)"] += 1
            if not sample_file:
                sample_file = fp

        if total_bytes <= 0:
            return None

        scan_ref_time = max(time.time(), max_mtime)
        risk = target.get("risk", "SAFE")
        stats = {
            "file_count": len(files_found),
            "size_mb": round(total_bytes / MB, 2),
            "extensions": [ext for ext, _ in extensions.most_common(5)],
        }

        active_service = target.get("active_service")
        if active_service and self.is_service_running(active_service):
            ai_eval = {
                "decision": "SKIP",
                "explanation": (
                    f"Serviço '{active_service}' em execução no momento; limpeza desmarcada "
                    "automaticamente para não interromper operações ativas."
                ),
                "engine": "Guarda Operacional (Serviço Ativo)",
            }
        else:
            ai_eval = self.ai.evaluate_category(
                target["category"], target["path"], sample_file, risk=risk, stats=stats
            )

        return {
            "category": target["category"],
            "path": target["path"],
            "description": target["description"],
            "profiles": target["profiles"],
            "risk": risk,
            "filter_prefix": prefix,
            "scan_ref_time": scan_ref_time,
            "files": files_found,
            "file_count": len(files_found),
            "size_bytes": total_bytes,
            "size_mb": round(total_bytes / MB, 2),
            "ai_decision": ai_eval["decision"],
            "ai_explanation": ai_eval["explanation"],
            "ai_engine": ai_eval["engine"],
        }

    def scan(self, progress_callback=None) -> list:
        targets = get_cleanup_targets()
        self.scan_results = []
        total_targets = len(targets)
        self.purge_old_quarantine()

        if total_targets == 0:
            return self.scan_results

        done = 0
        results = [None] * total_targets
        with ThreadPoolExecutor(max_workers=min(4, total_targets)) as pool:
            futures = {pool.submit(self._scan_target, t): i for i, t in enumerate(targets)}
            for fut in as_completed(futures):
                idx = futures[fut]
                try:
                    results[idx] = fut.result()
                except Exception as exc:
                    logger.error("Falha ao analisar '%s': %s", targets[idx]["category"], exc)
                done += 1
                if progress_callback:
                    progress_callback(
                        done / total_targets,
                        f"Analisando: {targets[idx]['category']}...",
                    )

        self.scan_results = [r for r in results if r]
        return self.scan_results

    @staticmethod
    def _revalidate(
        filepath: str,
        expected_size: int,
        root: str,
        scan_ref_time: float | None = None,
    ) -> str:
        """Reconfere o arquivo imediatamente antes de apagar. Retorna 'ok' ou o motivo."""
        try:
            st = os.lstat(filepath)
        except OSError:
            return "inexistente"
        if _is_reparse(st):
            return "link/junction"
        if not stat.S_ISREG(st.st_mode):
            return "não é arquivo comum"
        if st.st_size != expected_size:
            return "modificado após a análise"
        if scan_ref_time is not None and st.st_mtime > scan_ref_time:
            return "modificado após a análise"
        if not _is_within(filepath, root):
            return "fora do diretório alvo"
        return "ok"

    @staticmethod
    def _quarantine(filepath: str, root: str, category: str, stamp: str) -> None:
        slug = re.sub(r"\W+", "_", category).strip("_") or "categoria"
        dest = os.path.join(quarantine_root(), stamp, slug, os.path.relpath(filepath, root))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.move(filepath, dest)

    @staticmethod
    def purge_old_quarantine(days: int = QUARANTINE_DAYS) -> None:
        qroot = quarantine_root()
        if not os.path.isdir(qroot):
            return
        limit = time.time() - days * 86400
        for name in os.listdir(qroot):
            folder = os.path.join(qroot, name)
            try:
                if os.path.isdir(folder) and os.path.getmtime(folder) < limit:
                    shutil.rmtree(folder)
                    logger.info("Quarentena expirada removida: %s", folder)
            except OSError as exc:
                logger.warning("Falha ao limpar quarentena %s: %s", folder, exc)

    @staticmethod
    def _remove_empty_dirs(root: str) -> None:
        """Remove subdiretórios vazios de baixo para cima sem seguir links ou junctions."""
        dirs_to_check = []
        stack = [root]
        while stack:
            current = stack.pop()
            try:
                with os.scandir(current) as it:
                    entries = list(it)
            except OSError as exc:
                logger.debug("Não foi possível listar %s: %s", current, exc)
                continue
            for entry in entries:
                try:
                    st = entry.stat(follow_symlinks=False)
                    if _is_reparse(st):
                        continue
                    if entry.is_dir(follow_symlinks=False):
                        dirs_to_check.append(entry.path)
                        stack.append(entry.path)
                except OSError as exc:
                    logger.debug("Ignorando subdiretório %s: %s", entry.path, exc)

        for dirpath in reversed(dirs_to_check):
            try:
                if _is_reparse(os.lstat(dirpath)):
                    continue
                os.rmdir(dirpath)
            except OSError as exc:
                logger.debug("Diretório preservado (%s): %s", dirpath, exc)

    def execute_cleanup(self, selected_categories: list, dry_run: bool = False, progress_callback=None) -> dict:
        total_freed_bytes = 0
        total_quarantined_bytes = 0
        deleted_files_count = 0
        quarantined_count = 0
        skipped_locked_count = 0
        details = []
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        active_items = [item for item in self.scan_results if item["category"] in selected_categories]
        total_groups = len(active_items)

        for idx, item in enumerate(active_items):
            cat_freed = 0
            cat_deleted = 0
            cat_skipped = 0
            cat_quarantined = 0
            cat_quarantined_bytes = 0
            skip_reasons = Counter()
            use_quarantine = item.get("risk") == "REVIEW" and not dry_run
            root = item["path"]
            scan_ref_time = item.get("scan_ref_time")

            for filepath, size in item["files"]:
                reason = self._revalidate(filepath, size, root, scan_ref_time=scan_ref_time)
                if reason != "ok":
                    logger.info("Preservado %s (%s)", filepath, reason)
                    skip_reasons[reason] += 1
                    cat_skipped += 1
                    continue

                if dry_run:
                    if self._can_simulate_delete(filepath):
                        cat_freed += size
                        cat_deleted += 1
                    else:
                        skip_reasons["em uso / sem permissão"] += 1
                        cat_skipped += 1
                elif use_quarantine:
                    try:
                        self._quarantine(filepath, root, item["category"], stamp)
                        cat_quarantined += 1
                        cat_quarantined_bytes += size
                    except OSError as exc:
                        logger.info("Preservado %s (%s)", filepath, exc)
                        skip_reasons["em uso / sem permissão"] += 1
                        cat_skipped += 1
                else:
                    try:
                        os.remove(filepath)
                        cat_freed += size
                        cat_deleted += 1
                    except OSError as exc:
                        logger.info("Em uso, preservado %s (%s)", filepath, exc)
                        skip_reasons["em uso / sem permissão"] += 1
                        cat_skipped += 1

            if not dry_run and not item.get("filter_prefix"):
                self._remove_empty_dirs(root)

            total_freed_bytes += cat_freed
            total_quarantined_bytes += cat_quarantined_bytes
            deleted_files_count += cat_deleted
            quarantined_count += cat_quarantined
            skipped_locked_count += cat_skipped

            details.append({
                "category": item["category"],
                "path": item["path"],
                "risk": item.get("risk", "SAFE"),
                "freed_mb": round(cat_freed / MB, 2),
                "deleted_count": cat_deleted,
                "skipped_count": cat_skipped,
                "skip_reasons": dict(skip_reasons),
                "quarantined_count": cat_quarantined,
                "quarantined_mb": round(cat_quarantined_bytes / MB, 2),
                "ai_explanation": item["ai_explanation"],
                "ai_engine": item["ai_engine"]
            })
            logger.info(
                "%s | %s: %d removidos, %d em quarentena, %d preservados",
                "DRY-RUN" if dry_run else "REAL", item["category"],
                cat_deleted, cat_quarantined, cat_skipped,
            )

            if progress_callback:
                mode_label = "Simulando" if dry_run else "Limpando"
                progress_callback((idx + 1) / max(total_groups, 1), f"{mode_label}: {item['category']}...")

        return {
            "dry_run": dry_run,
            "total_freed_mb": round(total_freed_bytes / MB, 2),
            "total_freed_gb": round(total_freed_bytes / (MB * 1024), 3),
            "total_quarantined_mb": round(total_quarantined_bytes / MB, 2),
            "deleted_files_count": deleted_files_count,
            "quarantined_count": quarantined_count,
            "skipped_locked_count": skipped_locked_count,
            "details": details
        }
