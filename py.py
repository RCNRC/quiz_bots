import logging
import traceback
from dotenv import dotenv_values
from telegram import Update
import telegram
from telegram.ext import (
    Updater,
    CallbackContext,
    CommandHandler,
    MessageHandler,
    Filters,
)
from tools.logger import LogsHandler


LOGGER = logging.getLogger('Telegram bot logger')


def get_qustions_answers(file_name: str) -> dict:
    qustions_answers = dict()
    last_added_tour = ''
    last_added_question = ''
    last_added_answer = ''
    next_is_tour = False
    next_is_question = False
    next_is_answer = False
    with open(file_name, 'r', encoding='KOI8-R') as file:
        line = file.readline()
        while line:
            if next_is_tour:
                last_added_tour = line
                qustions_answers[line] = []
                next_is_tour = False
            elif next_is_question:
                if line == '\n':
                    next_is_question = False
                else:
                    last_added_question = last_added_question + line
            elif next_is_answer:
                if line == '\n':
                    next_is_answer = False
                    qustions_answers[last_added_tour].append(
                        (last_added_question, last_added_answer)
                    )
                    last_added_question = ''
                    last_added_answer = ''
                else:
                    last_added_answer = last_added_answer + line
            elif line.startswith('Тур:'):
                next_is_tour = True
            elif line.startswith('Вопрос '):
                next_is_question = True
            elif line.startswith('Ответ:'):
                next_is_answer = True
            line = file.readline()
    return qustions_answers


def start(update: Update, context: CallbackContext):
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text='Здравствуйте'
    )


def echo(update: Update, context: CallbackContext):
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=update.message.text,
    )


def error_handler(_, context):
    tb_list = traceback.format_exception(
        None,
        context.error,
        context.error.__traceback__,
    )
    tb_string = ''.join(tb_list)
    LOGGER.error(tb_string)


def main():
    #import pprint

    # Prints the nicely formatted dictionary
    #pprint.pprint(get_qustions_answers('quiz-questions/1vs1200.txt'))

    LOGGER.setLevel(logging.DEBUG)

    chat_id = dotenv_values()['TELEGRAM_CHAT_ID']
    bot_telegram_logger_api_token = dotenv_values()[
        'TELEGRAM_BOT_LOGGER_API_TOKEN'
    ]
    logger_format = logging.Formatter(
        '%(process)d [%(levelname)s] (%(asctime)s) in %(name)s:\n\n%(message)s'
    )
    handler = LogsHandler(
        bot_telegram_logger_api_token,
        chat_id,
    )
    handler.setFormatter(logger_format)

    LOGGER.addHandler(handler)

    bot_telegramm_api_token = dotenv_values()['TELEGRAM_BOT_API_TOKEN']
    bot = telegram.Bot(token=bot_telegramm_api_token)
    updater = Updater(bot=bot)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(
        MessageHandler(Filters.text & (~Filters.command), echo)
    )
    dispatcher.add_error_handler(error_handler)
    updater.start_polling()


if __name__ == '__main__':
    main()
