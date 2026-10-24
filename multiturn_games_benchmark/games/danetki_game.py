"""Lateral-thinking puzzle (данетка) game implementation."""

import os
import re
from dataclasses import dataclass
from ..prompts import load_prompt
from typing import Any, Callable, Dict, Optional, Tuple

import jinja2

from ..base_game import BaseGame, GameMove, GameResult, GameStatus
from ..base_judge import BaseJudge
from ..constants import DanetkiPromptsGenerator, DanetkiTextConstants
from ..llm_player import LLMPlayer


def _load_danetki_template(name: str, language: str) -> str:
    return load_prompt("situation_puzzles", name, language)


def _extract_content_by_keyword(text: str, keyword: str) -> str:
    match = re.search(fr".*{keyword}:\s*(.+)", text, re.IGNORECASE | re.DOTALL)
    if not match:
        return ""
    content = match.group(1).strip()
    if not content:
        return ""
    return content.splitlines()[0].strip().strip("\"'`")


class DanetkaJudge(BaseJudge):
    """LLM-based judge for Danetki."""

    _YN_RESPONSES = {
        "ru": {
            "yes": "Да",
            "no": "Нет",
            "irrelevant": "Неважно",
            "ambiguous": "На вопрос нельзя ответить однозначно да/нет",
            "only_one": "Задай только один вопрос",
            "clarify": "Уточни вопрос. Помни о формате.",
        },
        "en": {
            "yes": "Yes",
            "no": "No",
            "irrelevant": "It doesn't matter",
            "ambiguous": "The question cannot be answered unambiguously with yes/no",
            "only_one": "Ask only one question",
            "clarify": "Please clarify the question. Remember the format.",
        },
    }

    def __init__(self, judge_model_config: Dict[str, Any], language: str = "ru"):
        self.language = language
        self.constants = DanetkiTextConstants(language=language)
        self.verifier = LLMPlayer(judge_model_config)
        self.yn_prompt_template = _load_danetki_template("judge_yn_question", language)
        self.final_answer_template = _load_danetki_template("judge_final_answer", language)

    def evaluate_player_move(self, game_state: Dict[str, Any], player_input: str) -> Tuple[bool, str]:
        raise NotImplementedError(
            "DanetkaJudge requires explicit move type. Use answer_yn_question() or check_final_answer()."
        )

    def _extract_answer_content(self, text: str) -> str:
        return _extract_content_by_keyword(text, self.constants.answer_key_word)

    def _normalize_yn_answer(self, raw_answer: str) -> str:
        answer_text = self._extract_answer_content(raw_answer)
        lower = (answer_text or raw_answer).lower()
        responses = self._YN_RESPONSES.get(self.language, self._YN_RESPONSES["en"])

        if self.language == "ru":
            if "однознач" in lower:
                return responses["ambiguous"]
            if "только один" in lower or "только один вопрос" in lower:
                return responses["only_one"]
            if "неваж" in lower:
                return responses["irrelevant"]
            if re.search(r"\bда\b", lower):
                return responses["yes"]
            if re.search(r"\bнет\b", lower):
                return responses["no"]
        else:
            if "cannot be answered" in lower or "unambiguous" in lower:
                return responses["ambiguous"]
            if "only one" in lower:
                return responses["only_one"]
            if "doesn't matter" in lower or "does not matter" in lower or "irrelevant" in lower:
                return responses["irrelevant"]
            if re.search(r"\byes\b", lower):
                return responses["yes"]
            if re.search(r"\bno\b", lower):
                return responses["no"]

        return responses["clarify"]
    
    def _judge_call(self, prompt: str) -> str:
        self.verifier.initialize_player_with_prompts(
            system_prompt="",
            initial_user_message=prompt
        )
        answer = self.verifier.get_move()

        return answer

    def answer_yn_question(self, game_state: Dict[str, Any], question: str, dialogue_history: str) -> str:
        prompt = self.yn_prompt_template.format(
            setup=game_state["setup"],
            solution=game_state["solution"],
            question=question.strip(),
            dialogue_history=dialogue_history,
        )
        raw_answer = self._judge_call(prompt)
        return self._normalize_yn_answer(raw_answer)

    def check_final_answer(self, game_state: Dict[str, Any], guess: str, dialogue_history: str) -> bool:
        template = jinja2.Template(self.final_answer_template)
        prompt = template.render(
            setup=game_state["setup"],
            solution=game_state["solution"],
            guess=guess,
            facts=game_state["facts"],
            dialogue_history=dialogue_history,
        )
        raw_answer = self._judge_call(prompt)
        verdict = self._extract_answer_content(raw_answer)
        return "true" in verdict.lower()


@dataclass
class DanetkaState:
    game_over: bool
    won: bool
    final_guess: str = ""


class DanetkaGame(BaseGame):
    """Danetka (lateral thinking puzzle) game implementation."""

    def __init__(
        self,
        game_id: str,
        puzzle: Dict[str, Any],
        max_attempts: int = 20,
        enable_reasoning: bool = False,
        language: str = "ru",
        judge_model_config: Optional[Dict[str, Any]] = None,
        is_CoT: Optional[bool] = None,
        lang: Optional[str] = None,
    ):
        super().__init__(game_id, max_attempts)

        if is_CoT is not None:
            enable_reasoning = is_CoT
        if lang is not None:
            language = lang

        self.puzzle_setup = puzzle["setup"]
        self.puzzle_solution = puzzle["solution"]
        self.puzzle_facts = puzzle["key_fact"]
        self.enable_reasoning = enable_reasoning
        self.language = language

        assert judge_model_config is not None
    
        self.constants = DanetkiTextConstants(language=language)
        self.prompt_generator = DanetkiPromptsGenerator(language=language, cot=enable_reasoning)
        self.judge = DanetkaJudge(judge_model_config=judge_model_config, language=language)
        self.prompt_template = _load_danetki_template("prompt", language)
        self.state = DanetkaState(game_over=False, won=False)

    def get_system_prompt(self) -> str:
        return self.prompt_template.format(
            REASONING_INSTRUCTION=self.prompt_generator.reasoning_instruction_prompt(),
        )

    def _moves_left_prompt(self, moves_left: int) -> str:
        return self.prompt_generator.moves_left_prompt(max(moves_left, 0))

    def _add_moves_left_to_feedback(self, feedback: str, moves_left: int) -> str:
        return f"{feedback}\n\n{self._moves_left_prompt(moves_left)}"

    def get_initial_user_message(self) -> str:
        prompt = self.prompt_generator.init_game_prompt(self.puzzle_setup)
        return f"{prompt}\n\n{self._moves_left_prompt(self.max_attempts - self.get_move_count())}"

    def _extract_reasoning(self, response: str) -> str:
        if not self.enable_reasoning:
            return ""

        match = re.search(
            fr"{self.constants.reasoning_key_word}:\s*(.*?)\s*(?:{self.constants.question_key_word}|{self.constants.answer_key_word}):",
            response,
            re.IGNORECASE | re.DOTALL,
        )
        if match:
            return match.group(1).strip()
        return ""

    def _extract_question(self, response: str) -> str:
        question = _extract_content_by_keyword(response, self.constants.question_key_word)
        if question:
            return re.sub(r"\s+", " ", question)

        stripped = response.strip()
        if stripped.endswith("?"):
            return re.sub(r"\s+", " ", stripped)
        return ""

    def _extract_final_answer(self, response: str) -> str:
        answer = _extract_content_by_keyword(response, self.constants.answer_key_word)
        if answer:
            return re.sub(r"\s+", " ", answer)
        return ""

    def _parse_player_turn(self, response: str) -> Tuple[str, str, str]:
        question_marker = re.search(fr"{self.constants.question_key_word}:", response, re.IGNORECASE)
        answer_marker = re.search(fr"{self.constants.answer_key_word}:", response, re.IGNORECASE)

        if question_marker and answer_marker:
            return "", "", ""
        if question_marker:
            question = self._extract_question(response)
            return "question", question, f"{self.constants.question_key_word}: {question}" if question else ""
        if answer_marker:
            answer = self._extract_final_answer(response)
            return "answer", answer, f"{self.constants.answer_key_word}: {answer}" if answer else ""

        question = self._extract_question(response)
        if question:
            return "question", question, f"{self.constants.question_key_word}: {question}"
        return "", "", ""

    def _build_dialogue_history(self) -> str:
        if not self.moves:
            return self.prompt_generator.no_questions_yet_prompt()

        lines = []
        answer_prefix = self.prompt_generator.dialogue_history_answer_prefix()
        for move in self.moves:
            lines.append(move.player_answer)
            lines.append(f"{answer_prefix} {move.feedback}")
        return "\n".join(lines)

    def process_player_move(self, player_input: str) -> GameMove:
        move_number = self.get_move_count() + 1
        player_input = player_input.strip()

        move_type, payload, player_answer = self._parse_player_turn(player_input)
        reasoning = self._extract_reasoning(player_input)
        metadata = {
            "reasoning": reasoning,
            "move_type": move_type,
            "payload": payload,
        }

        if not move_type or not payload:
            feedback = self._add_moves_left_to_feedback(
                self.prompt_generator.wrong_format_answer_feedback_prompt(),
                self.max_attempts - move_number,
            )
            move = GameMove(
                move_number=move_number,
                player_input=player_input,
                player_answer=player_input,
                feedback=feedback,
                is_valid=False,
                metadata=metadata,
            )
            self.moves.append(move)
            return move

        dialogue_history = self._build_dialogue_history()
        game_state = {
            "setup": self.puzzle_setup,
            "solution": self.puzzle_solution,
            "facts": self.puzzle_facts,
        }

        if move_type == "question":
            feedback = self.judge.answer_yn_question(game_state, payload, dialogue_history)
            feedback = self.prompt_generator.judge_clarification_feedback_prompt(feedback)
        else:
            is_correct = self.judge.check_final_answer(game_state, payload, dialogue_history)
            self.state.final_guess = payload
            feedback = self.prompt_generator.final_answer_feedback_prompt(is_correct)
            metadata["is_correct_guess"] = is_correct
            if is_correct:
                self.state.game_over = True
                self.state.won = True
                self.status = GameStatus.WON

        feedback = self._add_moves_left_to_feedback(feedback, self.max_attempts - move_number)

        move = GameMove(
            move_number=move_number,
            player_input=player_input,
            player_answer=player_answer,
            feedback=feedback,
            is_valid=True,
            metadata=metadata,
        )
        self.moves.append(move)

        if not self.state.game_over and not self.has_attempts_left():
            self.state.game_over = True
            self.state.won = False
            self.status = GameStatus.LOST

        return move

    def should_retry_response(self, response: str) -> bool:
        move_type, payload, _ = self._parse_player_turn(response)
        return not bool(move_type and payload)

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
            game_type="danetka",
            status=self.status,
            moves=self.moves,
            total_moves=len(self.moves),
            won=self.state.won,
            target=self.puzzle_solution,
            metadata={
                "setup": self.puzzle_setup,
                "facts": self.puzzle_facts,
                "final_guess": self.state.final_guess,
                "language": self.language,
            },
        )
