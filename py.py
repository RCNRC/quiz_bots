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
import redis
from tools.logger import LogsHandler
from tools.quiz import get_random_question_answer


LOGGER = logging.getLogger('Telegram QUIZ bot logger')
DEFAULT_KEYBOARD = [['Новый вопрос', 'Сдаться'],
                   ['Мой счёт']]
DEFAULT_MARKUP = telegram.ReplyKeyboardMarkup(DEFAULT_KEYBOARD)
REDIS = redis.Redis(
    host=dotenv_values()['REDIS_HOST'],
    port=dotenv_values()['REDIS_PORT'],
    password=dotenv_values()['REDIS_PASSWORD'],
    decode_responses=True
)


def start(update: Update, context: CallbackContext):
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text='Здравствуйте',
        reply_markup=DEFAULT_MARKUP,
    )


def quiz_next(update: Update, context: CallbackContext):
    if not REDIS.ping():
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='Ошибка на сервере, повторите попытку позже.',
            reply_markup=DEFAULT_MARKUP,
        )
        raise redis.ConnectionError
    else:
        is_user = REDIS.exists(update.effective_chat.id)
        if is_user:
            users_data_length = REDIS.llen(update.effective_chat.id)
            original_answer = REDIS.lrange(update.effective_chat.id, 0, 0)[0]
            answer = original_answer
            if ' (' in answer and ')' in answer:
                answer = answer.split(' (')[0] + answer.split(' (')[1].split(')')[1]
            if '.' in answer:
                answer = answer.split('.')[0]
            else:
                answer = answer.split('\n')[0]
            if answer == update.message.text:
                REDIS.delete(update.effective_chat.id)
                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text='Правильно! Поздравляю! Для следующего вопроса нажми «Новый вопрос»',
                    reply_markup=DEFAULT_MARKUP,
                )
            elif users_data_length == 1:
                REDIS.rpush(update.effective_chat.id, 1)
                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text='Неправильно… Попробуешь ещё раз?',
                    reply_markup=DEFAULT_MARKUP,
                )
            elif users_data_length == 2:
                REDIS.delete(update.effective_chat.id)
                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f'Неправильно, правильный ответ:\n{original_answer}',
                    reply_markup=DEFAULT_MARKUP,
                )
        else:
            if update.message.text == 'Новый вопрос':
                question, answer = get_random_question_answer('quiz-questions')
                print(answer)
                REDIS.rpush(update.effective_chat.id, answer)
                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=question,
                    reply_markup=DEFAULT_MARKUP,
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
        MessageHandler(Filters.text & (~Filters.command), quiz_next)
    )
    dispatcher.add_error_handler(error_handler)
    updater.start_polling()


if __name__ == '__main__':
    main()
