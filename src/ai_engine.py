import json
import logging
import threading
import urllib.request

logger = logging.getLogger("winai")

VALID_DECISIONS = {"SAFE", "SKIP"}
MAX_EXPLANATION_LEN = 300

HEURISTIC_EXPLANATIONS = {
    "Temporários do Usuário": "Arquivos de rascunho de programas já fechados. Seus documentos pessoais ficam intactos.",
    "Temporários do Sistema (Windows)": "Logs e sobras de operações antigas do Windows. Arquivos ativos são preservados automaticamente.",
    "Windows Prefetch": "Otimizações antigas de abertura de apps sem uso recente. Limpá-las renova o índice de velocidade do Windows.",
    "Cache do Windows Update": "Instaladores de atualizações do Windows que já foram instaladas no sistema.",
    "DirectX Shader Cache": "Caches gráficos antigos. A limpeza corrige engasgos visuais em jogos e softwares 3D.",
    "NVIDIA DXCache (Shaders de GPU)": "Shaders compilados antigos da placa de vídeo. Os jogos ativos recriam apenas o necessário.",
    "Relatórios de Falha (Crash Dumps)": "Gravações pesadas de memória de erros passados sem utilidade para o usuário.",
    "Adobe Media Cache Files": "Arquivos pesados de pré-renderização (.cfa/.pek). Seus projetos salvos do Premiere não são afetados.",
    "Adobe Media Cache Database": "Bancos de cache antigos da Adobe que acumulam gigabytes após finalizar edições de vídeo.",
    "Cache de Miniaturas (Explorer)": "Miniaturas antigas de imagens e vídeos que já foram movidos ou apagados.",
}


def validate_ai_response(data) -> dict | None:
    """
    Valida a resposta do LLM contra o schema esperado. Retorna None se inválida,
    impedindo que respostas malformadas ou manipuladas influenciem a limpeza.
    """
    if not isinstance(data, dict):
        return None
    decision = data.get("decision")
    explanation = data.get("explanation")
    if decision not in VALID_DECISIONS:
        return None
    if not isinstance(explanation, str) or not explanation.strip():
        return None
    return {
        "decision": decision,
        "explanation": explanation.strip()[:MAX_EXPLANATION_LEN],
    }


class AIEngine:
    """
    Motor de IA Híbrido: Utiliza Ollama localmente se estiver ativo para auditar e explicar,
    ou aciona o Fallback Heurístico Nativo para execução instantânea em máquinas de leigos.

    Segurança: o LLM recebe apenas METADADOS (categoria, caminho, risco, contagem, tamanho e
    extensões), nunca o conteúdo dos arquivos, evitando prompt injection.
    """
    def __init__(self, model_name: str = "qwen2.5:1.5b"):
        self.model_name = model_name
        self.ollama_available = self._check_ollama()
        self._cache: dict[tuple[str, str], dict] = {}
        self._lock = threading.Lock()

    def _check_ollama(self) -> bool:
        try:
            req = urllib.request.Request("http://127.0.0.1:11434/api/tags")
            with urllib.request.urlopen(req, timeout=1.2) as response:
                return response.status == 200
        except Exception as exc:
            logger.info("Ollama indisponível: %s", exc)
            return False

    def _heuristic(self, category: str, risk: str = "SAFE") -> dict:
        explanation = HEURISTIC_EXPLANATIONS.get(
            category, "Resíduos temporários validados pelas regras de segurança do sistema."
        )
        if risk == "REVIEW":
            explanation += " (Categoria de revisão: enviada para quarentena de 7 dias antes da exclusão definitiva.)"
        return {
            "decision": "SAFE",
            "explanation": explanation,
            "engine": "Heurística Nativa (Ultra-Leve)",
        }

    def _ask_ollama(
        self, category: str, path: str, stats: dict, risk: str = "SAFE"
    ) -> dict | None:
        import ollama
        extensions = ", ".join(stats.get("extensions", [])) or "n/d"
        prompt = (
            "Você é um especialista em Windows. Explique em 1 frase curta e clara para um usuário leigo "
            f"se é seguro limpar a categoria '{category}' (nível de risco: {risk}) localizada em '{path}'. "
            f"Metadados: {stats.get('file_count', 0)} arquivos, {stats.get('size_mb', 0)} MB, "
            f"extensões mais comuns: {extensions}. "
            "Responda estritamente em JSON com as chaves: 'decision' ('SAFE' ou 'SKIP') e 'explanation'."
        )
        client = ollama.Client(timeout=15)
        response = client.chat(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            format="json",
        )
        data = json.loads(response["message"]["content"])
        return validate_ai_response(data)

    def evaluate_category(
        self,
        category: str,
        path: str,
        sample_file: str = "",
        risk: str = "SAFE",
        stats: dict | None = None,
    ) -> dict:
        cache_key = (category, risk)
        with self._lock:
            if cache_key in self._cache:
                return self._cache[cache_key]

        result = None
        if self.ollama_available:
            try:
                validated = self._ask_ollama(category, path, stats or {}, risk=risk)
                if validated:
                    result = {**validated, "engine": f"Ollama ({self.model_name})"}
                else:
                    logger.warning("Resposta do Ollama inválida para '%s'; usando heurística.", category)
            except Exception as exc:
                logger.warning("Falha ao consultar Ollama para '%s': %s", category, exc)

        if result is None:
            result = self._heuristic(category, risk=risk)

        with self._lock:
            self._cache[cache_key] = result
        return result
