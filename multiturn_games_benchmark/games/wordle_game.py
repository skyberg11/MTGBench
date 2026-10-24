"""Wordle game implementation."""

import re
from dataclasses import dataclass
from ..prompts import load_prompt
from typing import Any, Dict, Optional, Tuple

import nltk
from nltk.corpus import wordnet
from ruwordnet import RuWordNet

from ..base_game import BaseGame, GameMove, GameResult, GameStatus
from ..base_judge import BaseJudge
from ..constants import WordlePromptsGenerator, WordleTextConstants
from .reasoning_utils import extract_reasoning_and_answer, strip_reasoning_for_context


@dataclass
class WordleState:
    game_over: bool
    won: bool

def is_english_noun(word):
    synsets = wordnet.synsets(word)
    for synset in synsets:
        if synset.pos() == 'n':
            return True
    return False

def is_russian_noun(word):
    senses = RuWordNet().get_senses(word.lower())

    for sense in senses:
        if sense.synset.part_of_speech == 'N':
            return True
    return False


class WordleJudge(BaseJudge):
    """Script-based judge for Wordle game."""

    def __init__(self, prompt_generator: WordlePromptsGenerator, language: str = "ru"):
        self.prompt_generator = prompt_generator
        self.language = language

        self.wn = is_russian_noun if language == "ru" else is_english_noun

    def evaluate_player_move(self, game_state: Dict[str, Any], player_input: str) -> Tuple[bool, str]:
        is_valid_word, feedback = self._validate_input(game_state, player_input)
        if not is_valid_word:
            return False, feedback

        target = game_state["target_word"].lower()
        guess = player_input.lower()

        states = ["gray"] * len(guess)

        for idx, char in enumerate(guess):
            if char == target[idx]:
                states[idx] = "green"

        for idx, char in enumerate(guess):
            if states[idx] != "gray":
                continue
            if char in target:
                states[idx] = "yellow"

        feedback = self.prompt_generator.guess_feedback_prompt(
            states=states,
            guess=guess,
        )
        return guess == target, feedback

    def _validate_input(self, game_state: Dict[str, Any], word: str) -> Tuple[bool, str]:
        word = word.lower().strip().replace("ё", "е")
        expected_length = game_state["word_length"]

        if len(word) != expected_length:
            return False, self.prompt_generator.invalid_length_feedback_prompt(expected_length)

        if self.language == "ru":
            if not re.fullmatch(r"[а-я]+", word):
                return False, self.prompt_generator.invalid_characters_feedback_prompt()
        else:
            if not re.fullmatch(r"[a-z]+", word):
                return False, self.prompt_generator.invalid_characters_feedback_prompt()

        is_noun = self.wn(word)
        if not is_noun:
            return False, self.prompt_generator.invalid_dictionary_word_feedback_prompt()

        return True, "ok"


class WordleGame(BaseGame):
    """Wordle game implementation."""

    def __init__(
        self,
        game_id: str,
        target_word: str,
        max_attempts: int = 6,
        enable_reasoning: bool = False,
        language: str = "ru",
        is_CoT: Optional[bool] = None,
        lang: Optional[str] = None,
    ):
        super().__init__(game_id, max_attempts)

        if is_CoT is not None:
            enable_reasoning = is_CoT
        if lang is not None:
            language = lang

        self.target_word = target_word.lower().replace("ё", "е")
        self.word_length = len(self.target_word)
        self.enable_reasoning = enable_reasoning
        self.language = language

        self.constants = WordleTextConstants(language=language)
        self.prompt_generator = WordlePromptsGenerator(language=language, cot=enable_reasoning)
        self.judge = WordleJudge(prompt_generator=self.prompt_generator, language=language)

        self.prompt_template = load_prompt("wordle", "prompt", language)

        self.state = WordleState(game_over=False, won=False)

    def get_system_prompt(self) -> str:
        return self.prompt_template.format(
            REASONING_INSTRUCTION=self.prompt_generator.reasoning_instruction_prompt(),
        )

    def get_initial_user_message(self) -> str:
        return self.prompt_generator.init_game_prompt()

    def _extract_guess(self, response: str) -> str:
        match = re.search(fr"{self.constants.answer_key_word}:\s*(.+)", response, re.IGNORECASE)
        if match:
            guess = match.group(1).strip()
        else:
            guess = response.strip()
            if not re.fullmatch(fr"[{self.constants.regexp_alphabet}]+", guess):
                return ""

        if not guess:
            return ""
        guess = guess.splitlines()[0].strip().strip("\"'`")
        guess = re.sub(fr"[^{self.constants.regexp_alphabet}]", "", guess)
        if not guess:
            return ""
        return guess.lower().replace("ё", "е")

    def process_player_move(self, player_input: str) -> GameMove:
        move_number = self.get_move_count() + 1
        player_input = player_input.strip()

        if self.enable_reasoning:
            reasoning, answer = extract_reasoning_and_answer(player_input)
        else:
            reasoning = ""
            answer = player_input

        guess = self._extract_guess(answer)
        player_answer = strip_reasoning_for_context(player_input) if self.enable_reasoning else answer
        metadata = {
            "reasoning": reasoning,
            "guess": guess,
        }

        if not guess:
            move = GameMove(
                move_number=move_number,
                player_input=player_input,
                player_answer=player_answer,
                feedback=self.prompt_generator.wrong_format_answer_feedback_prompt(),
                is_valid=False,
                metadata=metadata,
            )
            self.moves.append(move)
            return move

        is_won, feedback = self.judge.evaluate_player_move(
            {
                "target_word": self.target_word,
                "word_length": self.word_length,
            },
            guess,
        )

        move = GameMove(
            move_number=move_number,
            player_input=player_input,
            player_answer=player_answer,
            feedback=feedback,
            is_valid=True,
            metadata=metadata,
        )
        self.moves.append(move)

        if is_won:
            self.state.game_over = True
            self.state.won = True
            self.status = GameStatus.WON
        elif not self.has_attempts_left():
            self.state.game_over = True
            self.state.won = False
            self.status = GameStatus.LOST

        return move

    def should_retry_response(self, response: str) -> bool:
        if self.enable_reasoning:
            _, answer = extract_reasoning_and_answer(response)
        else:
            answer = response
        guess = self._extract_guess(answer)
        return not bool(guess)

    def get_max_format_retries(self) -> int:
        return 2

    def is_game_over(self) -> bool:
        if not self.state.game_over and not self.has_attempts_left():
            self.state.game_over = True
            self.state.won = False
            self.status = GameStatus.LOST
        return self.state.game_over

    def get_result(self) -> GameResult:
        return GameResult(
            game_id=self.game_id,
            game_type="wordle",
            status=self.status,
            moves=self.moves,
            total_moves=len(self.moves),
            won=self.state.won,
            target=self.target_word,
            metadata={
                "word_length": self.word_length,
                "language": self.language,
            },
        )
