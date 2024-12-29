import logging
import json
import random
import re

from environs import Env
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler
)
import redis

from bot_logging import setup_logger, exception_out

redis_db = None
all_questions = None
QUESTIONS_COUNT = 3


def load_from_json(filename):
    with open(filename, 'r', encoding='utf-8') as json_file:
        data = json.load(json_file)
    return data


# Функция для начала разговора
def start(update: Update, context):
    questions = redis_db.get('questions')
    user_key = f"user:{update.effective_user.id}"
    questions = random.sample(all_questions, QUESTIONS_COUNT)
    question = questions.pop(0)
    redis_db.hset(user_key, mapping={
        "score": 0,
        "questions": json.dumps(questions),
        "question": question['question'],
        "answer": question['answer']
    })
    reply_keyboard = [['Вопрос', 'Сдаться', 'Узнать счёт']]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=False)
    update.message.reply_text(
        'Нажми на кнопку "Вопрос", чтобы начать.',
        reply_markup=markup
    )
    return "START"


def get_next_question(user_key):
    questions = json.loads(redis_db.hget(user_key, "questions"))
    if questions:
        question = questions.pop(0)
        redis_db.hset(user_key, 'questions', json.dumps(questions))
        return question
    else:
        return None


def ask_question(update: Update, context):
    user_key = f"user:{update.effective_user.id}"
    answer = redis_db.hget(user_key, "answer") # удали
    question = redis_db.hget(user_key, "question")
    questions = json.loads(redis_db.hget(user_key, "questions"))
    question_num = QUESTIONS_COUNT - len(questions)
    update.message.reply_text(
        f'Вопрос №{question_num}:\n{question}\n\n<tg-spoiler>{answer}</tg-spoiler>', parse_mode = 'HTML'
    )
    return "ANSWER"


def show_score(update: Update, context):
    user_key = f"user:{update.effective_user.id}"
    score = redis_db.hget(user_key, "score")
    update.message.reply_text(f'Ваш счёт: {score}')
    return "START"


def clean_and_toggle_answer(input_string):
    ''' Нормализации ответа (регистр, спецсимволы) '''
    cleaned_string = re.sub(r'[^a-zA-Zа-яА-Я]', '', input_string)
    toggled_string = ''.join([char.upper() if char.islower() else char.upper() for char in cleaned_string])

    return toggled_string


def check_answer(update: Update, context):
    user_key = f"user:{update.effective_user.id}"
    user_answer = clean_and_toggle_answer(update.message.text)
    correct_answer = clean_and_toggle_answer(redis_db.hget(user_key, "answer"))
    if user_answer == correct_answer:
        update.message.reply_text('Правильно!')
        score = int(redis_db.hget(user_key, "score"))
        score += 1
        redis_db.hset(user_key, "score", score)
        give_up(update, context)
        return "START"
    else:
        update.message.reply_text('Неправильно. Попробуйте еще раз или нажмите "Сдаться".')
        return "ANSWER"


def give_up(update: Update, context):
    user_key = f"user:{update.effective_user.id}"
    correct_answer = redis_db.hget(user_key, "answer")
    update.message.reply_text(f'Правильный ответ: {correct_answer}')
    question = get_next_question(user_key)
    if question:
        redis_db.hset(user_key, "answer", question['answer'])
        redis_db.hset(user_key, "question", question['question'])
    else:
        score = redis_db.hget(user_key, "score")
        update.message.reply_text(
            f"Все вопросы закончились!\nВаш итоговый счёт составил: {score}\nНачинаем новую игру!"
        )
        start(update, context)
    return "START"


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
    all_questions = load_from_json('QA.json')
    main_bot_token = env.str('TELEGRAM_MAIN_BOT_TOKEN')
    setup_logger(
        env.str('TELEGRAM_LOGGER_BOT_TOKEN_TG'),
        env.str('TELEGRAM_CHAT_ID'))
    while (True):
        try:
            updater = Updater(main_bot_token)
            dispatcher = updater.dispatcher
            conv_handler = ConversationHandler(
                entry_points=[CommandHandler('start', start)],
                states={
                    "START": [
                        MessageHandler(
                            Filters.regex('^Вопрос$'), ask_question
                        ),
                        MessageHandler(
                            Filters.regex('^Узнать счёт$'), show_score
                        )
                    ],
                    "ANSWER": [
                        MessageHandler(
                            Filters.regex('^Сдаться$'), give_up
                        ),
                        MessageHandler(
                            Filters.text & ~Filters.command, check_answer
                        )
                    ]
                },
                fallbacks=[CommandHandler('start', start)]
            )

            dispatcher.add_handler(conv_handler)
            logging.info('Бот Telegram успешно запущен!')
            updater.start_polling()
            updater.idle()
        except Exception as e:
            exception_out(
                'Шеф, у нас неожиданная ошибка: ', e
            )
