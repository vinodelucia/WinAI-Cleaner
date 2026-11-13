import logging
import os

LOGGER_NAME = "winai"


def setup_logging(log_dir: str = "reports") -> logging.Logger:
    """
    Configura o log em arquivo (reports/winai.log). Seguro para chamar várias vezes.
    Se não for possível gravar o arquivo, o app continua funcionando sem log em disco.
    """
    logger = logging.getLogger(LOGGER_NAME)
    if any(isinstance(h, logging.FileHandler) for h in logger.handlers):
        return logger
    logger.setLevel(logging.INFO)
    try:
        os.makedirs(log_dir, exist_ok=True)
        handler = logging.FileHandler(
            os.path.join(log_dir, "winai.log"), encoding="utf-8", delay=True
        )
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        )
        logger.addHandler(handler)
    except OSError:
        logger.addHandler(logging.NullHandler())
    return logger
