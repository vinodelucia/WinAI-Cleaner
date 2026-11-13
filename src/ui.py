import queue
import logging
import threading
import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox
from src import __version__
from src.scanner import SystemScanner, quarantine_root
from src.targets import PROFILES
from src.report_generator import generate_html_report
from src.icon_helper import ensure_app_icon

logger = logging.getLogger("winai")

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class WinAICleanerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"WinAI-Cleaner v{__version__} | Limpeza Inteligente de Uso Único")
        self.geometry("880x650")
        self.resizable(False, False)

        # Configura o ícone nativo .ico na janela
        try:
            icon_path = ensure_app_icon()
            self.iconbitmap(icon_path)
        except Exception as exc:
            logger.warning("Não foi possível aplicar o ícone: %s", exc)

        self.events: queue.Queue = queue.Queue()
        self.scanner = SystemScanner()
        self.checkboxes: dict[str, ctk.BooleanVar] = {}
        self.checkbox_widgets: dict[str, ctk.CTkCheckBox] = {}
        self.cleaned_categories: set[str] = set()
        self.current_profile = PROFILES[0]
        self.last_results: list[dict] = []
        self._poll_after_id = None

        self._build_ui()
        self._poll_after_id = self.after(50, self._poll_events)

    def destroy(self):
        if self._poll_after_id is not None:
            try:
                self.after_cancel(self._poll_after_id)
            except tk.TclError as exc:
                logger.debug("Cancelamento de timer após fechamento: %s", exc)
            self._poll_after_id = None
        super().destroy()

    def _build_ui(self):
        # 1. Cabeçalho Superior
        header = ctk.CTkFrame(self, corner_radius=10)
        header.pack(fill="x", padx=20, pady=(18, 8))

        title_lbl = ctk.CTkLabel(
            header, text="WinAI-Cleaner", font=ctk.CTkFont(size=24, weight="bold")
        )
        title_lbl.pack(side="left", padx=15, pady=12)

        admin_status = "Admin Ativo" if self.scanner.is_admin() else "Usuário Padrão"
        ai_status = "IA Local (Ollama)" if self.scanner.ai.ollama_available else "Heurística Nativa"

        status_badge = ctk.CTkLabel(
            header,
            text=f"{admin_status}  •  {ai_status}",
            font=ctk.CTkFont(size=12),
            text_color="#38bdf8"
        )
        status_badge.pack(side="right", padx=15)

        # 2. Barra de Perfis e Chave de Simulação (Dry-Run)
        ctrl_frame = ctk.CTkFrame(self, corner_radius=10)
        ctrl_frame.pack(fill="x", padx=20, pady=6)

        prof_lbl = ctk.CTkLabel(
            ctrl_frame, text="Perfil:", font=ctk.CTkFont(size=13, weight="bold")
        )
        prof_lbl.pack(side="left", padx=(15, 8), pady=10)

        self.profile_selector = ctk.CTkSegmentedButton(
            ctrl_frame,
            values=PROFILES,
            command=self.on_profile_change
        )
        self.profile_selector.set(PROFILES[0])
        self.profile_selector.pack(side="left", padx=5, pady=10)

        self.dry_run_var = ctk.BooleanVar(value=False)
        self.dry_run_switch = ctk.CTkSwitch(
            ctrl_frame,
            text="Modo Simulação (Dry-Run)",
            variable=self.dry_run_var,
            command=self.on_dry_run_toggle,
            font=ctk.CTkFont(size=12, weight="bold"),
            progress_color="#eab308"
        )
        self.dry_run_switch.pack(side="right", padx=15, pady=10)

        # 3. Área Central de Resultados
        self.scroll_frame = ctk.CTkScrollableFrame(
            self, label_text="Categorias Auditadas (Selecione um perfil acima ou marque manualmente)"
        )
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=8)

        self.empty_lbl = ctk.CTkLabel(
            self.scroll_frame,
            text="Clique em '1. Analisar Computador' para mapear caches de Jogos, Vídeo (Adobe) e Sistema.",
            text_color="#94a3b8"
        )
        self.empty_lbl.pack(pady=90)

        # 4. Barra de Progresso e Status
        self.progress = ctk.CTkProgressBar(self)
        self.progress.pack(fill="x", padx=20, pady=(4, 4))
        self.progress.set(0)

        self.status_lbl = ctk.CTkLabel(
            self, text="Pronto para iniciar. Zero processos em segundo plano.", font=ctk.CTkFont(size=12)
        )
        self.status_lbl.pack(padx=20, pady=(0, 8))

        # 5. Botões de Ação
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(0, 18))

        self.scan_btn = ctk.CTkButton(
            btn_frame, text="1. Analisar Computador", height=42, command=self.start_scan
        )
        self.scan_btn.pack(side="left", expand=True, fill="x", padx=(0, 10))

        self.clean_btn = ctk.CTkButton(
            btn_frame,
            text="2. Limpar e Gerar Relatório",
            height=42,
            fg_color="#16a34a",
            hover_color="#15803d",
            state="disabled",
            command=self.start_cleanup
        )
        self.clean_btn.pack(side="left", expand=True, fill="x", padx=(10, 10))

        self.exit_btn = ctk.CTkButton(
            btn_frame,
            text="Fechar App",
            height=42,
            fg_color="#475569",
            hover_color="#334155",
            command=self.destroy
        )
        self.exit_btn.pack(side="right", padx=(10, 0))

    def on_dry_run_toggle(self):
        if self.dry_run_var.get():
            self.clean_btn.configure(
                text="2. Simular Limpeza (Dry-Run)",
                fg_color="#ca8a04",
                hover_color="#a16207"
            )
        else:
            self.clean_btn.configure(
                text="2. Limpar e Gerar Relatório",
                fg_color="#16a34a",
                hover_color="#15803d"
            )

    def _recalculate_selected(self):
        if not self.last_results:
            return
        selected_mb = 0.0
        for item in self.last_results:
            cat = item["category"]
            var = self.checkboxes.get(cat)
            if var is not None and var.get():
                selected_mb += item["size_mb"]
        self.status_lbl.configure(
            text=f"Perfil '{self.current_profile}' aplicado! Espaço selecionado para liberação: {round(selected_mb, 2)} MB."
        )

    def on_profile_change(self, selected_profile: str):
        self.current_profile = selected_profile
        if not self.last_results:
            self.status_lbl.configure(text=f"Perfil '{selected_profile}' selecionado. Clique em Analisar.")
            return

        for item in self.last_results:
            cat = item["category"]
            if cat in self.checkboxes and cat not in self.cleaned_categories:
                should_check = (
                    (selected_profile in item["profiles"])
                    and (item["ai_decision"] == "SAFE")
                    and (item.get("risk") == "SAFE")
                )
                self.checkboxes[cat].set(should_check)

        self._recalculate_selected()

    def _update_progress(self, value: float, text: str):
        # Chamado a partir de threads de trabalho: apenas enfileira (thread-safe).
        self.events.put(("progress", value, text))

    def _poll_events(self):
        while True:
            try:
                event = self.events.get_nowait()
            except queue.Empty:
                break
            kind = event[0]
            if kind == "progress":
                self.progress.set(event[1])
                self.status_lbl.configure(text=event[2])
            elif kind == "scan_done":
                self._populate_results(event[1])
            elif kind == "clean_done":
                self._finish_cleanup_ui(event[1], event[2])
            elif kind == "error":
                self._show_error(event[1])
        self._poll_after_id = self.after(50, self._poll_events)

    def _show_error(self, message: str):
        self.scan_btn.configure(state="normal")
        has_pending = any(c not in self.cleaned_categories for c in self.checkboxes)
        self.clean_btn.configure(state="normal" if has_pending else "disabled")
        self.status_lbl.configure(text="Ocorreu um erro. Consulte reports/winai.log.")
        messagebox.showerror("Erro", message)

    def start_scan(self):
        busy, msg = self.scanner.check_system_busy()
        if busy:
            if not messagebox.askyesno("Sistema Ocupado", f"{msg}\nDeseja analisar mesmo assim?"):
                return

        self.scan_btn.configure(state="disabled")
        self.clean_btn.configure(state="disabled")
        self.progress.set(0)
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        threading.Thread(target=self._run_scan_thread, daemon=True).start()

    def _run_scan_thread(self):
        try:
            results = self.scanner.scan(progress_callback=self._update_progress)
            self.events.put(("scan_done", results))
        except Exception as exc:
            logger.exception("Falha na análise")
            self.events.put(("error", f"Falha durante a análise: {exc}"))

    def _populate_results(self, results: list):
        self.last_results = results
        self.checkboxes.clear()
        self.checkbox_widgets.clear()
        self.cleaned_categories.clear()

        if not results:
            lbl = ctk.CTkLabel(self.scroll_frame, text="Nenhum lixo temporário encontrado no momento.")
            lbl.pack(pady=60)
            self.status_lbl.configure(text="Análise concluída. Seu sistema já está limpo!")
            self.scan_btn.configure(state="normal")
            return

        for item in results:
            row = ctk.CTkFrame(self.scroll_frame, corner_radius=8)
            row.pack(fill="x", pady=5, padx=5)

            is_in_profile = (
                (self.current_profile in item["profiles"])
                and (item["ai_decision"] == "SAFE")
                and (item.get("risk") == "SAFE")
            )
            var = ctk.BooleanVar(value=is_in_profile)

            profiles_str = " | ".join(item["profiles"])
            if item.get("ai_decision") == "SKIP":
                tag = "  ⛔ IGNORADO (em uso/serviço ativo)"
            elif item.get("risk") == "REVIEW":
                tag = "  ⚠ REVISAR (quarentena 7 dias)"
            else:
                tag = ""

            cb = ctk.CTkCheckBox(
                row,
                text=f"{item['category']}{tag}  ({item['size_mb']} MB • {item['file_count']} arq.)",
                variable=var,
                command=self._recalculate_selected,
                font=ctk.CTkFont(size=14, weight="bold")
            )
            cb.pack(anchor="w", padx=12, pady=(10, 2))

            desc = ctk.CTkLabel(
                row,
                text=f"[{profiles_str}] — {item['ai_explanation']}",
                font=ctk.CTkFont(size=12),
                text_color="#94a3b8"
            )
            desc.pack(anchor="w", padx=38, pady=(0, 8))

            self.checkboxes[item["category"]] = var
            self.checkbox_widgets[item["category"]] = cb

        self.on_profile_change(self.current_profile)
        self.scan_btn.configure(state="normal")
        self.clean_btn.configure(state="normal")

    def start_cleanup(self):
        selected = [cat for cat, var in self.checkboxes.items() if var.get()]
        if not selected:
            messagebox.showwarning("Aviso", "Selecione pelo menos uma categoria para continuar.")
            return

        is_dry = self.dry_run_var.get()
        review_selected = [
            item["category"]
            for item in self.last_results
            if item["category"] in selected and item.get("risk") == "REVIEW"
        ]
        if review_selected and not is_dry:
            proceed = messagebox.askyesno(
                "Categorias para revisão",
                "As categorias abaixo serão movidas para uma quarentena de 7 dias "
                "(não liberam espaço em disco imediatamente):\n\n"
                + "\n".join(review_selected)
                + "\n\nContinuar?",
            )
            if not proceed:
                return

        self.scan_btn.configure(state="disabled")
        self.clean_btn.configure(state="disabled")
        threading.Thread(
            target=self._run_cleanup_thread,
            args=(selected, is_dry),
            daemon=True
        ).start()

    def _run_cleanup_thread(self, selected: list, is_dry: bool):
        try:
            cleanup_data = self.scanner.execute_cleanup(
                selected, dry_run=is_dry, progress_callback=self._update_progress
            )
            report_path = generate_html_report(
                cleanup_data, profile_name=self.current_profile, open_browser=True
            )
            self.events.put(("clean_done", cleanup_data, report_path))
        except Exception as exc:
            logger.exception("Falha na limpeza")
            self.events.put(("error", f"Falha durante a limpeza: {exc}"))

    def _finish_cleanup_ui(self, cleanup_data: dict, report_path: str):
        is_dry = cleanup_data["dry_run"]
        title = "Simulação (Dry-Run) Concluída!" if is_dry else "Limpeza Concluída com Sucesso!"
        action_verb = "Espaço que seria liberado" if is_dry else "Espaço efetivamente liberado"

        if not is_dry:
            for detail in cleanup_data.get("details", []):
                cat = detail["category"]
                self.cleaned_categories.add(cat)
                if cat in self.checkboxes:
                    self.checkboxes[cat].set(False)
                if cat in self.checkbox_widgets:
                    self.checkbox_widgets[cat].configure(
                        state="disabled",
                        text=f"{cat}  [Processado nesta sessão]"
                    )

        quarantined_info = ""
        if cleanup_data.get("quarantined_count"):
            quarantined_info = (
                f"Arquivos em quarentena (7 dias): {cleanup_data['quarantined_count']} "
                f"({cleanup_data['total_quarantined_mb']} MB)\n"
                f"Pasta de quarentena: {quarantine_root()}\n"
            )

        self.status_lbl.configure(
            text=f"{title} {cleanup_data['total_freed_mb']} MB auditados. Relatório aberto no navegador."
        )
        messagebox.showinfo(
            title,
            f"Perfil utilizado: {self.current_profile}\n"
            f"{action_verb}: {cleanup_data['total_freed_mb']} MB\n"
            f"Arquivos processados: {cleanup_data['deleted_files_count']}\n"
            f"{quarantined_info}"
            f"Arquivos preservados (em uso/protegidos): {cleanup_data['skipped_locked_count']}\n\n"
            f"Relatório salvo em: {report_path}"
        )
        self.scan_btn.configure(state="normal")
        has_pending = any(c not in self.cleaned_categories for c in self.checkboxes)
        self.clean_btn.configure(state="normal" if (is_dry or has_pending) else "disabled")
