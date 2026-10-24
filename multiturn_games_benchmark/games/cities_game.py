"""Cities game implementation."""

import random
import re
import unicodedata
from dataclasses import dataclass
from ..prompts import load_prompt
from typing import Any, Dict, List, Optional, Set, Tuple

from ..base_game import BaseGame, GameMove, GameResult, GameStatus
from ..base_judge import BaseJudge
from ..constants import CitiesPromptsGenerator, CitiesTextConstants
from .reasoning_utils import extract_reasoning_and_answer, strip_reasoning_for_context


def _to_ascii_safe(text: str) -> str:
    result = []
    for char in text:
        if re.match(r"[а-яА-ЯёЁ]", char):
            result.append(char)
            continue
        normalized = unicodedata.normalize("NFKD", char)
        result.append("".join(c for c in normalized if not unicodedata.combining(c)))
    return "".join(result)


def _clean_city_name(city: str) -> str:
    ascii_text = _to_ascii_safe(city)
    text_with_spaces = re.sub(r"[^a-zA-Zа-яА-ЯёЁ]", " ", ascii_text)
    return re.sub(r"\s+", " ", text_with_spaces).strip()


@dataclass
class CitiesState:
    used_cities: Set[str]
    current_letter: Optional[str]
    game_over: bool
    won: bool
    last_opponent_city: Optional[str] = None


class CitiesJudge(BaseJudge):
    """Script-based judge for Cities game."""

    def __init__(self, cities_list: List[str], allowed_cities_list: List[str]):
        super().__init__()
        self.cities_normalized = {self._normalize_city(city): city for city in cities_list}
        self.cities_queue = allowed_cities_list.copy()

    def _normalize_city(self, city: str) -> str:
        city_norm = _clean_city_name(city)
        city_norm = (
            city_norm.lower()
            .replace("‘", " ")
            .replace("-", " ")
            .replace(",", " ")
            .replace(".", " ")
            .replace("ё", "е")
            .strip()
        )

        if city_norm.endswith(" city"):
            city_norm = city_norm[:-5].strip()
        elif city_norm == "city":
            city_norm = "city"
        return city_norm

    def _get_last_letter(self, city: str) -> str:
        city = self._normalize_city(city)
        if not city:
            return ""

        if city[-1] in ["ь", "ъ", "ы"] and len(city) > 1:
            return city[-2]
        return city[-1]

    def find_next_city(self, required_letter: str, used_cities: Set[str]) -> Optional[str]:
        if not required_letter:
            return None

        rng = random.Random("|".join(sorted(str(item) for item in used_cities)))
        queue = self.cities_queue.copy()
        rng.shuffle(queue)

        required_letter = required_letter.lower()
        for city in queue:
            city_normalized = self._normalize_city(city)
            if city_normalized in used_cities:
                continue
            if city_normalized and city_normalized[0] == required_letter:
                return city
        return None

    def evaluate_player_move(self, game_state: Dict[str, Any], player_input: str) -> Tuple[bool, str]:
        required_letter = game_state.get("current_letter")
        used_cities = game_state.get("used_cities", set())
        city = self._normalize_city(player_input)

        if not city:
            return False, "invalid_format"
        if city not in self.cities_normalized:
            return False, "not_found"
        if city in used_cities:
            return False, "repeated"
        if required_letter and city[0] != required_letter.lower():
            return False, "wrong_letter"
        return True, "valid"


class CitiesGame(BaseGame):
    """Cities game implementation."""

    def __init__(
        self,
        game_id: str,
        cities_list: List[str],
        allowed_cities_list: List[str],
        start_city: str,
        max_attempts: int = 50,
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

        if not cities_list:
            raise ValueError("Cities list is empty")

        self.cities_list = cities_list
        self.allowed_cities_list = allowed_cities_list
        self.start_city = start_city
        self.enable_reasoning = enable_reasoning
        self.language = language

        self.judge = CitiesJudge(cities_list, allowed_cities_list)
        self.constants = CitiesTextConstants(language=language)
        self.prompt_generator = CitiesPromptsGenerator(language=language, cot=enable_reasoning)

        self.prompt_template = load_prompt("word_chain", "prompt", language)

        self.state = CitiesState(
            used_cities={self.judge._normalize_city(start_city)},
            current_letter=self.judge._get_last_letter(start_city),
            game_over=False,
            won=False,
        )

    def get_system_prompt(self) -> str:
        return self.prompt_template.format(
            REASONING_INSTRUCTION=self.prompt_generator.reasoning_instruction_prompt(),
        )

    def get_initial_user_message(self) -> str:
        return self.prompt_generator.init_game_prompt(self.start_city)

    def _extract_city_guess(self, response: str) -> str:
        match = re.search(fr"{self.constants.answer_key_word}:\s*(.+)", response, re.IGNORECASE)
        if match:
            guess = match.group(1).strip()
        else:
            guess = response.strip()
            if not re.fullmatch(fr"[{self.constants.regexp_alphabet}\s\-\'`\".]+", guess):
                return ""

        if not guess:
            return ""
        guess = guess.splitlines()[0].strip().strip("\"'`")
        if not re.search(fr"[{self.constants.regexp_alphabet}]", guess):
            return ""
        return re.sub(r"\s+", " ", guess)

    def _invalid_move_feedback(self, guess: str, error_type: str) -> str:
        if error_type == "not_found":
            return self.prompt_generator.city_not_found_feedback_prompt(guess)
        if error_type == "repeated":
            return self.prompt_generator.repeated_city_feedback_prompt(guess)
        if error_type == "wrong_letter":
            return self.prompt_generator.wrong_letter_feedback_prompt(guess, self.state.current_letter or "")
        return self.prompt_generator.wrong_format_answer_feedback_prompt()

    def process_player_move(self, player_input: str) -> GameMove:
        move_number = self.get_move_count() + 1
        player_input = player_input.strip()

        if self.enable_reasoning:
            reasoning, answer = extract_reasoning_and_answer(player_input)
        else:
            reasoning = ""
            answer = player_input

        guess = self._extract_city_guess(answer)
        player_answer = strip_reasoning_for_context(player_input) if self.enable_reasoning else answer

        metadata = {
            "reasoning": reasoning,
            "guess": guess,
            "current_letter": self.state.current_letter,
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

        is_valid, verdict = self.judge.evaluate_player_move(
            {
                "used_cities": self.state.used_cities,
                "current_letter": self.state.current_letter,
            },
            guess,
        )

        metadata["verdict"] = verdict
        if not is_valid:
            self.state.game_over = True
            self.state.won = False
            self.status = GameStatus.LOST
            move = GameMove(
                move_number=move_number,
                player_input=player_input,
                player_answer=player_answer,
                feedback=self._invalid_move_feedback(guess, verdict),
                is_valid=False,
                metadata=metadata,
            )
            self.moves.append(move)
            return move

        self.state.used_cities.add(self.judge._normalize_city(guess))

        next_letter = self.judge._get_last_letter(guess)
        judge_city = self.judge.find_next_city(next_letter, self.state.used_cities)
        metadata["player_next_letter"] = next_letter

        if judge_city is None:
            self.state.game_over = True
            self.state.won = True
            self.status = GameStatus.WON
            feedback = self.prompt_generator.no_available_city_feedback_prompt(guess)
        else:
            self.state.last_opponent_city = judge_city
            self.state.used_cities.add(self.judge._normalize_city(judge_city))
            self.state.current_letter = self.judge._get_last_letter(judge_city)
            metadata["opponent_city"] = judge_city
            metadata["next_letter"] = self.state.current_letter
            feedback = self.prompt_generator.next_city_feedback_prompt(
                judge_city, self.state.current_letter or ""
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

        if not self.has_attempts_left() and not self.state.game_over:
            self.state.game_over = True
            self.state.won = True
            self.status = GameStatus.WON

        return move

    def should_retry_response(self, response: str) -> bool:
        if self.enable_reasoning:
            _, answer = extract_reasoning_and_answer(response)
        else:
            answer = response
        guess = self._extract_city_guess(answer)
        return not bool(guess)

    def get_max_format_retries(self) -> int:
        return 2

    def is_game_over(self) -> bool:
        if not self.state.game_over and not self.has_attempts_left():
            self.state.game_over = True
            self.state.won = True
            self.status = GameStatus.WON
        return self.state.game_over

    def get_result(self) -> GameResult:
        return GameResult(
            game_id=self.game_id,
            game_type="cities",
            status=self.status,
            moves=self.moves,
            total_moves=len(self.moves),
            won=self.state.won,
            target=self.start_city,
            metadata={
                "start_city": self.start_city,
                "current_letter": self.state.current_letter,
                "last_opponent_city": self.state.last_opponent_city,
                "total_cities_used": len(self.state.used_cities),
                "used_cities": list(self.state.used_cities),
            },
        )
