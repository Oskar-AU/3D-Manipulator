from .IO import Motion_Commands
from typing import Literal
import logging

def setup_logging(level: int = logging.DEBUG):
    """
    Optional helper to configure logging. Application can call this but is not automatic.

    Parameters
    ----------
    level : Literal str, optional
        The level of logging. Recommended to use e.g. logging.DEBUG (default is logging.DEBUG).
    """
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )