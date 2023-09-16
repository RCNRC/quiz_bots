import logging
from enum import Enum
import traceback
from dotenv import dotenv_values
from telegram import Update
import telegram
from telegram.ext import (
    Updater,
    CallbackContext,
    MessageHandler,
    Filters,
    ConversationHandler,
)
import redis
from tools.logger import LogsHandler
from tools.quiz import QuizQuestionsCash


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

QQC = QuizQuestionsCash('./quiz-questions')


class States(Enum):
    QUESTION = 0
    ANSWER = 1


def start(update: Update, context: CallbackContext):
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text='Здравствуйте',
        reply_markup=DEFAULT_MARKUP,
    )


def handle_new_question_request(update, _):
    question, answer = QQC.get_random_question_anwer()
    REDIS.rpush(update.effective_chat.id, answer)
    update.message.reply_text(
        text=question,
        reply_markup=DEFAULT_MARKUP,
    )
    return States.ANSWER


def handle_solution_attempt(update, _):
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
        update.message.reply_text(
            text='Правильно! Поздравляю!' +
                 ' Для следующего вопроса нажми «Новый вопрос»',
            reply_markup=DEFAULT_MARKUP,
        )
        return ConversationHandler.END
    elif users_data_length == 1:
        REDIS.rpush(update.effective_chat.id, 1)
        update.message.reply_text(
            text='Неправильно… Попробуешь ещё раз?',
            reply_markup=DEFAULT_MARKUP,
        )
        return States.ANSWER
    elif users_data_length >= 2:
        REDIS.delete(update.effective_chat.id)
        update.message.reply_text(
            text=f'Неправильно, правильный ответ:\n{original_answer}',
            reply_markup=DEFAULT_MARKUP,
        )
        return ConversationHandler.END


def cancel_question(update, _):
    if REDIS.exists(update.effective_chat.id):
        answer = REDIS.lrange(update.effective_chat.id, 0, 0)[0]
        text = f'Правильный ответ:\n{answer}'
        REDIS.delete(update.effective_chat.id)
    else:
        text = 'Нечего отменять'
    update.message.reply_text(
        text=text,
        reply_markup=DEFAULT_MARKUP,
    )
    return handle_new_question_request(update, _)


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

    QQC.store_new_questions()

    bot_telegramm_api_token = dotenv_values()['TELEGRAM_BOT_API_TOKEN']
    bot = telegram.Bot(token=bot_telegramm_api_token)
    updater = Updater(bot=bot)
    dispatcher = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(
                Filters.regex('^(Новый вопрос)$'),
                handle_new_question_request
            ),
        ],

        states={
            States.ANSWER: [
                MessageHandler(
                    Filters.regex('^(Сдаться)$'),
                    cancel_question
                ),
                MessageHandler(
                    Filters.text,
                    handle_solution_attempt,
                ),
            ],
        },

        fallbacks=[]
    )

    dispatcher.add_handler(conv_handler)

    dispatcher.add_error_handler(error_handler)
    updater.start_polling()


if __name__ == '__main__':
    main()
