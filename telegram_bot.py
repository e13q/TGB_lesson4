import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler
)
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
    try_update_question
)
from quiz_logic import load_from_json

HASH_START = "user_tg"


def start(update: Update, context):
    redis_db = context.bot_data['redis_db']
    user_key = f"{HASH_START}:{update.effective_user.id}"
    all_questions = load_from_json('QA.json')
    create_quiz(user_key, redis_db, all_questions)
    reply_keyboard = [['Вопрос', 'Сдаться', 'Узнать счёт']]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=False)
    update.message.reply_text(
        'Нажми на кнопку "Вопрос", чтобы начать.',
        reply_markup=markup
    )
    return "START"


def ask_question(update: Update, context):
    redis_db = context.bot_data['redis_db']
    user_key = f"{HASH_START}:{update.effective_user.id}"
    question, answer, question_num = get_question_info(user_key, redis_db)
    update.message.reply_text(
        f'Вопрос №{question_num}:\n{question}\n\n<tg-spoiler>{answer}</tg-spoiler>', parse_mode = 'HTML' # noqa
    )
    return "ANSWER"


def show_score(update: Update, context):
    redis_db = context.bot_data['redis_db']
    user_key = f"{HASH_START}:{update.effective_user.id}"
    score = get_score(user_key, redis_db)
    update.message.reply_text(f'Ваш счёт: {score}')
    return "START"


def check_answer(update: Update, context):
    redis_db = context.bot_data['redis_db']
    user_key = f"{HASH_START}:{update.effective_user.id}"
    if is_correct_answer(user_key, update.message.text, redis_db):
        update.message.reply_text('Правильно!')
        add_points(user_key, redis_db)
        give_up(update, context)
        return "START"
    else:
        update.message.reply_text('Неправильно. Попробуйте еще раз или нажмите "Сдаться".') # noqa
        return "ANSWER"


def give_up(update: Update, context):
    redis_db = context.bot_data['redis_db']
    user_key = f"{HASH_START}:{update.effective_user.id}"
    correct_answer = get_correct_answer(user_key, redis_db)
    update.message.reply_text(f'Правильный ответ: {correct_answer}')
    if not try_update_question(user_key, redis_db):
        score = get_score(user_key, redis_db)
        update.message.reply_text(
            f"Все вопросы закончились!\nВаш итоговый счёт составил: {score}\nНачинаем новую игру!" # noqa
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
    main_bot_token = env.str('TELEGRAM_MAIN_BOT_TOKEN')
    setup_logger(
        env.str('TELEGRAM_LOGGER_BOT_TOKEN_TG'),
        env.str('TELEGRAM_CHAT_ID'))
    while (True):
        try:
            updater = Updater(main_bot_token, use_context=True)
            dispatcher = updater.dispatcher
            dispatcher.bot_data['redis_db'] = redis_db
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
