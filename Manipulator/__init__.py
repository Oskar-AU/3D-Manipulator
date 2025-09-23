from .Driver_Interface import IO
import logging

def setup_logging(level: int = logging.DEBUG):
    """
    Optional helper to configure logging. Application can call this but is not automatic.

    Parameters
    ----------
    level : Literal str, optional
        The level of logging. Recommended to use e.g. logging.DEBUG (default is logging.DEBUG).
    """
    # Handler for logging in external file.
    file_handler = logging.FileHandler('log.log')
    file_handler.setLevel(logging.DEBUG)

    # Handler for terminal logging.
    terminal_handler = logging.StreamHandler()
    terminal_handler.setLevel(logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[file_handler, terminal_handler]
    )