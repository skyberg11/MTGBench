"""
Alias Game Implementation with LLM-as-a-judge
"""

import os
import pickle
import re
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path

from ..prompts import load_prompt
from ..base_game import BaseGame, GameMove, GameResult, GameStatus
from ..llm_player import LLMPlayer
from ..constants import COT_REMINDERS
from multiturn_games_benchmark.utils import normalize_string
from dataclasses import dataclass


ALIAS_PROMPTS = {
    'guesser': {language: load_prompt("alias", 'guesser', language) for language in ("en", "ru")},
    'guesser_cot': {language: load_prompt("alias", 'guesser_cot', language) for language in ("en", "ru")},
    'verifier': {language: load_prompt("alias", 'verifier', language) for language in ("en", "ru")},
    'verifier_bio': {language: load_prompt("alias", 'verifier_bio', language) for language in ("en", "ru")},
}


def clean_wiki_article(text: str) -> str:
    pattern = r'\n\s*(См\. также|Примечания|Ссылки|See also|References|External links)\b.*'
    return re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL).strip()


def load_bio(bio_path: str) -> Optional[str]:
    ### Do not run game if bio is not loaded
    # if not os.path.exists(bio_path):
    #     return None
    with open(bio_path, 'rb') as f:
        try:
            return pickle.load(f)
        except Exception:
            return None
        
def extract_answer(player_input: str, language: str) -> str:
    markers = {
        "ru": "ответ",
        "en": "answer",
    }
    marker = markers[language]
    lines = [substr.strip() for substr in player_input.split('\n') if len(substr) > 0]
    last_line = lines[-1] if lines else player_input

    matches = list(re.finditer(fr'\b{marker}\b', last_line, flags=re.IGNORECASE))

    if not matches:
        return last_line
    return last_line[matches[-1].end():].strip(" :-—\n\t")


class AliasVerifier:
    def __init__(self, verifier_model_config: Dict[str, Any], language: str = 'ru'):
        self.verifier = LLMPlayer(verifier_model_config)
        self.language = language
        self.yes = {"en": "yes", "ru": "да"}
        self.no = {"en": "no", "ru": "нет"}
        self.error = {"en": "error", "ru": "ошибка"}

    def _verify_name_match(self, model_answer: str, target_name: str) -> str:
        prompt = ALIAS_PROMPTS['verifier'][self.language].format(
            target_person=target_name,
            model_answer=model_answer
        )
        self.verifier.initialize_player_with_prompts(
            system_prompt="",
            initial_user_message=prompt
        )
        response = self.verifier.get_move()
        norm_response = normalize_string(response)

        if self.error[self.language] in norm_response:
            return self.error[self.language]
        return self.yes[self.language] if self.yes[self.language] in norm_response else self.no[self.language]

    def _verify_fact_in_bio(self, question: str, bio_text: str, target_name: str) -> str:
        if not bio_text:
            return self.no[self.language]
        bio_clean = clean_wiki_article(bio_text)
        prompt = ALIAS_PROMPTS['verifier_bio'][self.language].format(
            question=question,
            target_name=target_name,
            bio_text=bio_clean
        )
        self.verifier.initialize_player_with_prompts(
            system_prompt="",
            initial_user_message=prompt
        )
        response = self.verifier.get_move()
        # print(response)
        # judge_answer = extract_answer(response, self.language)
        judge_answer = response
        return self.yes[self.language] if self.yes[self.language] in normalize_string(judge_answer) else self.no[self.language]

    def evaluate_question(self, question: str, bio_path: str, target_name: str) -> str:
        bio = load_bio(bio_path)
        return self._verify_fact_in_bio(question, bio, target_name)

    def evaluate_guess(self, guess: str, target_name: str) -> bool:
        guess = guess.strip(' !?')
        return self._verify_name_match(guess, target_name)


class AliasGame(BaseGame):
    def __init__(
        self,
        game_id: str,
        target_person: str,
        bio_path: str,
        verifier_model_config: Dict[str, Any],
        max_attempts: int = 30,
        is_CoT: bool = False,
        language: str = "ru"
    ):
        super().__init__(game_id, max_attempts)
        self.language = language
        self.target_person = target_person
        self.bio_path = bio_path
        self.judge = AliasVerifier(verifier_model_config, self.language)
        self.is_CoT = is_CoT
        self.system_prompt = self._get_system_prompt()
        self.initial_prompt = self._get_initial_prompt()
        self.guessed = False
        self.target_person_len = len(target_person.split(' '))

    def _get_system_prompt(self) -> str:
        if self.is_CoT:
            return ALIAS_PROMPTS["guesser_cot"][self.language]
        else:
            return ALIAS_PROMPTS["guesser"][self.language]

    def _get_initial_prompt(self) -> str:
        return self.system_prompt

    def process_player_move(self, player_input: str) -> GameMove:
        move_number = self.get_move_count() + 1
        player_input = player_input.strip()
        extracted_answer = extract_answer(player_input, self.language)

        ### Get only N last words of extracted answer (N = num words in target person name) in case of long extracted answer
        ### Not good for cases when extracted_answer = 'Пушкин Александр Сергеевич' and target_answer = 'Александр Пушкин', 
        ### so the extracted_answer will be stripped to 'Александр Сергеевич' and lose the most important part (surname).
        # extracted_answer_split = extracted_answer.split(' ')
        # if len(extracted_answer_split) > len(self.target_person_len):
        #     extracted_answer_split = extracted_answer_split[-len(self.target_person):]
        # extracted_answer = ' '.join(extracted_answer_split)
        
        if normalize_string(text=extracted_answer) == normalize_string(text=self.target_person):
            self.guessed = True
            self.status = GameStatus.WON
            feedback = self.judge.yes[self.language]
            is_valid = True
        else:
            guess_verdict = self.judge.evaluate_guess(extracted_answer, self.target_person)
            if guess_verdict == self.judge.yes[self.language]:
                self.guessed = True
                self.status = GameStatus.WON
                feedback = self.judge.yes[self.language]
                is_valid = True
            elif guess_verdict == self.judge.no[self.language]:
                feedback = guess_verdict
                is_valid = True
            else:
                print()
                print('---> Redirect to bio judge')
                feedback = self.judge.evaluate_question(extracted_answer, self.bio_path, self.target_person)

                # infinite loop protection when evaluate_guess says "no", but the answer is correct person
                if feedback == self.judge.yes[self.language] and extracted_answer[-1] == '!':
                    self.guessed = True
                    self.status = GameStatus.WON
                    feedback = self.judge.yes[self.language]
                    is_valid = True
                else:
                    is_valid = True

        if self.is_CoT:
            feedback = feedback + '\n' + COT_REMINDERS[self.language]

        move = GameMove(
            move_number=move_number,
            player_input=player_input,
            player_answer=extracted_answer,
            feedback=feedback,
            is_valid=is_valid
        )
        self.moves.append(move)
        if self.guessed or not self.has_attempts_left():
            self.status = GameStatus.WON if self.guessed else GameStatus.LOST
        return move

    def is_game_over(self) -> bool:
        return self.status in [GameStatus.WON, GameStatus.LOST]


    def get_result(self) -> GameResult:
        print()
        print(f'JUDGE COST: {self.judge.verifier.price}')
        print(f'JUDGE TOKENS: prompt {self.judge.verifier.prompt_tokens} / completion {self.judge.verifier.completion_tokens}')
        return GameResult(
            game_id=self.game_id,
            game_type="alias",
            status=self.status,
            moves=self.moves,
            total_moves=len(self.moves),
            won=self.guessed,
            target=self.target_person,
            metadata={
                "bio_path": self.bio_path
            }
        )
    
    def get_system_prompt(self) -> str:
        return ""
    
    def get_initial_user_message(self) -> str:
        return self.system_prompt

