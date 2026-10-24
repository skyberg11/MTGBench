"""Runtime templates, distributed with the Python package."""

from functools import lru_cache
from importlib.resources import files


@lru_cache(maxsize=None)
def load_prompt(game: str, template: str, language: str) -> str:
    """Read an EN/RU template without depending on the working directory."""
    if language not in {"en", "ru"}:
        raise ValueError(f"Unsupported prompt language: {language!r}")
    if not all(
        part and all(c.isalnum() or c == "_" for c in part) for part in (game, template)
    ):
        raise ValueError("Game and template must be resource names")
    name = f"{template}_{language}.txt"
    try:
        return files(__package__).joinpath(game, name).read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Missing prompt: {game}/{name}") from exc
