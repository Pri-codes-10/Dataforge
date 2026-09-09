import logging


def setup_logger() -> logging.Logger:
    """
    Configure the application logger.
    """

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    return logging.getLogger("voice-agent")


logger = setup_logger()