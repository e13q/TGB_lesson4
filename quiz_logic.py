import random
import json
import re


QUESTIONS_COUNT = 5


def load_from_json(filename):
    with open(filename, 'r', encoding='utf-8') as json_file:
        data = json.load(json_file)
    return data


def create_quiz(user_key, redis_db, all_questions):
    questions = redis_db.get('questions')
    questions = random.sample(all_questions, QUESTIONS_COUNT)
    question = questions.pop(0)
    redis_db.hset(user_key, mapping={
        "score": 0,
        "questions": json.dumps(questions),
        "question": question['question'],
        "answer": question['answer']
    })


def get_question_info(user_key, redis_db):
    answer = redis_db.hget(user_key, "answer")
    question = redis_db.hget(user_key, "question")
    questions = json.loads(redis_db.hget(user_key, "questions"))
    question_num = QUESTIONS_COUNT - len(questions)
    return question, answer, question_num


def get_score(user_key, redis_db):
    score = redis_db.hget(user_key, "score")
    return score


def get_next_question(user_key, redis_db):
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


def is_correct_answer(user_key, answer, redis_db):
    user_answer = clean_and_toggle_answer(answer)
    correct_answer = clean_and_toggle_answer(redis_db.hget(user_key, "answer"))
    return user_answer == correct_answer


def get_correct_answer(user_key, redis_db):
    return redis_db.hget(user_key, "answer")


def try_update_question(user_key, redis_db):
    question = get_next_question(user_key, redis_db)
    if question:
        redis_db.hset(user_key, "answer", question['answer'])
        redis_db.hset(user_key, "question", question['question'])
        return True
    else:
        return False


def get_state(user_key, redis_db):
    return redis_db.hget(user_key, "state")


def set_state(user_key, state, redis_db):
    redis_db.hset(user_key, "state", state)


def add_points(user_key, redis_db):
    score = int(redis_db.hget(user_key, "score"))
    score += 1
    redis_db.hset(user_key, "score", score)
