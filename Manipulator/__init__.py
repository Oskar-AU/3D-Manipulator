from .Driver_Interface import IO, Motion_Commands
from .Manipulator import Manipulator
import logging
import os

def setup_logging(terminal_handler_level: int = logging.INFO, delete_current_log_at_startup: bool = True, file_name: str = "log.log"):
    """
    Optional helper to configure logging. Application can call this but is not automatic.

    Parameters
    ----------
    level : Literal str, optional
        The level of logging. Recommended to use e.g. logging.DEBUG (default is logging.DEBUG).
    """
    path = "logs"
    if not os.path.exists(path):
        os.mkdir(path)

    formatter_all = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    formatter_drive = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    file_mode = 'w' if delete_current_log_at_startup else 'a'

    # Handler for logging in external file.
    file_handler = logging.FileHandler(path + '/' + file_name, file_mode)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter_all)

    # Handler for terminal logging.
    terminal_handler = logging.StreamHandler()
    terminal_handler.setLevel(terminal_handler_level)
    terminal_handler.setFormatter(formatter_all)

    # Driver log handlers.
    driver_1_file_handler = logging.FileHandler(path + '/' + "DRIVE_1.log", file_mode)
    driver_1_file_handler.setLevel(logging.DEBUG)
    driver_1_file_handler.setFormatter(formatter_drive)
    driver_2_file_handler = logging.FileHandler(path + '/' + "DRIVE_2.log", file_mode)
    driver_2_file_handler.setLevel(logging.DEBUG)
    driver_2_file_handler.setFormatter(formatter_drive)
    driver_3_file_handler = logging.FileHandler(path + '/' + "DRIVE_3.log", file_mode)
    driver_3_file_handler.setLevel(logging.DEBUG)
    driver_3_file_handler.setFormatter(formatter_drive)

    DRIVE_1_logger = logging.getLogger('DRIVE_1')
    DRIVE_1_logger.setLevel(logging.DEBUG)
    DRIVE_1_logger.addHandler(driver_1_file_handler)
    DRIVE_1_logger.addHandler(file_handler)
    DRIVE_1_logger.addHandler(terminal_handler)
    DRIVE_2_logger = logging.getLogger('DRIVE_2')
    DRIVE_2_logger.setLevel(logging.DEBUG)
    DRIVE_2_logger.addHandler(driver_2_file_handler)
    DRIVE_2_logger.addHandler(file_handler)
    DRIVE_2_logger.addHandler(terminal_handler)
    DRIVE_3_logger = logging.getLogger('DRIVE_3')
    DRIVE_3_logger.setLevel(logging.DEBUG)
    DRIVE_3_logger.addHandler(driver_3_file_handler)
    DRIVE_3_logger.addHandler(file_handler)
    DRIVE_3_logger.addHandler(terminal_handler)

    OS_logger = logging.getLogger('OS')
    OS_logger.setLevel(logging.DEBUG)
    OS_logger.addHandler(terminal_handler)
    OS_logger.addHandler(file_handler)