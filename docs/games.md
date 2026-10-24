# Games and scoring

Every game is available in English and Russian. `--CoT` changes player instructions; native reasoning is configured separately in `models.json`.

## Word Chain

The model and a fixed opponent alternate city names. Each city must start with the effective last letter of the previous one and must not have appeared before. The supplied vocabulary validates names; a separate vocabulary controls opponent moves.

Opening city `London` → `Answer: New York`. A repeated, unknown or incorrectly chained city loses the game. The model wins if the opponent has no valid move or the model completes the turn budget (25 in the paper). For Russian city names ending in ь, ъ or ы, the preceding character determines the next letter.

Survival score rewards valid turns before failure; winning yields 1.

See Appendix A.1 of the paper for the full rules.

## Wordle

A five-letter noun is hidden. Submit one guess per turn; feedback marks letters as green (right position), yellow (present elsewhere), or gray (absent). The model is not given the candidate vocabulary. Invalid guesses consume a turn.

`Answer: crane` → per-letter feedback → another guess. A correct word wins; the paper uses 20 attempts. Repeated letters are checked independently against the full target, without exhausting its letter counts.

Speed score uses the released per-word baseline turn count.

See Appendix A.2 of the paper for the full rules.

## Situation Puzzles

The model sees an unusual situation but not its explanation. It asks one clarifying question or proposes one complete explanation per turn. An LLM verifier sees the solution and the key fact.

`Question: Was the door locked?` → yes, no, irrelevant or clarification. `Answer: …` proposes a solution; covering the key fact wins. The paper horizon is 20 turns.

Speed score rewards solving the puzzle early.

See Appendix A.3 of the paper for the full rules.

## 20 Questions

The model is the respondent. It sees a synthetic secret word, the candidate pool and the words’ hierarchical attributes. An algorithm asks attribute questions and word guesses, tracking candidates consistent with the answers.

Given that the secret has attribute X: `Does your word have X?` → `Answer: yes`. A contradiction loses; consistently confirming the secret or surviving 20 questions wins.

Survival score: 1 for a win, otherwise (turns − 1) / 20.

See Appendix A.4 of the paper for the full rules.

## Wheel of Fortune

A masked word is shown. The model can guess one letter or the entire word. A correct letter reveals all matching positions; a word guess or full reveal can win. Russian play treats И/Й, Е/Ё and Ь/Ъ/Ы as equivalence classes.

`Answer: E` or `Answer: WORD: PLANET`. English play allows 26 attempts and Russian play 29.

Speed score uses half the target’s distinct letter classes as its floor and a common normalization horizon of 29 in both languages.

See Appendix A.5 of the paper for the full rules.

## 20 Features

An object’s features are revealed one at a time. The model guesses an object after each feature; an LLM verifier evaluates the guess. Optional `nei` requests another feature, but the reported model benchmark disables it.

`Color: red` → `ANSWER: apple`. A correct guess wins; at most 20 turns are available.

Speed score has floor 2 and horizon 20.

See Appendix A.6 of the paper for the full rules.

## Alias with Personalities

A public figure is hidden. The model asks one yes/no question or makes one identity guess per turn. The biography verifier is instructed to answer `No` when the stored text lacks the requested information or the question is not a yes/no question.

`ANSWER: Is this person a scientist?` or `ANSWER: Marie Curie!`. A correct identity wins; the paper horizon is 30 turns.

Speed score has floor 9 and horizon 30.

See Appendix A.7 of the paper for the full rules.

## Score and win rate

Win rate counts successful episodes equally. Normalized score additionally rewards speed or surviving without an error. For speed games a loss scores zero; a win scores `clamp(1 - (turns - 1 - floor) / (horizon - floor), 0, 1)`. Wordle uses its saved baseline turns minus one as the floor; Situation Puzzles uses 1. For survival games the score is 1 on a win and `(turns - 1) / horizon` on a loss.

Here, `turns` is the number of recorded moves; `turns - 1` is the zero-based terminal-turn index. A last-turn victory can therefore have a positive score. `Total` averages the seven game means with equal weight. The formulas are implemented in [scoring.py](../analysis/scoring.py). See [analysis](../analysis/README.md) for exclusions, human aggregation and the separate score formula used in the Wordle figures.
