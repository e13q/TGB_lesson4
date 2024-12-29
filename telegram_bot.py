import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler
)


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
from quiz_logic import env

HASH_START = "user_tg"


def start(update: Update, context):
    user_key = f"{HASH_START}:{update.effective_user.id}"
    create_quiz(user_key)
    reply_keyboard = [['Вопрос', 'Сдаться', 'Узнать счёт']]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=False)
    update.message.reply_text(
        'Нажми на кнопку "Вопрос", чтобы начать.',
        reply_markup=markup
    )
    return "START"


def ask_question(update: Update, context):
    user_key = f"{HASH_START}:{update.effective_user.id}"
    question, answer, question_num = get_question_info(user_key)
    update.message.reply_text(
        f'Вопрос №{question_num}:\n{question}\n\n<tg-spoiler>{answer}</tg-spoiler>', parse_mode = 'HTML' # noqa
    )
    return "ANSWER"


def show_score(update: Update, context):
    user_key = f"{HASH_START}:{update.effective_user.id}"
    score = get_score(user_key)
    update.message.reply_text(f'Ваш счёт: {score}')
    return "START"


def check_answer(update: Update, context):
    user_key = f"{HASH_START}:{update.effective_user.id}"
    if is_correct_answer(user_key, update.message.text):
        update.message.reply_text('Правильно!')
        add_points(user_key)
        give_up(update, context)
        return "START"
    else:
        update.message.reply_text('Неправильно. Попробуйте еще раз или нажмите "Сдаться".') # noqa
        return "ANSWER"


def give_up(update: Update, context):
    user_key = f"{HASH_START}:{update.effective_user.id}"
    correct_answer = get_correct_answer(user_key)
    update.message.reply_text(f'Правильный ответ: {correct_answer}')
    if not try_update_question(user_key):
        score = get_score(user_key)
        update.message.reply_text(
            f"Все вопросы закончились!\nВаш итоговый счёт составил: {score}\nНачинаем новую игру!" # noqa
        )
        start(update, context)
    return "START"


if __name__ == "__main__":
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
