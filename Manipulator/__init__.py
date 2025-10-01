from .Driver_Interface import IO, Motion_Commands
from .Manipulator import Manipulator
from .Stream import Stream
import logging
import os

def setup_logging(level: int = logging.DEBUG, delete_current_log_at_startup: bool = True, file_name: str = "log.log"):
    """
    Optional helper to configure logging. Application can call this but is not automatic.

    Parameters
    ----------
    level : Literal str, optional
        The level of logging. Recommended to use e.g. logging.DEBUG (default is logging.DEBUG).
    """
    # Handler for logging in external file.
    file_handler = logging.FileHandler(file_name)
    file_handler.setLevel(logging.DEBUG)

    # Handler for terminal logging.
    terminal_handler = logging.StreamHandler()
    terminal_handler.setLevel(logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[file_handler, terminal_handler]
    )

    if delete_current_log_at_startup and os.path.exists(file_name):
        try:
            os.remove(file_name)
        except OSError as e:
            logger = logging.getLogger('SETUP')
            logger.warning(f"Logger was unable to remove previous log file '{file_name}': {e.strerror}. Logs are appended to this file instead.")