import os
import webbrowser
from datetime import datetime
from jinja2 import Template

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Relatório de Auditoria - WinAI-Cleaner</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 30px; }
        .container { max-width: 900px; margin: auto; background: #1e293b; padding: 30px; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.4); }
        .header-row { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #334155; padding-bottom: 15px; }
        h1 { margin: 0; color: #38bdf8; font-size: 24px; }
        .mode-badge { padding: 6px 14px; border-radius: 20px; font-weight: bold; font-size: 13px; }
        .mode-real { background: #16a34a; color: #ffffff; }
        .mode-dry { background: #eab308; color: #0f172a; }
        .summary { display: flex; gap: 20px; margin: 22px 0; }
        .card { flex: 1; background: #0f172a; padding: 18px; border-radius: 10px; border: 1px solid #334155; text-align: center; }
        .card h2 { margin: 5px 0; color: #4ade80; font-size: 28px; }
        .card p { margin: 0; color: #94a3b8; font-size: 13px; }
        table { width: 100%; border-collapse: collapse; margin-top: 25px; }
        th, td { text-align: left; padding: 14px; border-bottom: 1px solid #334155; }
        th { color: #38bdf8; font-size: 13px; text-transform: uppercase; }
        .explanation { color: #cbd5e1; font-size: 13px; margin-top: 4px; }
        .badge { background: #0284c7; color: white; padding: 3px 8px; border-radius: 6px; font-size: 11px; }
        .footer { margin-top: 30px; text-align: center; font-size: 12px; color: #64748b; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header-row">
            <div>
                <h1>Relatório de Auditoria - WinAI-Cleaner</h1>
                <p style="margin: 5px 0 0 0; color: #94a3b8; font-size: 13px;">
                    Data: <strong>{{ timestamp }}</strong> | Perfil: <strong>{{ profile_name }}</strong>
                </p>
            </div>
            {% if report.dry_run %}
            <span class="mode-badge mode-dry">SIMULAÇÃO (DRY-RUN) • NENHUM ARQUIVO APAGADO</span>
            {% else %}
            <span class="mode-badge mode-real">LIMPEZA REAL CONCLUÍDA</span>
            {% endif %}
        </div>
        
        <div class="summary">
            <div class="card">
                <h2>{{ report.total_freed_mb }} MB</h2>
                <p>{% if report.dry_run %}Espaço Simulado ({{ report.total_freed_gb }} GB){% else %}Espaço Total Liberado ({{ report.total_freed_gb }} GB){% endif %}</p>
            </div>
            <div class="card">
                <h2>{{ report.deleted_files_count }}</h2>
                <p>{% if report.dry_run %}Arquivos Elegíveis para Remoção{% else %}Arquivos Temporários Removidos{% endif %}</p>
            </div>
            <div class="card">
                <h2>{{ report.skipped_locked_count }}</h2>
                <p>Arquivos Preservados (Em Uso Ativo)</p>
            </div>
        </div>

        <table>
            <thead>
                <tr>
                    <th>Categoria e Diretório</th>
                    <th>Volume</th>
                    <th>Arquivos</th>
                    <th>Auditoria de Segurança (Como e Por Quê)</th>
                </tr>
            </thead>
            <tbody>
                {% for item in report.details %}
                <tr>
                    <td>
                        <strong>{{ item.category }}</strong><br>
                        <small style="color:#64748b;">{{ item.path }}</small>
                    </td>
                    <td><strong>{{ item.freed_mb }} MB</strong></td>
                    <td>{{ item.deleted_count }} arq. ({{ item.skipped_count }} em uso)</td>
                    <td>
                        <span class="badge">{{ item.ai_engine }}</span>
                        <div class="explanation">{{ item.ai_explanation }}</div>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>

        <div class="footer">
            Gerado por WinAI-Cleaner v2.0 (Open-Source Run-and-Done Utility). Zero processos residentes em segundo plano.
        </div>
    </div>
</body>
</html>
"""

def generate_html_report(cleanup_data: dict, profile_name: str = "Geral (Completo)", open_browser: bool = True) -> str:
    os.makedirs("reports", exist_ok=True)
    timestamp_str = datetime.now().strftime("%d/%m/%Y às %H:%M:%S")
    file_stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    prefix = "simulacao" if cleanup_data.get("dry_run") else "limpeza"
    filepath = os.path.abspath(os.path.join("reports", f"relatorio_{prefix}_{file_stamp}.html"))

    template = Template(HTML_TEMPLATE)
    html_content = template.render(
        report=cleanup_data,
        timestamp=timestamp_str,
        profile_name=profile_name
    )

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_content)

    if open_browser:
        webbrowser.open(f"file://{filepath}")

    return filepath
