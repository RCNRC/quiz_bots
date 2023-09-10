import logging
import random
import sys
from dotenv import dotenv_values
import redis
from vk_api import VkApi
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor

from tools.logger import LogsHandler
from tools.quiz import get_random_question_answer


LOGGER = logging.getLogger('Vk QUIZ bot logger')
REDIS = redis.Redis(
    host=dotenv_values()['REDIS_HOST'],
    port=dotenv_values()['REDIS_PORT'],
    password=dotenv_values()['REDIS_PASSWORD'],
    decode_responses=True
)
DEFAULT_KEYBOARD = VkKeyboard(one_time=True)

DEFAULT_KEYBOARD.add_button('Новый вопрос', color=VkKeyboardColor.PRIMARY)
DEFAULT_KEYBOARD.add_button('Сдаться', color=VkKeyboardColor.NEGATIVE)
DEFAULT_KEYBOARD.add_line()
DEFAULT_KEYBOARD.add_button('Мой счёт', color=VkKeyboardColor.SECONDARY)


def handle_new_question_request(event, vk_api):
    question, answer = get_random_question_answer('quiz-questions')
    REDIS.rpush(event.user_id, answer)
    vk_api.messages.send(
        user_id=event.user_id,
        message=question,  # event.text
        random_id=random.randint(1, 1000),
        keyboard=DEFAULT_KEYBOARD.get_keyboard(),
    )


def handle_solution_attempt(event, vk_api):
    users_data_length = REDIS.llen(event.user_id)
    original_answer = REDIS.lrange(event.user_id, 0, 0)[0]
    answer = original_answer
    if ' (' in answer and ')' in answer:
        answer = answer.split(' (')[0] + answer.split(' (')[1].split(')')[1]
    if '.' in answer:
        answer = answer.split('.')[0]
    else:
        answer = answer.split('\n')[0]
    if answer == event.text:
        REDIS.delete(event.user_id)
        vk_api.messages.send(
            user_id=event.user_id,
            message='Правильно! Поздравляю! Для следующего вопроса нажми «Новый вопрос»',
            random_id=random.randint(1, 1000),
            keyboard=DEFAULT_KEYBOARD.get_keyboard(),
        )
    elif users_data_length == 1:
        REDIS.rpush(event.user_id, 1)
        vk_api.messages.send(
            user_id=event.user_id,
            message='Неправильно… Попробуешь ещё раз?',
            random_id=random.randint(1, 1000),
            keyboard=DEFAULT_KEYBOARD.get_keyboard(),
        )
    elif users_data_length >= 2:
        REDIS.delete(event.user_id)
        vk_api.messages.send(
            user_id=event.user_id,
            message=f'Неправильно, правильный ответ:\n{original_answer}',
            random_id=random.randint(1, 1000),
            keyboard=DEFAULT_KEYBOARD.get_keyboard(),
        )


def cancel_question(event, vk_api):
    if REDIS.exists(event.user_id):
        answer = REDIS.lrange(event.user_id, 0, 0)[0]
        text = f'Правильный ответ:\n{answer}'
        REDIS.delete(event.user_id)
    else:
        text = 'Нечего отменять'
    vk_api.messages.send(
        user_id=event.user_id,
        message=text,
        random_id=random.randint(1, 1000),
        keyboard=DEFAULT_KEYBOARD.get_keyboard(),
    )
    return handle_new_question_request(event, vk_api)


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

    while True:
        try:
            vk_session = VkApi(token=dotenv_values()['VK_BOT_API_TOKEN'])
            vk_api = vk_session.get_api()
            longpoll = VkLongPoll(vk_session)
            for event in longpoll.listen():
                if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                    if event.text == "Сдаться":
                        cancel_question(event, vk_api)
                    elif REDIS.exists(event.user_id):
                        handle_solution_attempt(event, vk_api)
                    elif event.text == "Новый вопрос":
                        handle_new_question_request(event, vk_api)
        except KeyboardInterrupt:
            LOGGER.info('Bot ended work.')
            sys.exit(0)
        except Exception as exception:
            LOGGER.exception(exception)


if __name__ == '__main__':
    main()