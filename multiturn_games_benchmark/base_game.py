"""Base classes for multi-turn games"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum


class GameStatus(Enum):
    """Status of the game"""
    IN_PROGRESS = "in_progress"
    WON = "won"
    LOST = "lost"
    INVALID_MOVE = "invalid_move"


@dataclass
class GameMove:
    """Represents a single move in the game"""
    move_number: int
    player_input: str
    player_answer: str
    feedback: str
    is_valid: bool
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class GameResult:
    """Result of a completed game"""
    game_id: str
    game_type: str
    status: GameStatus
    moves: List[GameMove]
    total_moves: int
    won: bool
    initial_prompt: Optional[str] = None
    target: Optional[str] = None  # The answer (if applicable)
    duration_seconds: float = 0.0
    initial_prompt: str = ""
    metadata: Optional[Dict[str, Any]] = None


class BaseGame(ABC):
    """Abstract base class for all multi-turn games"""
    
    def __init__(self, game_id: str, max_attempts: int):
        self.game_id = game_id
        self.max_attempts = max_attempts
        self.moves: List[GameMove] = []
        self.status = GameStatus.IN_PROGRESS
        
    @abstractmethod
    def process_player_move(self, player_input: str) -> GameMove:
        """
        Process a player's move and return feedback
        
        Args:
            player_input: The player's input (word, city name, question, etc.)
            
        Returns:
            GameMove object with feedback
        """
        pass
    
    @abstractmethod
    def is_game_over(self) -> bool:
        """Check if the game has ended"""
        pass
    
    @abstractmethod
    def get_result(self) -> GameResult:
        """Get the final result of the game"""
        pass

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Get the system prompt for this game type"""
        pass

    @abstractmethod
    def get_initial_user_message(self) -> str:
        """Get the initial message to start the game"""
        pass
    
    def get_move_count(self) -> int:
        """Get the current number of moves"""
        return len(self.moves)

    def has_attempts_left(self) -> bool:
        """Check if there are attempts remaining"""
        return self.get_move_count() < self.max_attempts
