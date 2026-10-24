import re
from dataclasses import dataclass
from typing import Set, Tuple
from ..prompts import load_prompt

from ..base_game import BaseGame, GameMove, GameResult, GameStatus
from .reasoning_utils import extract_reasoning_and_answer, strip_reasoning_for_context
from ..constants import FieldOfMiraclesTextConstants, FieldOfMiraclesPromptsGenerator


@dataclass
class FieldOfMiraclesState:
    word: str
    revealed_word: str
    guessed_letters: Set[str]
    revealed_letters: Set[str]
    game_over: bool
    won: bool


class FieldOfMiraclesGame(BaseGame):

    def __init__(
            self,
            game_id: str,
            word: str,
            max_attempts: int = None,
            enable_reasoning: bool = False,
            language: str = "ru",
            level: str = "",
    ):
        if not max_attempts:
            if language == "en":
                max_attempts = 26
            else:
                max_attempts = 29
        super().__init__(game_id, max_attempts)

        self.word = word.upper()
        self.enable_reasoning = enable_reasoning
        self.language = language
        self.level = level

        self.prompt_template = load_prompt("wheel_of_fortune", "prompt", language)

        self.constants = FieldOfMiraclesTextConstants(language=language)
        self.prompt_generator = FieldOfMiraclesPromptsGenerator(language=language, cot=self.enable_reasoning)

        self.equivalent_letters = self.constants.equivalent_letters

        self.state = FieldOfMiraclesState(
            word=self.word,
            revealed_word=self._create_revealed_word(set()),
            guessed_letters=set(),
            revealed_letters=set(),
            game_over=False,
            won=False
        )

    def _create_revealed_word(self, revealed_letters: Set[str]) -> str:
        result = []
        for char in self.word:
            if char in revealed_letters or self._is_equivalent_revealed(char, revealed_letters):
                result.append(char)
            else:
                result.append('_')
        return ' '.join(result)

    def _is_equivalent_revealed(self, letter: str, revealed_letters: Set[str]) -> bool:
        for equiv_group in self.equivalent_letters:
            if letter in equiv_group:
                for revealed in revealed_letters:
                    if revealed in equiv_group:
                        return True
        return False

    def _normalize_letter(self, letter: str) -> str:
        letter = letter.upper()
        for equiv_group in self.equivalent_letters:
            if letter in equiv_group:
                return min(equiv_group)
        return letter

    def get_system_prompt(self) -> str:
        prompt = self.prompt_template.format(
            REASONING_INSTRUCTION=self.prompt_generator.reasoning_instruction_prompt(),
            WORD_DISPLAY=self.state.revealed_word,
            MAX_TURNS=self.max_attempts,
            NUM_TURNS=self.get_move_count()
        )

        return prompt

    def get_initial_user_message(self) -> str:
        return self.prompt_generator.init_game_prompt()

    def _extract_guess(self, response: str) -> Tuple[str, bool]:
        matches = re.findall(fr'{self.constants.answer_key_word}:\s*(.+)', response, re.IGNORECASE)
        if matches:
            guess = matches[-1].strip()
        else:
            guess = response.strip()
            if not re.search(fr'[{self.constants.regexp_alphabet}]', guess):
                return "", False

        word_match = re.search(fr'{self.constants.word_key_word}:\s*([{self.constants.regexp_alphabet}]+)', guess,
                               re.IGNORECASE)
        if word_match:
            return word_match.group(1).upper(), True

        guess = re.sub(fr'[^{self.constants.regexp_alphabet}]', '', guess)
        if len(guess) == 1:
            return guess[0].upper(), False

        return "", False

    def process_player_move(self, player_input: str) -> GameMove:
        move_number = self.get_move_count() + 1

        if self.enable_reasoning:
            reasoning, answer = extract_reasoning_and_answer(player_input)
        else:
            reasoning = ""
            answer = player_input

        guess, is_word_guess = self._extract_guess(answer)

        metadata = {
            "reasoning": reasoning,
            "guess": guess,
            "is_word_guess": is_word_guess
        }

        if not guess:
            feedback = self.prompt_generator.wrong_format_answer_feedback_prompt()
            move = GameMove(
                move_number=move_number,
                player_input=player_input,
                player_answer=f"{self.constants.answer_key_word}: {strip_reasoning_for_context(player_input)}" if self.enable_reasoning else answer,
                feedback=feedback,
                is_valid=False,
                metadata=metadata
            )
            self.moves.append(move)
            return move

        if is_word_guess:
            feedback = self._process_word_guess(guess)
        else:
            feedback = self._process_letter_guess(guess)

        feedback += self.prompt_generator.game_status_prompt(
            self.state.revealed_word, self.get_move_count(), self.max_attempts
        )

        move = GameMove(
            move_number=move_number,
            player_input=player_input,
            player_answer=f"{self.constants.answer_key_word}: {strip_reasoning_for_context(player_input)}" if self.enable_reasoning else answer,
            feedback=feedback,
            is_valid=True,
            metadata=metadata
        )
        self.moves.append(move)

        return move

    def _process_letter_guess(self, letter: str) -> str:
        normalized_letter = self._normalize_letter(letter)

        if normalized_letter in self.state.guessed_letters:
            return self.prompt_generator.repeated_letter_guess_feedback_prompt(letter)

        self.state.guessed_letters.add(normalized_letter)

        letter_in_word = False
        occurrences = 0

        for char in self.word:
            if char == letter or self._is_equivalent_letter(char, letter):
                letter_in_word = True
                occurrences += 1
                self.state.revealed_letters.add(char)

        self.state.revealed_word = self._create_revealed_word(self.state.revealed_letters)

        if letter_in_word:
            feedback = self.prompt_generator.correct_letter_guess_feedback_prompt(letter, occurrences=occurrences)

            if '_' not in self.state.revealed_word:
                self.state.won = True
                self.state.game_over = True
                self.status = GameStatus.WON
                feedback = self.prompt_generator.correct_letter_and_word_guess_feedback_prompt(letter, occurrences=occurrences, word=self.word)

            return feedback
        else:
            if not self.has_attempts_left():
                self.state.game_over = True
                self.state.won = False
                self.status = GameStatus.LOST
                return self.prompt_generator.no_moves_left_feedback_prompt(letter, max_attempts=self.max_attempts, is_letter=True)
            return self.prompt_generator.wrong_guess_feedback_prompt(letter, is_letter=True)

    def _process_word_guess(self, word_guess: str) -> str:
        if word_guess == self.word:
            self.state.won = True
            self.state.game_over = True
            self.status = GameStatus.WON
            self.state.revealed_word = ' '.join(self.word)

            return self.prompt_generator.correct_word_guess_feedback_prompt(word_guess)
        else:
            if not self.has_attempts_left():
                self.state.game_over = True
                self.state.won = False
                self.status = GameStatus.LOST
                return self.prompt_generator.no_moves_left_feedback_prompt(word_guess, max_attempts=self.max_attempts, is_letter=False)
            return self.prompt_generator.wrong_guess_feedback_prompt(word_guess, is_letter=False)

    def _is_equivalent_letter(self, letter1: str, letter2: str) -> bool:
        if letter1 == letter2:
            return True
        for equiv_group in self.equivalent_letters:
            if letter1 in equiv_group and letter2 in equiv_group:
                return True
        return False

    def should_retry_response(self, response: str) -> bool:
        if self.enable_reasoning:
            _, answer = extract_reasoning_and_answer(response)
        else:
            answer = response
        guess, _ = self._extract_guess(answer)
        return not bool(guess)

    def get_max_format_retries(self) -> int:
        return 0

    def is_game_over(self) -> bool:
        if not self.has_attempts_left() and not self.state.won:
            self.state.game_over = True
            self.status = GameStatus.LOST
        return self.state.game_over

    def get_result(self) -> GameResult:
        metadata = {
            "revealed_letters": list(self.state.revealed_letters),
            "guessed_letters": list(self.state.guessed_letters),
            "word_length": len(self.word),
            "final_revealed_word": self.state.revealed_word,
            "level": self.level,
        }

        return GameResult(
            game_id=self.game_id,
            game_type="field_of_miracles",
            status=self.status,
            moves=self.moves,
            total_moves=len(self.moves),
            won=self.state.won,
            target=self.word,
            metadata=metadata
        )
