import random
import json
import re

import redis
from environs import Env

env = Env()
env.read_env()

redis_db = redis.Redis(
        host=env.str('REDIS_CLOUD_HOST'),
        port=env.int('REDIS_CLOUD_PORT'),
        decode_responses=True,
        username=env.str('REDIS_CLOUD_USERNAME'),
        password=env.str('REDIS_CLOUD_PASSWORD'),
    )


def load_from_json(filename):
    with open(filename, 'r', encoding='utf-8') as json_file:
        data = json.load(json_file)
    return data


all_questions = load_from_json('QA.json')

QUESTIONS_COUNT = 3


def create_quiz(user_key):
    questions = redis_db.get('questions')
    questions = random.sample(all_questions, QUESTIONS_COUNT)
    question = questions.pop(0)
    redis_db.hset(user_key, mapping={
        "score": 0,
        "questions": json.dumps(questions),
        "question": question['question'],
        "answer": question['answer']
    })


def get_question_info(user_key):
    answer = redis_db.hget(user_key, "answer")
    question = redis_db.hget(user_key, "question")
    questions = json.loads(redis_db.hget(user_key, "questions"))
    question_num = QUESTIONS_COUNT - len(questions)
    return question, answer, question_num


def get_score(user_key):
    score = redis_db.hget(user_key, "score")
    return score


def get_next_question(user_key):
    questions = json.loads(redis_db.hget(user_key, "questions"))
    if questions:
        question = questions.pop(0)
        redis_db.hset(user_key, 'questions', json.dumps(questions))
        return question
    else:
        return None


def clean_and_toggle_answer(input_string):
    ''' Нормализации ответа (регистр, спецсимволы) '''
    cleaned_string = re.sub(r'[^a-zA-Zа-яА-Я]', '', input_string)
    toggled_string = ''.join(
        [
            char.upper() if char.islower() else char.upper() for char in cleaned_string # noqa
        ]
    )
    return toggled_string


def is_correct_answer(user_key, answer):
    user_answer = clean_and_toggle_answer(answer)
    correct_answer = clean_and_toggle_answer(redis_db.hget(user_key, "answer"))
    return user_answer == correct_answer


def get_correct_answer(user_key):
    return redis_db.hget(user_key, "answer")


def try_update_question(user_key):
    question = get_next_question(user_key)
    if question:
        redis_db.hset(user_key, "answer", question['answer'])
        redis_db.hset(user_key, "question", question['question'])
        return True
    else:
        return False


def add_points(user_key):
    score = int(redis_db.hget(user_key, "score"))
    score += 1
    redis_db.hset(user_key, "score", score)
