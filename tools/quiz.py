import random
import os


def get_qustions_answers(file_name: str) -> dict:
    qustions_answers = dict()
    last_added_tour = 'default'
    last_added_question = ''
    last_added_answer = ''
    next_is_tour = False
    next_is_question = False
    next_is_answer = False
    with open(file_name, 'r', encoding='KOI8-R') as file:
        line = file.readline()
        while line:
            if next_is_tour:
                last_added_tour = line
                qustions_answers[line] = []
                next_is_tour = False
            elif next_is_question:
                if line == '\n':
                    next_is_question = False
                else:
                    last_added_question = last_added_question + line
            elif next_is_answer:
                if line == '\n':
                    next_is_answer = False
                    if last_added_tour not in qustions_answers:
                        qustions_answers[last_added_tour] = []
                    qustions_answers[last_added_tour].append(
                        (last_added_question, last_added_answer)
                    )
                    last_added_question = ''
                    last_added_answer = ''
                else:
                    last_added_answer = last_added_answer + line
            elif line.startswith('Тур:'):
                next_is_tour = True
            elif line.startswith('Вопрос '):
                next_is_question = True
            elif line.startswith('Ответ:'):
                next_is_answer = True
            line = file.readline()
    return qustions_answers


def get_random_question_answer(path: str) -> tuple:
    random_file = random.choice(os.listdir(path))
    qustions_answers = get_qustions_answers(os.path.join(path, random_file))
    return random.choice(random.choice(list(qustions_answers.values())))
