import os
import ctypes
import psutil
from pathlib import Path
from src.targets import get_cleanup_targets
from src.ai_engine import AIEngine

class SystemScanner:
    def __init__(self):
        self.ai = AIEngine()
        self.scan_results = []

    @staticmethod
    def is_admin() -> bool:
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
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
        except OSError:
            return False

    def scan(self, progress_callback=None) -> list:
        targets = get_cleanup_targets()
        self.scan_results = []
        total_targets = len(targets)

        for idx, target in enumerate(targets):
            folder = Path(target["path"])
            prefix_filter = target.get("filter_prefix", None)
            files_found = []
            total_bytes = 0
            sample_file = ""

            try:
                for root, _, files in os.walk(folder):
                    for file in files:
                        if prefix_filter and not file.lower().startswith(prefix_filter.lower()):
                            continue
                        fp = os.path.join(root, file)
                        try:
                            size = os.path.getsize(fp)
                            files_found.append((fp, size))
                            total_bytes += size
                            if not sample_file:
                                sample_file = fp
                        except OSError:
                            continue
            except PermissionError:
                pass

            if total_bytes > 0:
                ai_eval = self.ai.evaluate_category(
                    target["category"], target["path"], sample_file
                )
                self.scan_results.append({
                    "category": target["category"],
                    "path": target["path"],
                    "description": target["description"],
                    "profiles": target["profiles"],
                    "files": files_found,
                    "file_count": len(files_found),
                    "size_bytes": total_bytes,
                    "size_mb": round(total_bytes / (1024 * 1024), 2),
                    "ai_decision": ai_eval["decision"],
                    "ai_explanation": ai_eval["explanation"],
                    "ai_engine": ai_eval["engine"]
                })

            if progress_callback:
                progress_callback((idx + 1) / max(total_targets, 1), f"Analisando: {target['category']}...")

        return self.scan_results

    def execute_cleanup(self, selected_categories: list, dry_run: bool = False, progress_callback=None) -> dict:
        total_freed_bytes = 0
        deleted_files_count = 0
        skipped_locked_count = 0
        details = []

        active_items = [item for item in self.scan_results if item["category"] in selected_categories]
        total_groups = len(active_items)

        for idx, item in enumerate(active_items):
            cat_freed = 0
            cat_deleted = 0
            cat_skipped = 0

            for filepath, size in item["files"]:
                if dry_run:
                    if self._can_simulate_delete(filepath):
                        cat_freed += size
                        cat_deleted += 1
                    else:
                        cat_skipped += 1
                else:
                    try:
                        os.remove(filepath)
                        cat_freed += size
                        cat_deleted += 1
                    except OSError:
                        cat_skipped += 1

            total_freed_bytes += cat_freed
            deleted_files_count += cat_deleted
            skipped_locked_count += cat_skipped

            details.append({
                "category": item["category"],
                "path": item["path"],
                "freed_mb": round(cat_freed / (1024 * 1024), 2),
                "deleted_count": cat_deleted,
                "skipped_count": cat_skipped,
                "ai_explanation": item["ai_explanation"],
                "ai_engine": item["ai_engine"]
            })

            if progress_callback:
                mode_label = "Simulando" if dry_run else "Limpando"
                progress_callback((idx + 1) / max(total_groups, 1), f"{mode_label}: {item['category']}...")

        return {
            "dry_run": dry_run,
            "total_freed_mb": round(total_freed_bytes / (1024 * 1024), 2),
            "total_freed_gb": round(total_freed_bytes / (1024 * 1024 * 1024), 3),
            "deleted_files_count": deleted_files_count,
            "skipped_locked_count": skipped_locked_count,
            "details": details
        }
