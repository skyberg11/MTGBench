"""Multi-turn LLM Games Benchmark Package"""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("multiturn-games-benchmark")
except PackageNotFoundError:
    __version__ = "0.1.0"
