import logging
import time

from telegram.ext import Updater


class TelegramLogHandler(logging.Handler):
    def __init__(self, logger_bot, log_chat_id):
        super().__init__()
        self.logger_bot = logger_bot
        self.log_chat_id = log_chat_id

    def emit(self, record):
        self.logger_bot.bot.send_message(
            chat_id=self.log_chat_id,
            text=self.format(record)
        )


def exception_out(text, exception):
    logging.info(f'{text}: {exception}', exc_info=True)
    time.sleep(4)


def setup_logger(token, log_chat_id):
    logger_bot = Updater(token=token)
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    telegram_handler = TelegramLogHandler(logger_bot, log_chat_id)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    telegram_handler.setFormatter(formatter)
    logger.addHandler(telegram_handler)
