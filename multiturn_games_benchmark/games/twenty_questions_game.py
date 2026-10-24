import random
import re
from dataclasses import dataclass
from typing import Set, List, Tuple, Dict
from ..prompts import load_prompt

from ..base_game import BaseGame, GameMove, GameResult, GameStatus
from .reasoning_utils import extract_reasoning_and_answer, strip_reasoning_for_context
from ..constants import TwentyQuestionsTextConstants, TwentyQuestionsPromptsGenerator


@dataclass
class TwentyQuestionsState:
    secret_word: str
    remaining_words: Set[str]
    qa_history: List[Tuple[str, str]]
    contradiction_found: bool
    contradiction_reason: str
    turns_used: int
    word_guessed: bool = False
    guessed_word: str = ""
    consecutive_invalid_moves: int = 0
    format_failure: bool = False


class TwentyQuestionsGame(BaseGame):

    def __init__(
            self,
            game_id: str,
            word_pool: List[str],
            word_attributes: Dict[str, List[str]],
            max_attempts: int = 20,
            enable_reasoning: bool = False,
            language: str = "ru",
            fixed_secret_word: str = None
    ):
        super().__init__(game_id, max_attempts)

        self.word_pool = word_pool
        self.word_attributes = word_attributes
        self.enable_reasoning = enable_reasoning
        self.language = language

        if fixed_secret_word:
            if fixed_secret_word not in word_pool:
                raise ValueError(f"Fixed secret word '{fixed_secret_word}' not in word pool")
            self.secret_word = fixed_secret_word
        else:
            self.secret_word = random.choice(word_pool)

        self.state = TwentyQuestionsState(
            secret_word=self.secret_word,
            remaining_words=set(word_pool),
            qa_history=[],
            contradiction_found=False,
            contradiction_reason="",
            turns_used=0
        )

        self.prompt_template = load_prompt("twenty_questions", "prompt", language)

        self.current_question = None
        self.constants = TwentyQuestionsTextConstants(language=self.language)
        self.prompt_generator = TwentyQuestionsPromptsGenerator(language=self.language, cot=self.enable_reasoning)

    def _is_word_question(self, question: str) -> bool:
        if question.lower().startswith(self.constants.word_guess_prompt_prefix.lower()):
            return True
        return False

    def _is_attribute_question(self, question: str) -> bool:
        if question.lower().startswith(self.constants.attribute_question_prompt_prefix.lower()):
            return True
        return False

    def _format_word_pool(self) -> str:
        return ", ".join(sorted(self.word_pool))

    def _format_word_attributes(self) -> str:
        lines = []
        for word in sorted(self.word_pool):
            attrs = ", ".join(self.word_attributes.get(word, []))
            lines.append(f"  {word}: {attrs}")
        return "\n".join(lines)

    def get_system_prompt(self) -> str:
        prompt = self.prompt_template.format(
            WORD_POOL=self._format_word_pool(),
            WORD_ATTRIBUTES=self._format_word_attributes(),
            REASONING_INSTRUCTION=self.prompt_generator.reasoning_instruction_prompt(),
            SECRET_WORD=self.secret_word
        )

        return prompt

    def get_initial_user_message(self) -> str:
        return self.prompt_generator.init_game_prompt()

    def _generate_next_question(self) -> str:
        """
        Generate the next question to ask.

        Probabilities:
        - 5%: Spontaneous word guess
        - 15%: Ask about attribute belonging to ALL remaining words (expect "yes")
        - 20%: Ask about attribute belonging ONLY to excluded words (expect "no")
        - 15%: Ask about a random attribute (adds question diversity)
        - 45%: Ask about attribute that splits remaining words ~50/50 (binary search)
        """

        if len(self.state.remaining_words) == 1:
            word = list(self.state.remaining_words)[0]
            return self.prompt_generator.word_guess_prompt(word)

        attribute_counts = {}
        for word in self.state.remaining_words:
            for attr in self.word_attributes.get(word, []):
                if attr not in attribute_counts:
                    attribute_counts[attr] = set()
                attribute_counts[attr].add(word)

        strategy_roll = random.random()

        if strategy_roll < 0.05:
            return self._make_word_guess()

        if strategy_roll < 0.20:
            common_question = self._generate_common_attribute_question(attribute_counts)
            if common_question:
                return common_question
            return self._generate_random_attribute_question(attribute_counts)

        if strategy_roll < 0.40:
            return self._generate_exclusion_question(attribute_counts)

        if strategy_roll < 0.55:
            return self._generate_random_attribute_question(attribute_counts)

        return self._generate_splitting_question(attribute_counts)

    def _make_word_guess(self) -> str:
        """
        Make a spontaneous word guess.

        30% chance of guessing an already-excluded word (to test consistency).
        """
        remaining = self.state.remaining_words
        excluded_words = set(self.word_pool) - remaining

        if random.random() < 0.30 and excluded_words:
            guessed_word = random.choice(list(excluded_words))
        elif remaining:
            guessed_word = random.choice(list(remaining))
        else:
            guessed_word = random.choice(self.word_pool)

        return self.prompt_generator.word_guess_prompt(guessed_word)

    def _generate_random_attribute_question(self, attribute_counts: Dict[str, Set[str]]) -> str:
        """Pick a random attribute from those present in remaining words."""
        if attribute_counts:
            attr = random.choice(list(attribute_counts.keys()))
            return self.prompt_generator.attribute_question_prompt(attr)
        return self.constants.confirm_word_prompt

    def _generate_splitting_question(self, attribute_counts: Dict[str, Set[str]]) -> str:
        num_remaining = len(self.state.remaining_words)
        target_split = num_remaining / 2

        best_attribute = None
        best_diff = float('inf')

        for attr, words_with_attr in attribute_counts.items():
            count = len(words_with_attr)
            diff = abs(count - target_split)

            if diff < best_diff:
                best_diff = diff
                best_attribute = attr
        if best_attribute:
            return self.prompt_generator.attribute_question_prompt(best_attribute)
        else:
            if attribute_counts:
                attr = random.choice(list(attribute_counts.keys()))
                return self.prompt_generator.attribute_question_prompt(attr)
            else:
                return self.constants.confirm_word_prompt

    def _generate_common_attribute_question(self, attribute_counts: Dict[str, Set[str]]) -> str:
        """Find attributes common to ALL remaining words (expect 'yes' answer)."""
        remaining_count = len(self.state.remaining_words)
        common_attrs = [
            attr for attr, words in attribute_counts.items()
            if len(words) == remaining_count
        ]
        if common_attrs:
            attr = random.choice(common_attrs)
            return self.prompt_generator.attribute_question_prompt(attr)
        return ""

    def _generate_exclusion_question(self, attribute_counts: Dict[str, Set[str]]) -> str:
        all_attributes = set()
        for word in self.word_pool:
            all_attributes.update(self.word_attributes.get(word, []))

        remaining_attributes = set(attribute_counts.keys())
        excluded_attributes = all_attributes - remaining_attributes
        if excluded_attributes:
            attr = random.choice(list(excluded_attributes))
            return self.prompt_generator.attribute_question_prompt(attr)
        else:
            return self._generate_random_attribute_question(attribute_counts)

    def _extract_yes_no(self, response: str) -> str:
        matches = re.findall(fr'{self.constants.answer_key_word}:\s*(.+)', response, re.IGNORECASE)
        if matches:
            answer_text = matches[-1].strip().lower()
        else:
            answer_text = response.strip().lower()

        if answer_text.startswith(self.constants.yes_answer):
            return 'yes'
        elif answer_text.startswith(self.constants.no_answer):
            return 'no'

        return ''

    def _extract_attribute_or_word_from_question(self, question: str) -> str:
        match = re.search(fr"{self.constants.attribute_word}\s+['\"](.+?)['\"]", question, re.IGNORECASE)
        if match:
            return match.group(1)

        match = re.search(fr"{self.constants.attribute_word}\s+«(.+?)»", question, re.IGNORECASE)
        if match:
            return match.group(1)

        match = re.search(fr"{self.constants.word_word}\s+['\"](.+?)['\"]", question, re.IGNORECASE)
        if match:
            return match.group(1)

        return ''

    def _update_remaining_words(self, question: str, answer: str) -> None:
        attribute_word = self._extract_attribute_or_word_from_question(question)

        if not attribute_word:
            return

        if self._is_word_question(question):
            word = attribute_word
            attribute = None
        else:
            attribute = attribute_word
            word = None

        if self._is_word_question(question):
            if answer == 'yes':
                if word in self.state.remaining_words:
                    self.state.remaining_words = {word}
                else:
                    self.state.remaining_words = set()
            else:
                self.state.remaining_words.discard(word)
            return

        if answer == 'yes':
            new_remaining = set()
            for word in self.state.remaining_words:
                word_attrs = self.word_attributes[word]
                if attribute in word_attrs:
                    new_remaining.add(word)
            self.state.remaining_words = new_remaining
        else:
            new_remaining = set()
            for word in self.state.remaining_words:
                word_attrs = self.word_attributes[word]
                if attribute not in word_attrs:
                    new_remaining.add(word)
            self.state.remaining_words = new_remaining

    def process_player_move(self, player_input: str) -> GameMove:
        move_number = self.get_move_count() + 1

        if self.enable_reasoning:
            reasoning, answer = extract_reasoning_and_answer(player_input)
        else:
            reasoning = ""
            answer = player_input

        yes_no_answer = self._extract_yes_no(answer)

        metadata = {
            "reasoning": reasoning,
            "parsed_answer": yes_no_answer,
            "question": self.current_question
        }

        if not yes_no_answer:
            self.state.consecutive_invalid_moves += 1
            if self.state.consecutive_invalid_moves >= 2:
                self.state.format_failure = True
                self.status = GameStatus.LOST
                feedback = self.prompt_generator.wrong_format_answer_feedback_prompt()
            else:
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
            question = self.current_question if self.current_question else f"{self.get_system_prompt()}\n{self.get_initial_user_message()}".strip()
            self.state.qa_history.append((question, move.player_answer))
            return move

        self.state.consecutive_invalid_moves = 0

        if self.current_question:  # Not the first move
            self._update_remaining_words(self.current_question, yes_no_answer)

            if self._is_word_question(self.current_question):
                word = self._extract_attribute_or_word_from_question(self.current_question)
                if yes_no_answer == 'yes':
                    self.state.word_guessed = True
                    self.state.guessed_word = word
                    if self.state.guessed_word == self.secret_word:
                        self.status = GameStatus.WON
                        feedback = self.prompt_generator.correct_secret_word_guess_feedback_prompt(self.secret_word)
                    else:
                        self.state.contradiction_found = True
                        self.state.contradiction_reason = self.prompt_generator.word_guess_yes_contradiction_prompt(
                            self.secret_word, self.state.guessed_word)
                        self.status = GameStatus.LOST
                        feedback = self.prompt_generator.word_guess_yes_contradiction_feedback_prompt(self.secret_word,
                                                                                                      self.state.guessed_word)
                    metadata["remaining_words_count"] = len(self.state.remaining_words)
                    metadata["remaining_words"] = list(self.state.remaining_words).copy()
                    metadata["guessed_word"] = self.state.guessed_word
                else:
                    if word == self.secret_word:
                        self.state.contradiction_found = True
                        self.state.contradiction_reason = self.prompt_generator.word_guess_no_contradiction_prompt(
                            self.secret_word)
                        self.status = GameStatus.LOST
                        feedback = self.prompt_generator.word_guess_no_contradiction_feedback_prompt(self.secret_word)
                    else:
                        feedback = self._process_win_condition_for_num_of_remaining_words(answer, metadata, move_number)
            else:  # Attribute question
                feedback = self._process_win_condition_for_num_of_remaining_words(answer, metadata, move_number)
        else:
            self.current_question = self._generate_next_question()
            self.state.turns_used = sum(1 for m in self.moves if m.is_valid) + 1

            remaining_count = len(self.state.remaining_words)
            feedback = self.prompt_generator.no_contradiction_feedback_prompt(remaining_count, self.current_question)
            metadata["remaining_words_count"] = remaining_count
            metadata["remaining_words"] = list(self.state.remaining_words).copy()
            metadata["next_question"] = self.current_question

        move = GameMove(
            move_number=move_number,
            player_input=player_input,
            player_answer=f"{self.constants.answer_key_word}: {strip_reasoning_for_context(player_input)}" if self.enable_reasoning else answer,
            feedback=feedback,
            is_valid=True,
            metadata=metadata
        )
        self.moves.append(move)

        question = self.current_question if self.current_question else f"{self.get_system_prompt()}\n{self.get_initial_user_message()}".strip()
        self.state.qa_history.append((question, move.player_answer))

        return move

    def _process_win_condition_for_num_of_remaining_words(self, answer: str, metadata: dict[str, any],
                                                          move_number: int) -> str:
        if self.secret_word not in self.state.remaining_words:
            self.state.contradiction_found = True
            self.state.contradiction_reason = self.prompt_generator.secret_word_excluded_contradiction_prompt(
                self.secret_word, self.current_question, answer)
            self.status = GameStatus.LOST
            metadata["remaining_words_count"] = len(self.state.remaining_words)
            metadata["remaining_words"] = list(self.state.remaining_words).copy()
            return self.prompt_generator.secret_word_excluded_feedback_prompt(
                self.secret_word, self.current_question, answer)

        if len(self.state.remaining_words) == 0:
            self.state.contradiction_found = True
            self.state.contradiction_reason = self.prompt_generator.no_more_words_left_contradiction_prompt(
                self.current_question, answer)
            self.status = GameStatus.LOST
            if self._is_attribute_question(self.current_question):
                feedback = self.prompt_generator.no_more_words_left_feedback_prompt(self.current_question,
                                                                                answer)
            else:
                word = self._extract_attribute_or_word_from_question(self.current_question)
                feedback = self.prompt_generator.no_more_words_left_and_last_word_was_not_secret_word_feedback_prompt(
                    self.current_question, answer, self.secret_word, word)
        else:
            remaining_count = len(self.state.remaining_words)
            valid_moves = sum(1 for m in self.moves if m.is_valid) + 1  # +1 for current move
            if valid_moves == self.max_attempts:
                self.status = GameStatus.WON
                feedback = self.prompt_generator.no_contradiction_and_no_moves_left_feedback_prompt(self.max_attempts)
                metadata["next_question"] = None
            else:
                self.current_question = self._generate_next_question()
                feedback = self.prompt_generator.no_contradiction_feedback_prompt(remaining_count,
                                                                                  self.current_question)
                metadata["next_question"] = self.current_question
            self.state.turns_used = valid_moves
            metadata["remaining_words_count"] = remaining_count
            metadata["remaining_words"] = list(self.state.remaining_words).copy()

        return feedback

    def should_retry_response(self, response: str) -> bool:
        if self.enable_reasoning:
            _, answer = extract_reasoning_and_answer(response)
        else:
            answer = response
        yes_no = self._extract_yes_no(answer)
        return not bool(yes_no)

    def get_max_format_retries(self) -> int:
        return 0

    def has_attempts_left(self) -> bool:
        valid_moves = sum(1 for m in self.moves if m.is_valid)
        return valid_moves < self.max_attempts

    def is_game_over(self) -> bool:
        return self.state.contradiction_found or self.state.word_guessed or self.state.format_failure or self.state.turns_used >= self.max_attempts

    def get_result(self) -> GameResult:
        if self.state.word_guessed and self.state.guessed_word == self.secret_word:
            # Model correctly guessed the secret word
            status = GameStatus.WON
            won = True
            score = 100
        elif self.state.contradiction_found:
            # Model gave inconsistent answers
            status = GameStatus.LOST
            won = False
            score = int((self.state.turns_used / self.max_attempts) * 50)
        elif self.state.format_failure:
            # Model failed to produce valid format twice in a row
            status = GameStatus.LOST
            won = False
            score = 0
        else:
            # No contradiction for all turns — model wins
            status = GameStatus.WON
            won = True
            score = 100

        metadata = {
            "score": score,
            "questions_asked": self.state.turns_used,
            "remaining_words_count": len(self.state.remaining_words),
            "contradiction_found": self.state.contradiction_found,
            "contradiction_reason": self.state.contradiction_reason,
            "secret_word": self.secret_word,
            "qa_history": self.state.qa_history,
            "word_guessed": self.state.word_guessed,
            "guessed_word": self.state.guessed_word,
            "format_failure": self.state.format_failure
        }

        return GameResult(
            game_id=self.game_id,
            game_type="twenty_questions",
            status=status,
            moves=self.moves,
            total_moves=len(self.moves),
            won=won,
            target=self.secret_word,
            metadata=metadata
        )
