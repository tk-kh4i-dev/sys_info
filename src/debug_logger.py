# Copyright (c) 2026 tk-kh4i-dev. Licensed under the MIT License.

# The commented out lines are left as an option. 
# By default the debug console is disabled, you can un-comment the lines to enable console mode.
# Caution: Console mode is NOT tested.

import logging
from logging.handlers import RotatingFileHandler
import pathlib
import sys

__version__ = "1.3.1"

def handle_unhandled_exception(exc_type, exc_value, exc_trcebck):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_trcebck)
        return
    
    r_logger = logging.getLogger()

    r_logger.critical(
        "[!] CRITICAL ERROR OCCURED!",
        exc_info=(exc_type, exc_value, exc_trcebck)
    )

def ini_log(level: str = "INFO"):

    LEVELS = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }

    base_lvl = LEVELS.get(str(level).upper(), logging.INFO)

    f_format = logging.Formatter(
        fmt = "[%(asctime)s.%(msecs)03d] [%(levelname)s] [%(name)s:%(lineno)d] [Thrd:%(threadName)s] -> %(message)s",
        datefmt = "%Y-%m-%d %H:%M:%S"
    )

    # c_format = logging.Formatter(
    #     fmt="[%(levelname)s] %(message)s"
    # )
    
    log_dir = pathlib.Path(__file__).parent.parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = str(log_dir / "app_debug.log")

    f_handler = RotatingFileHandler(log_file, maxBytes=80 * 1024 * 1024, backupCount=7)
    f_handler.setLevel(base_lvl)
    f_handler.setFormatter(f_format)

    # c_handler = logging.StreamHandler(sys.stdout)
    # c_handler.setLevel(base_lvl)
    # c_handler.setFormatter(c_format)

    r_logger = logging.getLogger()
    r_logger.setLevel(base_lvl)

    while r_logger.handlers:
        r_logger.removeHandler(r_logger.handlers[0])

    r_logger.addHandler(f_handler)
    # r_logger.addHandler(c_handler)

    sys.excepthook = handle_unhandled_exception
    
    r_logger.log(base_lvl, f"Current level: {str(level).upper()}. Usage: python run.py (cmd/pwsh), if you want to enable debug mode, add the '--debug' flag after the execution command.")

r_logger = logging.getLogger() # Root logger for the entire utility.