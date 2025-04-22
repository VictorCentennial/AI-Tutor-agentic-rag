import logging


def setup_logging():
    # Check if root logger already has handlers to avoid duplicate logs
    root_logger = logging.getLogger()
    if root_logger.handlers:
        return root_logger

    # Configure root logger
    logging.basicConfig(
        level=logging.DEBUG,  # Change to INFO to see your messages
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            # logging.FileHandler('app.log'),
        ],
    )

    # Configure specific loggers
    logging.getLogger("pymongo").setLevel(logging.WARNING)
    logging.getLogger("flask").setLevel(logging.DEBUG)

    # Set the level for your own modules to DEBUG or INFO
    logging.getLogger("rag").setLevel(logging.DEBUG)

    # Return logger for convenience
    return logging.getLogger()
