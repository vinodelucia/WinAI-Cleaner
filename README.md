<div align="center">

# ✨ WinAI-Cleaner v2.1
### *Run-and-Done Intelligent Windows Cache & Temp Cleaner*
**Utilitário Open-Source ultraleve para limpeza auditada de caches e arquivos temporários no Windows 10/11.**

[![CI/CD Build & Test](https://github.com/vinodelucia/WinAI-Cleaner/actions/workflows/build_exe.yml/badge.svg)](https://github.com/vinodelucia/WinAI-Cleaner/actions/workflows/build_exe.yml)
[![Latest Release](https://img.shields.io/github/v/release/vinodelucia/WinAI-Cleaner?color=38bdf8&label=Release&logo=github)](https://github.com/vinodelucia/WinAI-Cleaner/releases/latest)
[![Downloads](https://img.shields.io/github/downloads/vinodelucia/WinAI-Cleaner/total?color=4ade80&label=Downloads&logo=windows)](https://github.com/vinodelucia/WinAI-Cleaner/releases/latest)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D6?logo=windows&logoColor=white)](#)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

<br>

### 🚀 [**BAIXAR EXECUTÁVEL PORTÁTIL (.EXE) / DOWNLOAD LATEST RELEASE**](https://github.com/vinodelucia/WinAI-Cleaner/releases/latest/download/WinAI-Cleaner.exe)
*(Não requer instalação • Zero processos em segundo plano / No installation required • Zero background services)*

<br>

[**🇧🇷 Português**](#-português-pt-br) &nbsp;•&nbsp; [**🇺🇸 English**](#-english-en)

</div>

---

## 🇧🇷 Português (PT-BR)

### 🎯 Visão Geral
Muitos "otimizadores de PC" acabam se tornando o próprio problema que prometem resolver: instalam serviços ocultos, rodam em segundo plano consumindo memória RAM e atrapalham o desempenho durante jogos ou renderizações pesadas.

O **WinAI-Cleaner** foi projetado sob a filosofia **Run-and-Done (Abriu, Limpou, Fechou)**:
1. **Você abre o executável portátil** apenas quando sentir necessidade de liberar espaço.
2. **Analisa o sistema** com perfis específicos (Jogos, Edição de Vídeo, Geral ou Básico).
3. **Executa a limpeza** (ou simula via *Dry-Run*) com proteção automática de arquivos em uso.
4. **Recebe um Relatório HTML completo** explicando exatamente o que foi removido e por que era seguro apagar.
5. **Fecha o aplicativo** e 100% dos recursos do seu computador ficam livres.

### ⚡ Principais Diferenciais
* **Seletor de Perfis Inteligente:** Alterne com um clique entre **Geral (Completo)**, **Modo Gamer**, **Edição de Vídeo** e **Básico do Sistema**.
* **Motor Híbrido (IA Local + Heurística Nativa):** Se o [Ollama](https://ollama.com/) estiver rodando localmente na máquina, o app utiliza um Small Language Model (`qwen2.5:1.5b`) para auditar amostras e explicar cada diretório. Se o usuário for leigo e não tiver o Ollama instalado, o aplicativo ativa automaticamente o **Motor Heurístico Ultra-Leve**, funcionando sem configuração adicional.
* **Modo Simulação (Dry-Run):** Permite testar a ferramenta com segurança total. Verifica permissões e arquivos travados no disco e gera o relatório HTML mostrando quanto espaço seria liberado, sem apagar um único byte.
* **Smart Busy Check (Zero Intromissão):** Monitora o uso de CPU via `psutil` antes de iniciar a varredura e avisa caso o computador esteja ocupado com jogos ou renderizações.
* **Relatório Auditável em HTML:** Abre automaticamente no navegador um painel escuro detalhando os megabytes liberados, arquivos preservados (em uso ativo) e a justificativa de segurança de cada categoria.

### 🗂️ Diretórios e Perfis Auditados

| Categoria | Alvo no Sistema | Perfis Associados | Benefício Principal |
| :--- | :--- | :--- | :--- |
| **Temporários do Usuário** | `%TEMP%` | Todos | Remove rascunhos de softwares já fechados. |
| **Temporários do Sistema** | `C:\Windows\Temp` | Geral, Básico | Limpa logs e caches antigos de serviços do Windows. |
| **Windows Prefetch** | `C:\Windows\Prefetch` | Geral, Gamer, Básico | Renova índices de inicialização de apps e jogos. |
| **Cache do Windows Update** | `SoftwareDistribution\Download` | Geral, Básico | Apaga instaladores de atualizações já concluídas. |
| **DirectX Shader Cache** | `%LOCALAPPDATA%\D3DSCache` | Geral, Gamer, Vídeo | Corrige *stuttering* (engasgos) em jogos e engines 3D. |
| **NVIDIA DXCache** | `%LOCALAPPDATA%\NVIDIA\DXCache` | Geral, Gamer, Vídeo | Limpa shaders compilados antigos da GPU. |
| **Crash Dumps** | `%LOCALAPPDATA%\CrashDumps` | Todos | Remove despejos de memória pesados de erros passados. |
| **Adobe Media Cache** | `Adobe\Common\Media Cache Files` | Geral, Edição de Vídeo | Libera gigabytes de arquivos `.cfa` e `.pek` (Premiere/AE). |
| **Explorer Thumbcache** | `Windows\Explorer\thumbcache_*` | Geral, Vídeo, Básico | Remove miniaturas órfãs de fotos e vídeos antigos. |

### 🛠️ Como Usar

#### Opção 1: Usuário Final (Portátil `.exe`)
1. Baixe o arquivo [**WinAI-Cleaner.exe**](https://github.com/vinodelucia/WinAI-Cleaner/releases/latest/download/WinAI-Cleaner.exe) na aba Releases.
2. Execute o programa (ele solicitará permissão de Administrador automaticamente para poder limpar pastas do sistema como `C:\Windows\Temp`).
3. Escolha seu **Perfil**, clique em **1. Analisar Computador** e depois em **2. Limpar e Gerar Relatório**.

#### Opção 2: Desenvolvedores (Código-Fonte)
```bash
# 1. Clone o repositório
git clone https://github.com/vinodelucia/WinAI-Cleaner.git
cd WinAI-Cleaner

# 2. Crie e ative um ambiente virtual
python -m venv .venv
.venv\Scripts\activate

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Inicie a aplicação
python main.py
```

### 🔒 Camadas de Segurança (v2.1)
* Categorias de risco **REVIEW** (Crash Dumps, Adobe Media Cache Database) vêm desmarcadas e são movidas para uma **quarentena de 7 dias** em vez de apagadas.
* Arquivos recentes (< 1 dia) em Temp são preservados; links simbólicos/junctions nunca são seguidos.
* Cada arquivo é **revalidado imediatamente antes** de ser removido (tamanho, tipo e diretório alvo).
* O LLM recebe apenas metadados (nunca conteúdo de arquivos) e sua resposta é validada por schema.
* Log de auditoria em `reports/winai.log`. Hash SHA-256 publicado em cada Release.

### 🧪 Testes Automatizados (CI/CD Quality Gate)
O projeto conta com uma suíte de testes unitários em `pytest` que valida a varredura, filtros de segurança, proteção de arquivos em uso e garante que o **Modo Dry-Run** jamais remova arquivos reais:
```bash
python -m pytest -v
```

---

## 🇺🇸 English (EN)

### 🎯 Overview
Many PC "optimizers" become the exact bloatware they claim to fight: installing hidden daemons, running constantly in the background, and consuming RAM and CPU cycles while you game or edit videos.

**WinAI-Cleaner** is built around a strict **Run-and-Done philosophy**:
1. **Launch the portable executable** only when you want to reclaim disk space.
2. **Scan your system** using tailored profiles (Gamer, Video Editing, General, or System Basic).
3. **Clean up safely** (or preview via *Dry-Run Mode*) while active/locked files are automatically skipped.
4. **Inspect the HTML Audit Report** explaining what was removed, how much space was freed, and why each category is safe.
5. **Close the app** with zero background processes left behind.

### ⚡ Key Features
* **Smart Profile Selector:** Switch effortlessly between **General (Full)**, **Gamer Mode** (DirectX & NVIDIA Shader Caches), **Video Editing** (Adobe Premiere/After Effects `.cfa`/`.pek` media caches), and **System Basic**.
* **Hybrid AI Engine (Local Ollama + Native Heuristics):** Connects automatically to a local [Ollama](https://ollama.com/) instance (`qwen2.5:1.5b`) when available to generate human-friendly security explanations. If Ollama is not installed, it seamlessly falls back to a **Zero-Dependency Native Heuristic Engine**—making it 100% plug-and-play for non-technical users.
* **Safe Dry-Run Simulation:** Test the entire workflow and generate the final HTML report without deleting a single byte from your drive.
* **Non-Intrusive CPU Check:** Checks CPU load via `psutil` prior to scanning to ensure it never interrupts active rendering or gaming sessions.
* **Automated CI/CD Pipeline:** Every push runs unit tests (`pytest`) as a Quality Gate before compiling the standalone `.exe` via `PyInstaller` and publishing official GitHub Releases.

### 🛠️ Quick Start (From Source)
```bash
git clone https://github.com/vinodelucia/WinAI-Cleaner.git
cd WinAI-Cleaner
pip install -r requirements.txt
python main.py
```

### 📦 Building the Portable `.exe` Locally
```bash
# 1. Generate the native high-DPI Windows icon (.ico)
python -c "from src.icon_helper import ensure_app_icon; ensure_app_icon()"

# 2. Bundle into a single standalone executable
pyinstaller --noconfirm --onefile --windowed --icon=assets/icon.ico --add-data "assets/icon.ico;assets" --name "WinAI-Cleaner" main.py
```

---

## 📂 Arquitetura do Projeto / Project Structure

```text
WinAI-Cleaner/
├── .github/workflows/
│   └── build_exe.yml       # Pipeline CI/CD: Pytest Quality Gate + PyInstaller + Auto Release
├── assets/                 # Ícone nativo (.ico) gerado programaticamente
├── reports/                # Relatórios HTML de auditoria gerados localmente
├── src/
│   ├── icon_helper.py      # Gerador de ícone .ico multi-resolução (Pillow)
│   ├── logger.py           # Logging auditável em arquivo (reports/winai.log)
│   ├── targets.py          # Mapeamento de diretórios e perfis de uso
│   ├── ai_engine.py        # Motor híbrido (Ollama Local + Fallback Heurístico)
│   ├── scanner.py          # Varredura, verificação de CPU, Dry-Run, quarentena e remoção segura
│   ├── report_generator.py # Renderizador de relatórios HTML com autoescape (Jinja2)
│   └── ui.py               # Interface gráfica moderna em modo escuro (CustomTkinter)
├── tests/
│   ├── test_scanner.py     # Testes principais do scanner e relatórios
│   └── test_safety.py      # Testes de segurança, quarentena, revalidação e schema da IA
├── main.py                 # Ponto de entrada e elevação UAC (Administrador)
└── requirements.txt        # Dependências enxutas do projeto
```

## 📄 Licença / License
Distribuído sob a licença **MIT**. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.  
Distributed under the **MIT License**. See [LICENSE](LICENSE) for more information.
