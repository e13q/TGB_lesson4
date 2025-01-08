import os
import json


def extract_questions_answers(directory):
    '''
    Переход по .txt файлам с вопросами и ответами
    с целью сбора всех вопросов и ответов
    '''
    questions_answers = []
    for filename in os.listdir(directory):
        if filename.endswith(".txt"):
            filepath = os.path.join(directory, filename)
            with open(filepath, 'r', encoding='KOI8-R') as file:
                content = file.read()
                questions_answers += parse_content(content)
    return questions_answers


def parse_content(content):
    ''' Парсинг файлов на вопросы и ответы'''
    lines = content.split('\n\n')
    question_answer_pairs = []
    question = None
    answer = None
    iteration = lines
    for line in iteration:
        if line.startswith('Вопрос'):
            question = line[line.index(':')+2:]
        elif line.startswith('Ответ:'):
            answer = line[line.index(':')+2:]
        if question and answer:
            question_answer_pairs.append(
                {'question': question, 'answer': answer}
            )
            question = ''
            answer = ''
    return question_answer_pairs


def save_to_json(data, filename):
    '''Экспорт данных в Json'''
    with open(filename, 'w', encoding='utf-8') as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)


if __name__ == '__main__':
    questions_answers = extract_questions_answers('./quiz-questions')
    save_to_json(questions_answers, 'QA.json')
