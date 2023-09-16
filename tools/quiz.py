import random
import os


class QuizQuestionsCash:
    def __init__(self, default_path: str) -> None:
        self.questions_answers = dict()
        self.index = 0
        self.looked_files = set()
        self.default_path = default_path

    def add_question_answer(self, question: str, answer: str):
        self.questions_answers[self.index] = (question, answer)
        self.index += 1

    def store_new_questions(self, path=None):
        if not path:
            path = self.default_path
        local_files = set(os.listdir(path))
        avialable_files = local_files.difference(self.looked_files)
        if not avialable_files:
            return
        random_file = random.choice(list(avialable_files))

        with open(os.path.join(path, random_file), 'r', encoding='KOI8-R') as file:
            file_data = file.read()

        file_blocks = [block.strip('\n') for block in file_data.split('\n\n')]
        for iters, block in enumerate(file_blocks):
            if block.startswith('Вопрос '):
                question = '\n'.join(block.split('\n')[1:])
                answer = '\n'.join(file_blocks[iters+1].split('\n')[1:])
                self.add_question_answer(question, answer)

    def get_random_question_anwer(self) -> tuple:
        return self.questions_answers[random.randint(0, self.index-1)]
