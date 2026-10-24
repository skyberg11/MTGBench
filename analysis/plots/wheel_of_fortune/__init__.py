"""Wheel of Fortune figures: scores by target complexity and letter-choice tactics."""

from .conditional_letter import plot_conditional_letter
from .difficulty import plot_difficulty


def plot_wheel_of_fortune(episodes, root, output, resamples=10000, seed=42):
    plot_difficulty(episodes, root, output, resamples, seed)
    plot_conditional_letter(episodes, root, output, resamples, seed)


__all__ = ["plot_wheel_of_fortune"]
