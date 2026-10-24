"""Twenty Features Game Implementation"""

import os
import pickle
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path

from ..prompts import load_prompt
from ..base_game import BaseGame, GameMove, GameResult, GameStatus
from ..base_judge import BaseJudge
from ..llm_player import LLMPlayer
from ..constants import COT_REMINDERS
from multiturn_games_benchmark.utils import normalize_string
from dataclasses import dataclass


TWENTY_FEATURES_PROMPTS = {
    'simple': {language: load_prompt("twenty_features", 'simple', language) for language in ("en", "ru")},
    'simple_with_nei': {language: load_prompt("twenty_features", 'simple_with_nei', language) for language in ("en", "ru")},
    'cot': {language: load_prompt("twenty_features", 'cot', language) for language in ("en", "ru")},
    'cot_with_nei': {language: load_prompt("twenty_features", 'cot_with_nei', language) for language in ("en", "ru")},
}


VERIFIER_PROMPTS = {language: load_prompt("twenty_features", "verifier", language) for language in ("en", "ru")}


@dataclass
class Feature:
    name: str
    value: str


class TwentyFeaturesJudge(BaseJudge):
    def __init__(self, verifier_model_config: Dict[str, Any], word_features: dict, language: str):
        self.word_features = word_features
        features = {
            "ru": [
                'Цвет', 'Форма', 'Размер', 'Материал', 'Вес', 'Текстура',
                'Температура-на-ощупь', 'Запах', 'Вкус', 'Прозрачность',
                'Гибкость', 'Твёрдость', 'Подвижность',
                'Количество-частей/компонентов', 'Назначение', 'Происхождение',
                'Живой/неживой', 'Встречаемость', 'Стоимость/ценовая-категория',
                'Опасность-для-человека'
            ],
            "en": [
                'Color', 'Shape', 'Size', 'Material', 'Weight', 'Texture',
                'Temperature-to-touch', 'Smell', 'Taste', 'Transparency',
                'Flexibility', 'Hardness', 'Mobility',
                'Number-of-parts/components', 'Purpose', 'Origin',
                'Living/non-living', 'Occurrence', 'Cost/price-category',
                'Danger-to-human'
            ]
        }
        self.features_order = features[language]

        self.verifier = LLMPlayer(verifier_model_config)
        self.verifier_prompt = VERIFIER_PROMPTS[language]


    def get_next_feature(self, word: str, used_features: list[str]) -> Feature | None:
        for feature_name in self.features_order:
            feature_condition = (
                feature_name not in used_features
                and feature_name in self.word_features.get(word, dict())
            )
            if feature_condition:
                value = self.word_features[word][feature_name]
                return Feature(name=feature_name, value=value)
        return None

    def evaluate_guess(self, word: str, guess: str) -> bool:
        if guess.strip().lower() == word.strip().lower():
            return True
        
        prompt = self.verifier_prompt.format(
            target_word=word,
            player_answer=guess
        )
        self.verifier.initialize_player_with_prompts(
            system_prompt="",
            initial_user_message=prompt
        )
        verdict = self.verifier.get_move()

        return "true" in verdict


    def evaluate_player_move(
        self, game_state: dict, player_input: str
    ) -> tuple[bool, str]:
        target_word = game_state["target_word"]
        used_features = game_state["used_features"]

        normalized_input = normalize_string(player_input).strip().lower()

        if self.evaluate_guess(target_word, normalized_input):
            return True, "correct"

        next_feature = self.get_next_feature(target_word, used_features)
        if next_feature:
            feedback = f"{next_feature.name}: {next_feature.value}"
            used_features.append(next_feature.name)
            return True, feedback
        else:
            return False, "no_more_features"


class TwentyFeaturesGame(BaseGame):
    def __init__(
        self,
        game_id: str,
        verifier_model_config: Dict[str, Any],
        word_features: dict,
        target_word: str,
        max_attempts: int = 20,
        is_CoT: bool = False,
        enable_nei: bool = True,
        language: str = 'ru'
    ):
        super().__init__(game_id, max_attempts)

        self.word_features = word_features
        self.target_word = target_word
        self.language = language
        self.judge = TwentyFeaturesJudge(verifier_model_config, word_features, language=self.language)
        self.used_features: List[str] = []
        self.is_CoT = is_CoT
        self.enable_nei = enable_nei
        self.guessed = False

        self.system_prompt = self.get_system_prompt()
        # self.initial_prompt = self.get_initial_user_message()

    def _extract_final_answer(self, player_input: str) -> str:
        markers = {
            "ru": "ответ",
            "en": "answer",
        }
        marker = markers[self.language]
        lines = [substr.strip() for substr in player_input.split('\n') if len(substr) > 0]
        last_line = lines[-1] if lines else player_input
        parts = last_line.lower().split(marker)
        if len(parts) > 1:
            return normalize_string(text=parts[-1])
        return normalize_string(last_line)

    def process_player_move(self, player_input: str) -> GameMove:
        move_number = self.get_move_count() + 1
        player_input = player_input.strip()
        final_answer = self._extract_final_answer(player_input)

        game_state = {
            "target_word": self.target_word,
            "used_features": self.used_features.copy()
        }

        is_valid, feedback = self.judge.evaluate_player_move(game_state, final_answer)

        if feedback != "incorrect" and not feedback.startswith("no_more"):
            if ":" in feedback:
                feature_name = feedback.split(":")[0].strip()
                if feature_name not in self.used_features:
                    self.used_features.append(feature_name)

        if not is_valid:
            move = GameMove(
                move_number=move_number,
                player_input=player_input,
                player_answer=final_answer,
                feedback=feedback,
                is_valid=False
            )
            self.moves.append(move)
            return move

        if feedback == "correct":
            self.guessed = True
            self.status = GameStatus.WON
        elif feedback == "no_more_features":
            self.status = GameStatus.LOST

        if self.is_CoT:
            feedback = feedback + '\n' + COT_REMINDERS[self.language]

        move = GameMove(
            move_number=move_number,
            player_input=player_input,
            player_answer=final_answer,
            feedback=feedback,
            is_valid=True
        )
        self.moves.append(move)

        if self.guessed or not self.has_attempts_left():
            self.status = GameStatus.WON if self.guessed else GameStatus.LOST
        return move

    def is_game_over(self) -> bool:
        return self.status in [GameStatus.WON, GameStatus.LOST]

    def get_result(self) -> GameResult:
        return GameResult(
            game_id=self.game_id,
            game_type="twenty_features",
            status=self.status,
            moves=self.moves,
            total_moves=len(self.moves),
            won=(self.status == GameStatus.WON),
            target=self.target_word,
            metadata={
                "used_features_count": len(self.used_features),
                "features_used": self.used_features
            }
        )
    def _get_system_prompt(self) -> str:
        if self.is_CoT:
            if self.enable_nei:
                return TWENTY_FEATURES_PROMPTS["cot_with_nei"][self.language]
            else:
                return TWENTY_FEATURES_PROMPTS["cot"][self.language]
        else:
            if self.enable_nei:
                return TWENTY_FEATURES_PROMPTS["simple_with_nei"][self.language]
            else:
                return TWENTY_FEATURES_PROMPTS["simple"][self.language]

    def get_system_prompt(self) -> str:
        return ""
    
    def get_initial_user_message(self) -> str:
        prompt = self._get_system_prompt()
        first_feature = self.judge.get_next_feature(self.target_word, self.used_features)
        if first_feature:
            self.used_features.append(first_feature.name)
            feature_text = f"{first_feature.name}: {first_feature.value}"
            return f"{prompt}\n\n{feature_text}"
        else:
            return "No features remaining."

