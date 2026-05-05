import logging
import sys


def configure_logging(level: str = "INFO") -> None:
    """Configure logging for the FastRAG application.

    Called in the lifespan startup after uvicorn has initialized its own
    logging config (which may set disable_existing_loggers=True). We
    explicitly re-enable and configure our backend.rag logger here.
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)-5s %(name)s %(message)s",
        datefmt="%H:%M:%S",
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    # Configure the backend.rag logger explicitly — this survives
    # uvicorn's DictConfig because we set it up AFTER uvicorn init.
    rag_logger = logging.getLogger("backend.rag")
    rag_logger.setLevel(numeric_level)
    # Clear any handlers uvicorn may have injected, use our own
    rag_logger.handlers.clear()
    rag_logger.addHandler(handler)
    # Do not propagate to root to avoid duplicate lines
    rag_logger.propagate = False
    # Ensure the logger is not disabled by disable_existing_loggers
    rag_logger.disabled = False

    # Also ensure the root logger can show our logs as a fallback
    root = logging.getLogger()
    root.setLevel(min(numeric_level, logging.WARNING))
