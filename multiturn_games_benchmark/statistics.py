"""Statistics collection and aggregation"""

import json
from typing import List, Dict, Any
from dataclasses import dataclass, asdict
from collections import Counter
from .base_game import GameResult, GameStatus


@dataclass
class BenchmarkStatistics:
    """Aggregated statistics for a benchmark run"""
    model_name: str
    game_type: str
    total_games: int
    wins: int
    losses: int
    win_rate: float
    avg_attempts: float
    avg_attempts_won: float  # Average attempts for won games only
    median_attempts: float
    min_attempts: int
    max_attempts: int
    invalid_moves_total: int
    attempts_distribution: Dict[str, int]  # {"1": count, "2": count, ..., "failed": count}
    total_duration_seconds: float
    avg_duration_seconds: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


class StatisticsCollector:
    """Collects and aggregates statistics from game results"""
    
    @staticmethod
    def calculate_statistics(
        results: List[GameResult],
        model_name: str,
        game_type: str
    ) -> BenchmarkStatistics:
        """
        Calculate aggregated statistics from game results
        
        Args:
            results: List of game results
            model_name: Name of the model
            game_type: Type of game (e.g., "wordle")
            
        Returns:
            BenchmarkStatistics object
        """
        if not results:
            return BenchmarkStatistics(
                model_name=model_name,
                game_type=game_type,
                total_games=0,
                wins=0,
                losses=0,
                win_rate=0.0,
                avg_attempts=0.0,
                avg_attempts_won=0.0,
                median_attempts=0.0,
                min_attempts=0,
                max_attempts=0,
                invalid_moves_total=0,
                attempts_distribution={},
                total_duration_seconds=0.0,
                avg_duration_seconds=0.0
            )
        
        total_games = len(results)
        wins = sum(1 for r in results if r.won)
        losses = total_games - wins
        win_rate = wins / total_games if total_games > 0 else 0.0
        
        # Calculate attempts statistics
        all_attempts = [r.total_moves for r in results]
        won_attempts = [r.total_moves for r in results if r.won]
        
        avg_attempts = sum(all_attempts) / len(all_attempts) if all_attempts else 0.0
        avg_attempts_won = sum(won_attempts) / len(won_attempts) if won_attempts else 0.0
        
        sorted_attempts = sorted(all_attempts)
        median_idx = len(sorted_attempts) // 2
        median_attempts = sorted_attempts[median_idx] if sorted_attempts else 0.0
        
        min_attempts = min(all_attempts) if all_attempts else 0
        max_attempts = max(all_attempts) if all_attempts else 0
        
        # Count invalid moves
        invalid_moves_total = sum(
            sum(1 for move in r.moves if not move.is_valid)
            for r in results
        )
        
        # Calculate attempts distribution
        attempts_counter = Counter()
        for result in results:
            if result.won:
                attempts_counter[str(result.total_moves)] += 1
            else:
                attempts_counter["failed"] += 1
        
        attempts_distribution = dict(attempts_counter)
        
        # Calculate duration statistics
        total_duration = sum(r.duration_seconds for r in results)
        avg_duration = total_duration / total_games if total_games > 0 else 0.0
        
        return BenchmarkStatistics(
            model_name=model_name,
            game_type=game_type,
            total_games=total_games,
            wins=wins,
            losses=losses,
            win_rate=win_rate,
            avg_attempts=avg_attempts,
            avg_attempts_won=avg_attempts_won,
            median_attempts=median_attempts,
            min_attempts=min_attempts,
            max_attempts=max_attempts,
            invalid_moves_total=invalid_moves_total,
            attempts_distribution=attempts_distribution,
            total_duration_seconds=total_duration,
            avg_duration_seconds=avg_duration
        )
    
    @staticmethod
    def print_statistics(stats: BenchmarkStatistics, verbose: bool = False):
        """
        Print statistics in a readable format
        
        Args:
            stats: BenchmarkStatistics object
            verbose: Whether to print detailed statistics
        """
        print(f"\n{'='*60}")
        print(f"Benchmark Results: {stats.model_name} - {stats.game_type}")
        print(f"{'='*60}")
        print(f"Total Games: {stats.total_games}")
        print(f"Wins: {stats.wins} ({stats.win_rate:.1%})")
        print(f"Losses: {stats.losses} ({(1-stats.win_rate):.1%})")
        print(f"\nAttempts Statistics:")
        print(f"  Average (all games): {stats.avg_attempts:.2f}")
        print(f"  Average (won games): {stats.avg_attempts_won:.2f}")
        print(f"  Median: {stats.median_attempts:.0f}")
        print(f"  Min: {stats.min_attempts}")
        print(f"  Max: {stats.max_attempts}")
        
        if stats.invalid_moves_total > 0:
            print(f"\nInvalid Moves: {stats.invalid_moves_total}")
        
        print(f"\nAttempts Distribution:")
        # Sort distribution by key (attempt number)
        sorted_dist = sorted(
            [(k, v) for k, v in stats.attempts_distribution.items() if k != "failed"],
            key=lambda x: int(x[0])
        )
        for attempts, count in sorted_dist:
            percentage = (count / stats.total_games) * 100
            bar = '█' * int(percentage / 2)
            print(f"  {attempts} attempts: {count:3d} ({percentage:5.1f}%) {bar}")
        
        if "failed" in stats.attempts_distribution:
            count = stats.attempts_distribution["failed"]
            percentage = (count / stats.total_games) * 100
            bar = '█' * int(percentage / 2)
            print(f"  Failed:      {count:3d} ({percentage:5.1f}%) {bar}")
        
        print(f"\nDuration:")
        print(f"  Total: {stats.total_duration_seconds:.2f}s")
        print(f"  Average per game: {stats.avg_duration_seconds:.2f}s")
        print(f"{'='*60}\n")
