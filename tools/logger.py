import logging

import telegram


class LogsHandler(logging.Handler):

    def __init__(
            self,
            tg_bot_logger_token,
            chat_id,
    ):
        super().__init__()
        self.chat_id = chat_id
        self.tg_bot_logger = telegram.Bot(token=tg_bot_logger_token)

    def emit(self, record):
        log_entry = self.format(record)
        self.tg_bot_logger.send_message(chat_id=self.chat_id, text=log_entry)
