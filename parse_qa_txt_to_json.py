import os
import json


def read_files_from_directory(directory):
    ''' Переход по .txt файлам с вопросами и ответами с целью сбора всех вопросов и ответов'''
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
    lines = content.split('\n')
    question_answer_pairs = []
    question = None
    answer = None

    iteration = iter(lines)
    for line in iteration:
        line = line.strip()
        question = ''
        answer = ''
        if line.startswith('Вопрос'):
            while (line and line != ''):
                line = next(iteration)
                if '.jpg' in line:
                    question = ''
                    break
                if question == '':
                    question = line
                else:
                    if line.startswith(' '):
                        question = f'{question}{line}'
                    else:
                        question = f'{question} {line}'
            line = next(iteration)
            if line.startswith('Ответ'):
                while (line and line != ''):
                    line = next(iteration)
                    if '.jpg' in line or len(line) > 20:
                        answer = ''
                        break
                    answer = f'{answer}\n{line}'
            if question and answer:
                question_answer_pairs.append(
                    {'question': question, 'answer': answer}
                )

    return question_answer_pairs


def save_to_json(data, filename):
    '''Экспорт данных в Json'''
    with open(filename, 'w', encoding='utf-8') as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)

if __name__ == '__main__':
    questions_answers = read_files_from_directory('./quiz-questions')
    save_to_json(questions_answers, 'QA.json')
