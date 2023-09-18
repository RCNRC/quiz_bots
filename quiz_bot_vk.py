import logging
import random
import sys
from dotenv import dotenv_values
from redis import Redis
from vk_api import VkApi
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor

from tools.logger import LogsHandler
from tools.quiz import QuizQuestionsCash


LOGGER = logging.getLogger('Vk QUIZ bot logger')
DEFAULT_KEYBOARD = VkKeyboard(one_time=True)

DEFAULT_KEYBOARD.add_button('Новый вопрос', color=VkKeyboardColor.PRIMARY)
DEFAULT_KEYBOARD.add_button('Сдаться', color=VkKeyboardColor.NEGATIVE)
DEFAULT_KEYBOARD.add_line()
DEFAULT_KEYBOARD.add_button('Мой счёт', color=VkKeyboardColor.SECONDARY)


def handle_new_question_request(event, vk_api, bot_data: dict):
    qqc = bot_data['qqc']
    redis = bot_data['redis']
    question, answer = qqc.get_random_question_anwer()
    redis.rpush(event.user_id, answer)
    vk_api.messages.send(
        user_id=event.user_id,
        message=question,
        random_id=random.randint(1, 1000),
        keyboard=DEFAULT_KEYBOARD.get_keyboard(),
    )


def handle_solution_attempt(event, vk_api, bot_data: dict):
    redis = bot_data['redis']
    users_data_length = redis.llen(event.user_id)
    full_answer = redis.lrange(event.user_id, 0, 0)[0]
    target_answer = full_answer
    if ' (' in target_answer and ')' in target_answer:
        target_answer = target_answer.split(' (')[0]\
            + target_answer.split(' (')[1].split(')')[1]
    if '.' in target_answer:
        target_answer = target_answer.split('.')[0]
    else:
        target_answer = target_answer.split('\n')[0]
    if target_answer == event.text:
        redis.delete(event.user_id)
        vk_api.messages.send(
            user_id=event.user_id,
            message='Правильно! Поздравляю! ' +
                    'Для следующего вопроса нажми «Новый вопрос»',
            random_id=random.randint(1, 1000),
            keyboard=DEFAULT_KEYBOARD.get_keyboard(),
        )
    elif users_data_length == 1:
        redis.rpush(event.user_id, 1)
        vk_api.messages.send(
            user_id=event.user_id,
            message='Неправильно… Попробуешь ещё раз?',
            random_id=random.randint(1, 1000),
            keyboard=DEFAULT_KEYBOARD.get_keyboard(),
        )
    elif users_data_length >= 2:
        redis.delete(event.user_id)
        vk_api.messages.send(
            user_id=event.user_id,
            message=f'Неправильно, правильный ответ:\n{full_answer}',
            random_id=random.randint(1, 1000),
            keyboard=DEFAULT_KEYBOARD.get_keyboard(),
        )


def cancel_question(event, vk_api, bot_data: dict):
    redis = bot_data['redis']
    if redis.exists(event.user_id):
        answer = redis.lrange(event.user_id, 0, 0)[0]
        text = f'Правильный ответ:\n{answer}'
        redis.delete(event.user_id)
    else:
        text = 'Нечего отменять'
    vk_api.messages.send(
        user_id=event.user_id,
        message=text,
        random_id=random.randint(1, 1000),
        keyboard=DEFAULT_KEYBOARD.get_keyboard(),
    )
    return handle_new_question_request(event, vk_api, bot_data)


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

    qqc = QuizQuestionsCash(dotenv_values()['DEFAULT_QUIZ_FOLDER'])
    qqc.store_new_questions()

    redis = Redis(
        host=dotenv_values()['REDIS_HOST'],
        port=dotenv_values()['REDIS_PORT'],
        password=dotenv_values()['REDIS_PASSWORD'],
        decode_responses=True
    )

    bot_data = {
        'redis': redis,
        'qqc': qqc,
    }

    while True:
        try:
            vk_session = VkApi(token=dotenv_values()['VK_BOT_API_TOKEN'])
            vk_api = vk_session.get_api()
            longpoll = VkLongPoll(vk_session)
            for event in longpoll.listen():
                if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                    if event.text == "Сдаться":
                        cancel_question(event, vk_api, bot_data)
                    elif redis.exists(event.user_id):
                        handle_solution_attempt(event, vk_api, bot_data)
                    elif event.text == "Новый вопрос":
                        handle_new_question_request(event, vk_api, bot_data)
        except KeyboardInterrupt:
            LOGGER.info('Bot ended work.')
            sys.exit(0)
        except Exception as exception:
            LOGGER.exception(exception)


if __name__ == '__main__':
    main()
