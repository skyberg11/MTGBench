"""Base classes for game judges"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Tuple


class BaseJudge(ABC):
    """Abstract base class for game judges"""

    @abstractmethod
    def evaluate_player_move(self, game_state: Dict[str, Any], player_input: str) -> Tuple[bool, str]:
        """
        Evaluate a player's move and return feedback

        Args:
            game_state: Current state of the game (target word, previous moves, etc.)
            player_input: The player's input to evaluate

        Returns:
            Feedback string (format depends on game type)
        """
        pass
