import logging
from colorama import Fore, Style
import datetime


class ColoredFormatter(logging.Formatter):
    COLOR_CODES = {
        logging.DEBUG: Fore.CYAN,
        logging.INFO: Fore.GREEN,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Fore.MAGENTA,
    }

    def format(self, record):
        level_color = self.COLOR_CODES.get(record.levelno, '')
        time = datetime.datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        reset = Style.RESET_ALL
        if record.levelno == logging.DEBUG:
            level_icon = f'[{Style.BRIGHT}{Fore.CYAN}^{reset}]'
            level_name = 'DEBUG'
            highlight_color = f'{Style.BRIGHT}{Fore.CYAN}'
        elif record.levelno == logging.INFO:
            level_icon = f'[{Style.BRIGHT}{Fore.GREEN}+{reset}]'
            level_name = 'INFO'
            highlight_color = f'{Style.BRIGHT}{Fore.GREEN}'
        elif record.levelno == logging.WARNING:
            level_icon = f'[{Style.BRIGHT}{Fore.YELLOW}!{reset}]'
            level_name = 'WARNING'
            highlight_color = f'{Style.BRIGHT}{Fore.YELLOW}'
        elif record.levelno == logging.ERROR:
            level_icon = f'[{Style.BRIGHT}{Fore.RED}#{reset}]'
            level_name = 'ERROR'
            highlight_color = f'{Style.BRIGHT}{Fore.RED}'
        elif record.levelno == logging.CRITICAL:
            level_icon = f'[{Style.BRIGHT}{Fore.MAGENTA}*{reset}]'
            level_name = 'CRITICAL'
            highlight_color = f'{Style.BRIGHT}{Fore.MAGENTA}'
        else:
            level_icon = ''
            level_name = ''
            highlight_color = ''
        message = super().format(record)
        for word in message.split():
            if word.startswith('<<') and word.endswith('>>'):
                message = message.replace(word, f'{highlight_color}{word[2:-2]}{reset}')
        return f'{time} {level_color}{level_name}:{reset} {level_icon} {message.replace(level_name + ": ", "")}'


class CustomLogger:
    _loggers = {}

    def __new__(cls, log_level, logger_name, log_path):
        if logger_name not in cls._loggers:
            new_logger = super(CustomLogger, cls).__new__(cls)
            cls._loggers[logger_name] = new_logger
            return new_logger
        else:
            return cls._loggers[logger_name]

    def __init__(self, log_level, logger_name, log_path):
        if hasattr(self, 'is_initialized'):
            # Logger already initialized, just update the log level
            self.set_log_level(log_level)
            return

        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(
            {1: logging.DEBUG, 2: logging.INFO, 3: logging.WARNING, 4: logging.ERROR, 5: logging.CRITICAL}.get(
                log_level, logging.INFO))

        console_handler = logging.StreamHandler()
        file_handler = logging.FileHandler(log_path)

        formatter = ColoredFormatter('%(message)s')
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))

        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)

        self.is_initialized = True

    def set_log_level(self, log_level):
        level = {1: logging.DEBUG, 2: logging.INFO, 3: logging.WARNING, 4: logging.ERROR, 5: logging.CRITICAL}.get(
            log_level, logging.INFO)
        self.logger.setLevel(level)
        for handler in self.logger.handlers:
            handler.setLevel(level)
