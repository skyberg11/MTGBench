from abc import ABC, abstractmethod
from dataclasses import dataclass, field


COT_REMINDERS = {
    "ru": "Не забывай рассуждать перед окончательным ответом. В историю диалога выше твои ответы передаются без рассуждений, так что не забывай рассуждать и только потом пиши окончательный ответ.",
    "en": "Don't forget to reason before giving the final answer. In the history of the dialogue above, your answers are transmitted without reasoning, so do not forget to reason and only then write the final answer."
}


def strip_cot_reminders_from_history(messages, key='content'):
    """Strip COT reminders from all user messages except the last one.

    Works with list of dicts. The `key` parameter specifies the field name
    for message content ('content' for LLMPlayer, 'message' for training data).
    """
    for i in range(len(messages) - 1):
        if messages[i]["role"] == "user":
            for cot_reminder in COT_REMINDERS.values():
                messages[i][key] = messages[i][key].replace(cot_reminder, '').strip()


@dataclass
class TwentyQuestionsTextConstants:
    """Constants for the 20 Questions game"""
    language: str

    word_guess_prompt_prefix: str = field(init=False)
    attribute_question_prompt_prefix: str = field(init=False)
    answer_key_word: str = field(init=False)
    reasoning_key_word: str = field(init=False)
    yes_answer: str = field(init=False)
    no_answer: str = field(init=False)
    attribute_word: str = field(init=False)
    word_word: str = field(init=False)

    def __post_init__(self):
        if self.language == "ru":
            self.word_guess_prompt_prefix = "Это слово "
            self.attribute_question_prompt_prefix = "У вашего слова есть атрибут "
            self.answer_key_word = "Ответ"
            self.reasoning_key_word = "Рассуждение"
            self.yes_answer = "да"
            self.no_answer = "нет"
            self.attribute_word = "атрибут"
            self.word_word = "слово"
            self.confirm_word_prompt = "Подтвердите ваше слово?"
        else:
            self.word_guess_prompt_prefix = "Is the word "
            self.attribute_question_prompt_prefix = "Does your word have the attribute "
            self.answer_key_word = "Answer"
            self.reasoning_key_word = "Reasoning"
            self.yes_answer = "yes"
            self.no_answer = "no"
            self.attribute_word = "attribute"
            self.word_word = "word"
            self.confirm_word_prompt = "Confirm your word?"

class BasePromptsGenerator(ABC):
    def __init__(self, language: str, cot: bool = False):
        self.language = language
        self.cot = cot

    @abstractmethod
    def reasoning_instruction_prompt(self):
        pass

    @abstractmethod
    def init_game_prompt(self):
        """Generate the initial prompt for the game"""
        pass

    def cot_history_reminder_prompt(self):
        if not self.cot:
            return ""
        if self.language == "ru":
            return COT_REMINDERS["ru"]
        else:
            return COT_REMINDERS["en"]

class TwentyQuestionsPromptsGenerator(BasePromptsGenerator):
    def __init__(self, language: str, cot: bool = False):
        super().__init__(language, cot)
        self.constants = TwentyQuestionsTextConstants(language)

    def init_game_prompt(self):
        """Generate the initial prompt for the game"""
        return ""

    def reasoning_instruction_prompt(self):
        if self.cot:
            if self.language == "ru":
                return f"Объясни свои рассуждения перед ответом в формате:\n{self.constants.reasoning_key_word}: <ваши мысли>\n{self.constants.answer_key_word}: <ваш ответ>"
            else:
                return f"Explain your reasoning before answering in the format:\n{self.constants.reasoning_key_word}: <your thoughts>\n{self.constants.answer_key_word}: <your answer>"
        else:
            if self.language == "ru":
                return f"Не пиши никаких рассуждений, дай сразу же окончательный ответ в формате\n{self.constants.answer_key_word}: <ваш ответ>."
            else:
                return f"Don't write any reasoning, give the final answer immediately in the format\n{self.constants.answer_key_word}: <your answer>."

    def _feedback_contradiction_prompt(self, contradiction_description: str):
        if self.language == "ru":
            return f"Обнаружено противоречие! {contradiction_description}"
        else:
            return f"Contradiction detected! {contradiction_description}"

    def word_guess_prompt(self, word: str) -> str:
        """Generate a prompt for guessing a word"""
        return f"{self.constants.word_guess_prompt_prefix}'{word}'?"

    def attribute_question_prompt(self, attribute: str) -> str:
        """Generate a prompt for asking about an attribute"""
        return f"{self.constants.attribute_question_prompt_prefix}'{attribute}'?"

    def no_more_words_left_contradiction_prompt(self, question: str, answer: str) -> str:
        """Generate a prompt explaining the reason for a contradiction"""
        if self.language == "ru":
            return (
                f"После ответа '{answer}' на вопрос '{question}', "
                f"не осталось ни одного слова, согласующегося со всеми ответами. "
                f"Обнаружено противоречие в ответах."
            )
        else:
            return (
                f"After the answer '{answer}' to the question '{question}', "
                f"there are no words left that are consistent with all the answers. "
                f"A contradiction in the answers has been detected."
            )

    def no_more_words_left_and_last_word_was_not_secret_word_contradiction_prompt(self, question: str, answer: str, secret_word: str, word: str) -> str:
        """Generate a prompt explaining the reason for a contradiction"""
        if self.language == "ru":
            return (
                f"После ответа '{answer}' на вопрос '{question}', "
                f"не осталось ни одного слова, согласующегося со всеми ответами. "
                f"Последнее оставшееся слово '{word}' не было загаданным словом '{secret_word}'."
            )
        else:
            return (
                f"After the answer '{answer}' to the question '{question}', "
                f"there are no words left that are consistent with all the answers. "
                f"The last remaining word '{word}' was not the secret word '{secret_word}'."
            )

    def secret_word_excluded_contradiction_prompt(self, secret_word: str, question: str, answer: str) -> str:
        if self.language == "ru":
            return (
                f"После ответа '{answer}' на вопрос '{question}', "
                f"загаданное слово '{secret_word}' больше не согласуется с данными ответами. "
                f"Обнаружено противоречие."
            )
        else:
            return (
                f"After the answer '{answer}' to the question '{question}', "
                f"the secret word '{secret_word}' is no longer consistent with the given answers. "
                f"Contradiction detected."
            )

    def secret_word_excluded_feedback_prompt(self, secret_word: str, question: str, answer: str) -> str:
        return self._feedback_contradiction_prompt(
            self.secret_word_excluded_contradiction_prompt(secret_word, question, answer)
        )

    def no_more_words_left_feedback_prompt(self, question: str, answer: str) -> str:
        return self._feedback_contradiction_prompt(self.no_more_words_left_contradiction_prompt(question, answer))

    def no_more_words_left_and_last_word_was_not_secret_word_feedback_prompt(self, question: str, answer: str, secret_word: str, word: str) -> str:
        return self._feedback_contradiction_prompt(self.no_more_words_left_and_last_word_was_not_secret_word_contradiction_prompt(question, answer, secret_word, word))

    def wrong_format_answer_feedback_prompt(self):
        """Generate feedback for an answer in the wrong format"""
        if self.language == "ru":
            return "Не удалось распознать ваш ответ. Используйте формат: 'Ответ: да' или 'Ответ: нет'"
        else:
            return "Could not recognize your answer. Please use the format: 'Answer: yes' or 'Answer: no'"

    def correct_secret_word_guess_feedback_prompt(self, secret_word: str):
        """Generate feedback for a correct secret word guess"""
        if self.language == "ru":
            return (f"Правильно! Загаданное слово: {secret_word}. "
                    f"Модель ответила согласованно.")
        else:
            return f"Correct! The secret word was: {secret_word}. The model answered consistently."

    def word_guess_yes_contradiction_prompt(self, secret_word: str, guessed_word: str):
        if self.language == "ru":
            return (f"Модель подтвердила слово '{guessed_word}', "
                    f"но загаданное слово было '{secret_word}'.")
        else:
            return (f"The model confirmed the word '{guessed_word}', "
                    f"but the secret word was '{secret_word}'.")

    def word_guess_yes_contradiction_feedback_prompt(self, secret_word: str, guessed_word: str):
        return self._feedback_contradiction_prompt(self.word_guess_yes_contradiction_prompt(secret_word, guessed_word))

    def word_guess_no_contradiction_prompt(self, secret_word: str):
        if self.language == "ru":
            return (f"Модель отвергла слово '{secret_word}', "
                    f"но это было загаданное слово.")
        else:
            return (f"The model rejected the word '{secret_word}', "
                    f"but it was the secret word.")

    def word_guess_no_contradiction_feedback_prompt(self, secret_word: str):
        return self._feedback_contradiction_prompt(self.word_guess_no_contradiction_prompt(secret_word))

    def no_contradiction_feedback_prompt(self, remaining_count: int, question: str):
        if self.cot:
            if self.language == "ru":
                cot_addition = COT_REMINDERS["ru"]
            else:
                cot_addition = COT_REMINDERS["en"]
        else:
            cot_addition = ""
        if self.language == "ru":
            return f"Принято. Осталось слов, согласующихся с ответами: {remaining_count}\n\nСледующий вопрос: {question}\n{cot_addition}"
        else:
            return f"Accepted. Remaining words consistent with the answers: {remaining_count}\n\nNext question: {question}\n{cot_addition}"

    def no_contradiction_and_no_moves_left_feedback_prompt(self, max_turns: int):
        if self.language == "ru":
            return f"Принято. Модель ответила согласованно и не пришла к противоречию на протяжении всех {max_turns} ходов, но не пользователь не угадал слово и не осталось ходов. Игра окончена."
        else:
            return f"Accepted. The model answered consistently and did not reach a contradiction throughout all {max_turns} turns, but the user did not guess the word and there are no moves left. Game over."


RUSSIAN_LETTER_FREQUENCY = {
    'О': 10.97, 'Е': 8.45, 'А': 8.01, 'И': 7.35, 'Н': 6.70,
    'Т': 6.26, 'С': 5.47, 'Р': 4.73, 'В': 4.54, 'Л': 4.40,
    'К': 3.49, 'М': 3.21, 'Д': 2.98, 'П': 2.81, 'У': 2.62,
    'Я': 2.01, 'Ы': 1.90, 'Ь': 1.74, 'Г': 1.70, 'З': 1.65,
    'Б': 1.59, 'Ч': 1.44, 'Й': 1.21, 'Х': 0.97, 'Ж': 0.94,
    'Ш': 0.73, 'Ю': 0.64, 'Ц': 0.48, 'Щ': 0.36, 'Э': 0.32,
    'Ф': 0.26, 'Ъ': 0.04, 'Ё': 0.04,
}

ENGLISH_LETTER_FREQUENCY = {
    'E': 12.70, 'T': 9.06, 'A': 8.17, 'O': 7.51, 'I': 6.97,
    'N': 6.75, 'S': 6.33, 'H': 6.09, 'R': 5.99, 'D': 4.25,
    'L': 4.03, 'C': 2.78, 'U': 2.76, 'M': 2.41, 'W': 2.36,
    'F': 2.23, 'G': 2.02, 'Y': 1.97, 'P': 1.93, 'B': 1.29,
    'V': 0.98, 'K': 0.77, 'J': 0.15, 'X': 0.15, 'Q': 0.10,
    'Z': 0.07,
}

FOM_LETTER_FREQUENCY = {
    "ru": RUSSIAN_LETTER_FREQUENCY,
    "en": ENGLISH_LETTER_FREQUENCY,
}

FOM_EQUIVALENT_LETTERS = {
    "ru": {
        frozenset(['И', 'Й']),
        frozenset(['Е', 'Ё']),
        frozenset(['Ь', 'Ъ', 'Ы']),
    },
    "en": set(),
}


@dataclass
class FieldOfMiraclesTextConstants:
    """Constants for the Field of Miracles game"""
    language: str

    answer_key_word: str = field(init=False)
    reasoning_key_word: str = field(init=False)
    word_key_word: str = field(init=False)
    regexp_alphabet: str = field(init=False)
    equivalent_letters: set = field(init=False)

    def __post_init__(self):
        if self.language == "ru":
            self.answer_key_word = "Ответ"
            self.reasoning_key_word = "Рассуждение"
            self.word_key_word = "СЛОВО"
            self.regexp_alphabet = "А-ЯЁа-яё"
        else:
            self.answer_key_word = "Answer"
            self.reasoning_key_word = "Reasoning"
            self.word_key_word = "WORD"
            self.regexp_alphabet = "A-Za-z"
        self.equivalent_letters = FOM_EQUIVALENT_LETTERS.get(self.language, set())


class FieldOfMiraclesPromptsGenerator(BasePromptsGenerator):
    def __init__(self, language: str, cot: bool = False):
        super().__init__(language, cot)
        self.constants = FieldOfMiraclesTextConstants(language)

    def reasoning_instruction_prompt(self):
        if self.cot:
            if self.language == "ru":
                return f"Объясни свои рассуждения перед ответом в формате:\n{self.constants.reasoning_key_word}: <ваши мысли>\n{self.constants.answer_key_word}: <ваш ответ>"
            else:
                return f"Explain your reasoning before answering in the format:\n{self.constants.reasoning_key_word}: <your thoughts>\n{self.constants.answer_key_word}: <your answer>"
        else:
            if self.language == "ru":
                return f"Не пиши никаких рассуждений, дай сразу же окончательный ответ в формате\n{self.constants.answer_key_word}: <ваш ответ>."
            else:
                return f"Don't write any reasoning, give the final answer immediately in the format\n{self.constants.answer_key_word}: <your answer>."

    def init_game_prompt(self):
        """Generate the initial prompt for the game"""
        if self.language == "ru":
            return "Начинаем игру! Ваш ход."
        else:
            return "Let's start the game! Your move."

    def wrong_format_answer_feedback_prompt(self):
        """Generate feedback for an answer in the wrong format"""
        if self.language == "ru":
            return "Не удалось распознать вашу попытку. Используйте формат: 'Ответ: О' для буквы или 'Ответ: СЛОВО: СОБАКА' для слова."
        else:
            return "Could not recognize your attempt. Please use the format: 'Answer: O' for a letter or 'Answer: WORD: DOG' for a word."

    def correct_word_guess_feedback_prompt(self, word: str):
        """Generate feedback for a correct word guess"""
        if self.language == "ru":
            return f"Правильно! Слово '{word}' угадано!"
        else:
            return f"Correct! The word '{word}' has been guessed!"

    def no_moves_left_feedback_prompt(self, guess: str, max_attempts: int, is_letter: bool):
        """Generate feedback for when the word is not guessed and there are no moves left"""
        if self.language == "ru":
            if is_letter:
                wrong_guess = f"Буквы '{guess}' нет в слове."
            else:
                wrong_guess = f"Слово '{guess}' не верно."
        else:
            if is_letter:
                wrong_guess = f"The letter '{guess}' is not in the word."
            else:
                wrong_guess = f"The word '{guess}' is incorrect."
        if self.language == "ru":
            return f"Неправильно. {wrong_guess} Вы исчерпали все попытки ({max_attempts}). Игра окончена. "
        else:
            return f"Incorrect. {wrong_guess} You have exhausted all attempts ({max_attempts}). Game over. "

    def wrong_guess_feedback_prompt(self, guess: str, is_letter: bool):
        """Generate feedback for when the word is not guessed and there are no moves left"""
        if self.language == "ru":
            if is_letter:
                wrong_guess = f"Буквы '{guess}' нет в слове."
            else:
                wrong_guess = f"Слово '{guess}' не верно."
        else:
            if is_letter:
                wrong_guess = f"The letter '{guess}' is not in the word."

            else:
                wrong_guess = f"The word '{guess}' is incorrect."


        if self.cot:
            if self.language == "ru":
                cot_addition = COT_REMINDERS["ru"]
            else:
                cot_addition = COT_REMINDERS["en"]
        else:
            cot_addition = ""
        if self.language == "ru":
            return f"Неправильно. {wrong_guess}\n{cot_addition}"
        else:
            return f"Incorrect. {wrong_guess}\n{cot_addition}"

    def repeated_letter_guess_feedback_prompt(self, letter: str):
        """Generate feedback for a repeated letter guess"""
        if self.cot:
            if self.language == "ru":
                cot_addition = COT_REMINDERS["ru"]
            else:
                cot_addition = COT_REMINDERS["en"]
        else:
            cot_addition = ""
        if self.language == "ru":
            return f"Буква '{letter}' уже была названа. Попробуйте другую.\n{cot_addition}"
        else:
            return f"The letter '{letter}' has already been guessed. Please try another one.\n{cot_addition}"

    def correct_letter_guess_feedback_prompt(self, letter: str, occurrences: int):
        """Generate feedback for a correct letter guess"""
        if self.cot:
            if self.language == "ru":
                cot_addition = COT_REMINDERS["ru"]
            else:
                cot_addition = COT_REMINDERS["en"]
        else:
            cot_addition = ""
        if self.language == "ru":
            return f"Правильно! Буква '{letter}' встречается {occurrences} раз(а).\n{cot_addition}"
        else:
            return f"Correct! The letter '{letter}' occurs {occurrences} time(s).\n{cot_addition}"

    def correct_letter_and_word_guess_feedback_prompt(self, letter: str, occurrences: int, word: str):
        """Generate feedback for a correct letter and word guess"""
        if self.language == "ru":
            return f"{self.correct_letter_guess_feedback_prompt(letter, occurrences)}\n\nПоздравляем! Вы угадали слово: {word}."
        else:
            return f"{self.correct_letter_guess_feedback_prompt(letter, occurrences)}\n\nCongratulations! You guessed the word: {word}."

    def game_status_prompt(self, revealed_word: str, move_count: int, max_attempts: int) -> str:
        """Generate the current game status string."""
        if self.language == "ru":
            return f"\nТекущее состояние:\nСлово: {revealed_word}\nИспользовано попыток: {move_count}/{max_attempts}"
        else:
            return f"\nCurrent state:\nWord: {revealed_word}\nAttempts used: {move_count}/{max_attempts}"


@dataclass
class CitiesTextConstants:
    language: str

    answer_key_word: str = field(init=False)
    reasoning_key_word: str = field(init=False)
    regexp_alphabet: str = field(init=False)

    def __post_init__(self):
        if self.language == "ru":
            self.answer_key_word = "Ответ"
            self.reasoning_key_word = "Рассуждение"
            self.regexp_alphabet = "А-ЯЁа-яё"
        else:
            self.answer_key_word = "Answer"
            self.reasoning_key_word = "Reasoning"
            self.regexp_alphabet = "A-Za-z"


class CitiesPromptsGenerator(BasePromptsGenerator):
    def __init__(self, language: str, cot: bool = False):
        super().__init__(language, cot)
        self.constants = CitiesTextConstants(language)

    def reasoning_instruction_prompt(self):
        if not self.cot:
            return ""
        if self.language == "ru":
            return "Сначала кратко объясни выбор, а затем напиши ответ в формате:\nРассуждение: <твои мысли>\nОтвет: <полное название города>"
        else:
            return "Briefly explain your choice in reasoning, then answer. The required format:\n\nReasoning: <your thoughts>\nAnswer: <full city name>"

    def init_game_prompt(self, start_city: str):
        if self.language == "ru":
            return f"Начинаем игру. Я начинаю с города \"{start_city}\". Ваш ход."
        else:
            return f"Let's start. My opening city is \"{start_city}\". Your move."

    def wrong_format_answer_feedback_prompt(self):
        if self.language == "ru":
            if self.cot:
                return f"Не удалось распознать город. {self.reasoning_instruction_prompt()}."
            return "Не удалось распознать город. Используйте формат: 'Ответ: <полное название города>'."
        else:
            if self.cot:
                return f"Could not recognize a city. {self.reasoning_instruction_prompt()}."
            return "Could not recognize a city. Please use the format: 'Answer: <full city name>'."

    def city_not_found_feedback_prompt(self, city: str):
        if self.language == "ru":
            return f"Город '{city}' не найден в базе. Игра окончена."
        else:
            return f"The city '{city}' was not found in the database. Game over."

    def repeated_city_feedback_prompt(self, city: str):
        if self.language == "ru":
            return f"Город '{city}' уже был назван раньше. Игра окончена."
        else:
            return f"The city '{city}' has already been used. Game over."

    def wrong_letter_feedback_prompt(self, city: str, required_letter: str):
        if self.language == "ru":
            return f"Город '{city}' не начинается на букву '{required_letter}'. Игра окончена."
        else:
            return f"The city '{city}' does not start with '{required_letter}'. Game over."

    def next_city_feedback_prompt(self, city: str, next_letter: str):
        reminder = self.cot_history_reminder_prompt()
        if self.language == "ru":
            base = f"Принято. Мой город: {city}."
        else:
            base = f"Accepted. My city is: {city}."
        if reminder:
            return f"{base}\n{reminder}"
        return base

    def no_available_city_feedback_prompt(self, city: str):
        if self.language == "ru":
            return f"Принято. После города '{city}' я больше не могу назвать новый город. Вы победили."
        else:
            return f"Accepted. After the city '{city}', I cannot name another valid city. You win."


@dataclass
class WordleTextConstants:
    language: str

    answer_key_word: str = field(init=False)
    reasoning_key_word: str = field(init=False)
    regexp_alphabet: str = field(init=False)

    def __post_init__(self):
        if self.language == "ru":
            self.answer_key_word = "Ответ"
            self.reasoning_key_word = "Рассуждение"
            self.regexp_alphabet = "А-ЯЁа-яё"
        else:
            self.answer_key_word = "Answer"
            self.reasoning_key_word = "Reasoning"
            self.regexp_alphabet = "A-Za-z"


class WordlePromptsGenerator(BasePromptsGenerator):
    def __init__(self, language: str, cot: bool = False):
        super().__init__(language, cot)
        self.constants = WordleTextConstants(language)

    def reasoning_instruction_prompt(self):
        if not self.cot:
            return ""
        if self.language == "ru":
            return "Сначала кратко объясни гипотезу в рассуждениях, затем напиши ответ. Необходимый формат:\n\nРассуждение: <ваши мысли>\nОтвет: <слово из 5 букв>"
        else:
            return "Briefly explain your hypothesis in reasoning, then answer. The required format:\n\nReasoning: <your thoughts>\nAnswer: <5-letter word>"

    def init_game_prompt(self):
        if self.language == "ru":
            return "Начинаем игру. Ваш первый вариант слова."
        else:
            return "Let's start the game. Give your first word."

    def wrong_format_answer_feedback_prompt(self):
        if self.language == "ru":
            if self.cot:
                return f"Не удалось распознать слово. {self.reasoning_instruction_prompt()}."
            return "Не удалось распознать слово. Используйте формат: 'Ответ: <слово из 5 букв>'."
        else:
            if self.cot:
                return f"Could not recognize a word. {self.reasoning_instruction_prompt()}."
            return "Could not recognize a word. Please use the format: 'Answer: <5-letter word>'."

    def invalid_length_feedback_prompt(self, expected_length: int):
        reminder = self.cot_history_reminder_prompt()
        if self.language == "ru":
            if self.cot:
                return f"Нужно назвать слово ровно из {expected_length} букв. {self.reasoning_instruction_prompt()}."
            base = f"Нужно назвать слово ровно из {expected_length} букв."
        else:
            if self.cot:
                return f"You must provide a word with exactly {expected_length} letters. {self.reasoning_instruction_prompt()}."
            base = f"You must provide a word with exactly {expected_length} letters."
        if reminder:
            return f"{base}\n{reminder}"
        return base

    def invalid_characters_feedback_prompt(self):
        reminder = self.cot_history_reminder_prompt()
        if self.language == "ru":
            base = "Нужно использовать только русские буквы."
        else:
            base = "Please use only English letters."
        if reminder:
            return f"{base}\n{reminder}"
        return base

    def invalid_dictionary_word_feedback_prompt(self):
        reminder = self.cot_history_reminder_prompt()
        if self.language == "ru":
            base = "Это слово не похоже на корректное существительное в словаре. Попробуйте другое."
        else:
            base = "This word is not accepted for the game. Try another one."
        if reminder:
            return f"{base}\n{reminder}"
        return base

    def green_feedback_line(self, letter: str):
        if self.language == "ru":
            return f'- "{letter}" - зелёная буква'
        else:
            return f'- "{letter}" - green letter'

    def yellow_feedback_line(self, letter: str):
        if self.language == "ru":
            return f'- "{letter}" - жёлтая буква'
        else:
            return f'- "{letter}" - yellow letter'

    def gray_feedback_line(self, letter: str):
        if self.language == "ru":
            return f'- "{letter}" - серая буква'
        else:
            return f'- "{letter}" - gray letter'

    def guess_feedback_prompt(self, states, guess: str):
        reminder = self.cot_history_reminder_prompt()
        feedback_lines = []

        for state, char in zip(states, guess):
            if state == "green":
                feedback_lines.append(self.green_feedback_line(char))
            elif state == "yellow":
                feedback_lines.append(self.yellow_feedback_line(char))
            elif state == "gray":
                feedback_lines.append(self.gray_feedback_line(char))

        base = "\n".join(feedback_lines)

        if reminder:
            return f"{base}\n\n{reminder}"
        return base


@dataclass
class DanetkiTextConstants:
    language: str

    answer_key_word: str = field(init=False)
    question_key_word: str = field(init=False)
    reasoning_key_word: str = field(init=False)

    def __post_init__(self):
        if self.language == "ru":
            self.answer_key_word = "Ответ"
            self.question_key_word = "Вопрос"
            self.reasoning_key_word = "Рассуждение"
        else:
            self.answer_key_word = "Answer"
            self.question_key_word = "Question"
            self.reasoning_key_word = "Reasoning"


class DanetkiPromptsGenerator(BasePromptsGenerator):
    def __init__(self, language: str, cot: bool = False):
        super().__init__(language, cot)
        self.constants = DanetkiTextConstants(language)

    def moves_left_prompt(self, moves_left: int):
        if self.language == "ru":
            return f"Осталось ходов до конца игры: {moves_left}"
        else:
            return f"Moves left until the end of the game: {moves_left}"

    def reasoning_instruction_prompt(self):
        if not self.cot:
            return ""
        if self.language == "ru":
            return (
                "Сначала кратко рассуждай, а затем выбери ровно одно действие в одном из форматов:\n"
                "Рассуждение: <ваши мысли>\n"
                "Вопрос: <один конкретный вопрос>\n"
                "или\n"
                "Рассуждение: <ваши мысли>\n"
                "Ответ: <ваша разгадка>"
            )
        else:
            return (
                "Reason briefly first, then choose exactly one action in one of these formats:\n"
                "Reasoning: <your thoughts>\n"
                "Question: <one specific question>\n"
                "or\n"
                "Reasoning: <your thoughts>\n"
                "Answer: <your solution>"
            )

    def init_game_prompt(self, puzzle_setup: str):
        if self.language == "ru":
            if self.cot:
                return (
                    "Вот завязка данетки:\n\n"
                    f"{puzzle_setup}\n\n"
                    "Сформулируй первый ход c рассуждениями: либо один уточняющий вопрос, либо финальную разгадку."
                )
            else:
                return (
                    "Вот завязка данетки:\n\n"
                    f"{puzzle_setup}\n\n"
                    "Сформулируй первый ход: либо один уточняющий вопрос, либо финальную разгадку."
                )
        else:
            if self.cot:
                return (
                    "Here is the setup of the lateral thinking puzzle:\n\n"
                    f"{puzzle_setup}\n\n"
                    "Make your first move with reasoning: either one clarifying question or a final solution."
                )
            else:
                return (
                    "Here is the setup of the lateral thinking puzzle:\n\n"
                    f"{puzzle_setup}\n\n"
                    "Make your first move: either one clarifying question or a final solution."
                )

    def wrong_format_answer_feedback_prompt(self):
        if self.language == "ru":
            if self.cot:
                return f"Не удалось распознать ход. {self.reasoning_instruction_prompt()}"
            else:
                return "Не удалось распознать ход. Используйте один из форматов: 'Вопрос: ...' или 'Ответ: ...'."
        else:
            if self.cot:
                return f"Could not recognize the move. {self.reasoning_instruction_prompt()}"
            else:
                return "Could not recognize the move. Please use one of these formats: 'Question: ...' or 'Answer: ...'."

    def no_questions_yet_prompt(self):
        if self.language == "ru":
            return "Пока вопросов не было."
        else:
            return "No questions yet."

    def dialogue_history_answer_prefix(self):
        if self.language == "ru":
            return "Ответ ведущего:"
        else:
            return "Host answer:"

    def final_answer_feedback_prompt(self, is_correct: bool):
        reminder = self.cot_history_reminder_prompt()
        if self.language == "ru":
            if is_correct:
                base = "Верно!"
            else:
                base = "Пока не совсем то. История объясняется чуть иначе или пропущены ключевые детали. Продолжайте задавать вопросы."
        else:
            if is_correct:
                base = "Correct!"
            else:
                base = "Not quite right. The story is explained a bit differently or key details are missing. Keep asking questions."
        if reminder and not is_correct:
            return f"{base}\n{reminder}"
        return base

    def judge_clarification_feedback_prompt(self, judge_answer: str):
        reminder = self.cot_history_reminder_prompt()
        if reminder:
            return f"{judge_answer}\n{reminder}"
        return judge_answer