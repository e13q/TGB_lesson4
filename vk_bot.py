import random
import logging
import json

import vk_api as vk
from vk_api.longpoll import VkLongPoll, VkEventType
import redis
from environs import Env

from bot_logging import setup_logger, exception_out
from quiz_logic import (
    create_quiz,
    get_question_info,
    get_score,
    is_correct_answer,
    add_points,
    get_correct_answer,
    try_update_question,
    set_state,
    get_state
)
from quiz_logic import load_from_json


HASH_START = "user_vk"


def start(event, vk_api, redis_db):
    all_questions = load_from_json('QA.json')
    user_key = f"{HASH_START}:{event.user_id}"
    create_quiz(user_key, redis_db, all_questions)
    keyboard = {
        "one_time": False,
        "buttons": [
            [{"action": {"type": "text", "label": "Вопрос"}, "color": "primary"}], # noqa
            [{"action": {"type": "text", "label": "Сдаться"}, "color": "negative"}], # noqa
            [{"action": {"type": "text", "label": "Узнать счёт"}, "color": "positive"}] # noqa
        ]
    }
    set_state(user_key, "START", redis_db)
    vk_api.messages.send(
        user_id=event.user_id,
        message='Нажми на кнопку "Вопрос", чтобы начать.',
        random_id=random.randint(1, 1000),
        keyboard=json.dumps(keyboard)
    )


def ask_question(event, vk_api, redis_db):
    user_key = f"{HASH_START}:{event.user_id}"
    question, answer, question_num = get_question_info(user_key, redis_db)
    text = f"Вопрос №{question_num}:\n{question}"
    vk_api.messages.send(
        user_id=event.user_id,
        message=text,
        random_id=random.randint(1, 1000)
    )
    set_state(user_key, "ANSWER", redis_db)


def show_score(event, vk_api, redis_db):
    user_key = f"{HASH_START}:{event.user_id}"
    score = get_score(user_key, redis_db)
    vk_api.messages.send(
        user_id=event.user_id,
        message=f'Ваш счёт: {score}',
        random_id=random.randint(1, 1000)
    )
    set_state(user_key, "START", redis_db)


def check_answer(event, vk_api, redis_db):
    user_key = f"{HASH_START}:{event.user_id}"
    if is_correct_answer(user_key, event.text, redis_db):
        vk_api.messages.send(
            user_id=event.user_id,
            message='Правильно!',
            random_id=random.randint(1, 1000)
        )
        add_points(user_key, redis_db)
        give_up(event, vk_api, redis_db)
        set_state(user_key, "START", redis_db)
    else:
        vk_api.messages.send(
            user_id=event.user_id,
            message='Неправильно. Попробуйте еще раз или нажмите "Сдаться".',
            random_id=random.randint(1, 1000)
        )
        set_state(user_key, "ANSWER", redis_db)


def give_up(event, vk_api, redis_db):
    user_key = f"{HASH_START}:{event.user_id}"
    correct_answer = get_correct_answer(user_key, redis_db)
    vk_api.messages.send(
            user_id=event.user_id,
            message=f'Правильный ответ: {correct_answer}',
            random_id=random.randint(1, 1000)
        )
    if not try_update_question(user_key, redis_db):
        score = get_score(user_key, redis_db)
        vk_api.messages.send(
            user_id=event.user_id,
            message=f"Все вопросы закончились!\nВаш итоговый счёт составил: {score}\nНачинаем новую игру!", # noqa
            random_id=random.randint(1, 1000)
        )
        start(event, vk_api, redis_db)
    set_state(user_key, "START", redis_db)


if __name__ == "__main__":
    env = Env()
    env.read_env()
    redis_db = redis.Redis(
            host=env.str('REDIS_CLOUD_HOST'),
            port=env.int('REDIS_CLOUD_PORT'),
            decode_responses=True,
            username=env.str('REDIS_CLOUD_USERNAME'),
            password=env.str('REDIS_CLOUD_PASSWORD'),
        )
    vk_session = vk.VkApi(token=env.str('VK_GROUP_TOKEN'))
    setup_logger(
        env.str('TELEGRAM_LOGGER_BOT_TOKEN_VK'),
        env.str('TELEGRAM_CHAT_ID')
    )
    try:
        while (True):
            vk_api = vk_session.get_api()
            longpoll = VkLongPoll(vk_session)
            logging.info('Бот для группы VK успешно запущен!')
            for event in longpoll.listen():
                if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                    user_state = get_state(
                        f"{HASH_START}:{event.user_id}", redis_db
                    )
                    if user_state is None:
                        user_state = start(
                            event, vk_api, redis_db
                        )
                    elif user_state == "START":
                        if event.text.lower() == 'вопрос':
                            user_state = ask_question(event, vk_api, redis_db)
                        elif event.text.lower() == 'узнать счёт':
                            user_state = show_score(event, vk_api, redis_db)
                    elif user_state == "ANSWER":
                        if event.text.lower() == 'сдаться':
                            user_state = give_up(event, vk_api, redis_db)
                        else:
                            user_state = check_answer(event, vk_api, redis_db)
    except Exception as e:
        exception_out(
            'Шеф, у нас неожиданная ошибка: ', e
        )
