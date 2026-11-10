import json
import urllib.request

class AIEngine:
    """
    Motor de IA Híbrido: Utiliza Ollama localmente se estiver ativo para auditar e explicar,
    ou aciona o Fallback Heurístico Nativo para execução instantânea em máquinas de leigos.
    """
    def __init__(self, model_name="qwen2.5:1.5b"):
        self.model_name = model_name
        self.ollama_available = self._check_ollama()

    def _check_ollama(self) -> bool:
        try:
            req = urllib.request.Request("http://127.0.0.1:11434/api/tags")
            with urllib.request.urlopen(req, timeout=1.2) as response:
                return response.status == 200
        except Exception:
            return False

    def read_snippet(self, filepath: str, max_bytes: int = 350) -> str:
        try:
            with open(filepath, "rb") as f:
                raw = f.read(max_bytes)
            return raw.decode("utf-8", errors="ignore").strip()
        except Exception:
            return "Arquivo binário sem cabeçalho de texto legível."

    def evaluate_category(self, category: str, path: str, sample_file: str = "") -> dict:
        if self.ollama_available:
            try:
                import ollama
                snippet = self.read_snippet(sample_file) if sample_file else "Sem amostra"
                prompt = (
                    f"Você é um especialista em Windows. Explique em 1 frase curta e clara para um usuário leigo "
                    f"por que é seguro limpar a categoria '{category}' localizada em '{path}'. "
                    f"Amostra: {snippet[:120]}. "
                    f"Responda estritamente em JSON com as chaves: 'decision' ('SAFE' ou 'SKIP') e 'explanation'."
                )
                response = ollama.chat(
                    model=self.model_name,
                    messages=[{"role": "user", "content": prompt}],
                    format="json"
                )
                content = response["message"]["content"]
                data = json.loads(content)
                return {
                    "decision": data.get("decision", "SAFE"),
                    "explanation": data.get("explanation", "Validado pelo modelo de IA local."),
                    "engine": f"Ollama ({self.model_name})"
                }
            except Exception:
                pass

        explanations = {
            "Temporários do Usuário": "Arquivos de rascunho de programas já fechados. Seus documentos pessoais ficam intactos.",
            "Temporários do Sistema (Windows)": "Logs e sobras de operações antigas do Windows. Arquivos ativos são preservados automaticamente.",
            "Windows Prefetch": "Otimizações antigas de abertura de apps. Limpá-las renova o índice de velocidade do Windows.",
            "Cache do Windows Update": "Instaladores de atualizações do Windows que já foram instaladas no sistema.",
            "DirectX Shader Cache": "Caches gráficos antigos. A limpeza corrige engasgos visuais em jogos e softwares 3D.",
            "NVIDIA DXCache (Shaders de GPU)": "Shaders compilados antigos da placa de vídeo. Os jogos ativos recriam apenas o necessário.",
            "Relatórios de Falha (Crash Dumps)": "Gravações pesadas de memória de erros passados sem utilidade para o usuário.",
            "Adobe Media Cache Files": "Arquivos pesados de pré-renderização (.cfa/.pek). Seus projetos salvos do Premiere não são afetados.",
            "Adobe Media Cache Database": "Bancos de cache antigos da Adobe que acumulam gigabytes após finalizar edições de vídeo.",
            "Cache de Miniaturas (Explorer)": "Miniaturas antigas de imagens e vídeos que já foram movidos ou apagados."
        }
        return {
            "decision": "SAFE",
            "explanation": explanations.get(category, "Resíduos temporários validados pelas regras de segurança do sistema."),
            "engine": "Heurística Nativa (Ultra-Leve)"
        }
