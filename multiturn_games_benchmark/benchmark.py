"""Benchmark runner for multi-turn games"""

import json
import time
import os
import traceback
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from .base_game import BaseGame, GameResult
from .llm_player import LLMPlayer
from .statistics import StatisticsCollector, BenchmarkStatistics



class SetEncoder(json.JSONEncoder):
    """Custom JSON encoder that converts sets to lists"""
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        return super().default(obj)


class GameBenchmark:
    """Runs benchmark tests for multi-turn games"""

    def __init__(self, game_type: str, model_config: Dict[str, Any]):
        """
        Initialize benchmark runner

        Args:
            game_type: Type of game (e.g., "wordle")
            model_config: Model configuration dictionary
        """
        self.game_type = game_type
        self.model_config = model_config
        self.model_name = model_config['model_name']

        # Initialize LLM player
        self.player = LLMPlayer(model_config)
    
    def run_single_game(self, game: BaseGame, max_attempts: Optional[int] = None) -> GameResult:
        """
        Run a single game

        Args:
            game: The game instance to play
            max_attempts: Maximum number of attempts (overrides game default)

        Returns:
            GameResult object
        """
        if max_attempts is not None:
            game.max_attempts = max_attempts

        start_time = time.time()

        system_prompt = game.get_system_prompt()
        initial_message = game.get_initial_user_message()

        self.player.initialize_player_with_prompts(system_prompt, initial_message)

        print(f"\n{'='*60}")
        print(f"Starting game: {game.game_id}")
        print(f"{'='*60}")

        # Game loop
        supports_retry = hasattr(game, 'should_retry_response')

        while not game.is_game_over() and game.has_attempts_left():
            retry_count = 0
            llm_response = None
            move = None

            try:
                # Get LLM's move
                llm_response = self.player.get_move()

                move = game.process_player_move(llm_response)

                raw_display = move.player_input[:100] + ("..." if len(move.player_input) > 100 else "")
                feedback_display = move.feedback[:300] + ("..." if len(move.feedback) > 300 else "")
                print(f"\nMove {move.move_number} (LLM):")
                print(f"  LLM raw answer: {raw_display}")
                print(f"  LLM answer: {move.player_answer}")
                print(f"  Judge Feedback: {feedback_display}")

                self.player.add_player_history(move.player_answer)
                self.player.add_feedback(move.feedback)

            except Exception as e:
                print(f"\nError during game: {e}")
                traceback.print_exc()
                break

        # Get game result
        result = game.get_result()
        result.initial_prompt = self.player.messages[0]['content']
        result.duration_seconds = time.time() - start_time
        print(f"\nGame finished:")
        print(f"  Status: {result.status.value}")
        print(f"  Won: {result.won}")
        print(f"  Total moves: {result.total_moves}")
        print(f"  Duration: {result.duration_seconds:.2f}s")

        # Reset player for next game
        self.player.reset()

        return result
    
    def run_benchmark(
        self,
        games: List[BaseGame],
        max_attempts: Optional[int] = None,
        save_results: bool = True,
        save_chat_history: bool = False,
        chat_history_dir: Optional[Path] = None
    ) -> BenchmarkStatistics:
        """
        Run benchmark on multiple games

        Args:
            games: List of game instances to play
            max_attempts: Maximum attempts per game
            save_results: Whether to save results to file

        Returns:
            BenchmarkStatistics object
        """
        print(f"\nRunning benchmark: {self.model_name} on {len(games)} {self.game_type} games")
        print(f"Max attempts per game: {max_attempts or 'default'}")

        if save_chat_history and chat_history_dir:
            print(f"Chat histories will be saved to: {chat_history_dir}")

        results = []
        for i, game in enumerate(games, 1):
            print(f"Progress: {i}/{len(games)}", end='\r')

            result = self.run_single_game(game, max_attempts)
            results.append(result)

            if save_chat_history and chat_history_dir:
                self._save_chat_history(
                    episode_id=str(i-1),
                    game=game,
                    result=result,
                    output_dir=chat_history_dir
                )

        stats = StatisticsCollector.calculate_statistics(
            results,
            self.model_name,
            self.game_type
        )
        StatisticsCollector.print_statistics(stats, verbose=True)

        if save_results:
            self._save_results(results, stats)

        return stats
    
    def return_tokens(self):
        return self.player.prompt_tokens, self.player.completion_tokens, self.player.price

    def _save_chat_history(
        self,
        episode_id: str,
        game: BaseGame,
        result: GameResult,
        output_dir: Path
    ) -> None:
        """Save chat history for a single game episode."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        conversation_history = []
        for move in result.moves:
            conversation_history.append({
                "role": "assistant",
                "content": move.player_input,
                "turn": move.move_number
            })
            conversation_history.append({
                "role": "user",
                "content": move.feedback,
                "turn": move.move_number
            })

        chat_data = {
            "episode_id": episode_id,
            "model": self.model_name,
            "game_type": result.game_type,
            "success": result.won,
            "turns_used": result.total_moves,
            "target": result.target,
            "conversation_history": conversation_history,
            "metadata": result.metadata
        }

        filename = f"chat_episode_{episode_id}.json"
        filepath = output_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(chat_data, f, indent=2, ensure_ascii=False, cls=SetEncoder)

    def _save_results(self, results: List[GameResult], stats: BenchmarkStatistics):
        """Save results to JSON file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        filepath = os.getenv('JSON_OUTPUT_FILE')
        if not filepath:
            results_dir = Path(f"results")
            results_dir.mkdir(parents=True, exist_ok=True)
            safe_model_name = self.model_name.replace('/', '_').replace(':', '_')
            filename = f"{timestamp}_{safe_model_name}_{self.game_type}_results.json"
            filepath = str(results_dir / filename)

        results_dict = {
            "metadata": {
                "timestamp": timestamp,
                "model_name": self.model_name,
                "game_type": self.game_type,
                "model_config": self.model_config,
                "cost": self.player.price,
                "prompt_tokens": self.player.prompt_tokens,
                "completion_tokens": self.player.completion_tokens
            },
            "statistics": stats.to_dict(),
            "games": [
                {
                    "game_id": r.game_id,
                    "status": r.status.value,
                    "won": r.won,
                    "initial_prompt": r.initial_prompt,
                    "total_moves": r.total_moves,
                    "target": r.target,
                    "duration_seconds": r.duration_seconds,
                    "moves": [
                        {
                            "move_number": m.move_number,
                            "player_input": m.player_input,
                            "player_answer": m.player_answer,
                            "feedback": m.feedback,
                            "is_valid": m.is_valid,
                            "metadata": m.metadata
                        }
                        for m in r.moves
                    ],
                    "metadata": r.metadata
                }
                for r in results
            ],
            "debug": [msg if isinstance(msg, dict) else msg.model_dump() for msg in self.player.raw_responses]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results_dict, f, indent=2, ensure_ascii=False)
        
        print(f"Results saved to: {filepath}")
