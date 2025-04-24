import chess
import chess.engine
from collections import Counter
import math

# ——— Configuration ———
engine_path  = "/opt/homebrew/bin/stockfish"  # path to your Stockfish binary
N_GAMES      = 100                            # total number of games
THINK_TIME_A = 0.01                          # seconds per move for Engine A
THINK_TIME_B = 0.001                          # seconds per move for Engine B
SKILL_A      = 0                             # Stockfish “Skill Level” for Engine A (0–20)
SKILL_B      = 0                             # Stockfish “Skill Level” for Engine B (0–20)
ELO_A        = 800                           # target Elo for Engine A
ELO_B        = 1200                          # target Elo for Engine B

def play_game(elo_white, skill_white, elo_black, skill_black):
    board = chess.Board()
    eng_w = chess.engine.SimpleEngine.popen_uci(engine_path)
    eng_b = chess.engine.SimpleEngine.popen_uci(engine_path)

    # configure each engine’s skill and Elo limit
    eng_w.configure({
        "Skill Level":       skill_white,
        # "UCI_LimitStrength": True,
        # "UCI_Elo":           elo_white
    })
    eng_b.configure({
        "Skill Level":       skill_black,
        # "UCI_LimitStrength": True,
        # "UCI_Elo":           elo_black
    })

    while not board.is_game_over():
        if board.turn == chess.WHITE:
            move = eng_w.play(board, chess.engine.Limit(time=THINK_TIME_A)).move
        else:
            move = eng_b.play(board, chess.engine.Limit(time=THINK_TIME_B)).move
        board.push(move)

    eng_w.quit()
    eng_b.quit()
    print(board.result())
    return board.result()  # '1-0', '0-1' or '1/2-1/2'

def estimate_diff(wins, draws, losses):
    n = wins + draws + losses
    s = (wins + 0.5 * draws) / n
    return -400 * math.log10(1/s - 1)

def main():
    half = N_GAMES // 2
    wins = { "A": 0, "B": 0, "D": 0 }

    # First half: A as White vs B as Black
    for _ in range(half):
        result = play_game(ELO_A, SKILL_A, ELO_B, SKILL_B)
        if result == "1-0":
            wins["A"] += 1
        elif result == "0-1":
            wins["B"] += 1
        else:
            wins["D"] += 1

    # Second half: B as White vs A as Black
    for _ in range(half):
        result = play_game(ELO_B, SKILL_B, ELO_A, SKILL_A)
        if result == "1-0":
            wins["B"] += 1
        elif result == "0-1":
            wins["A"] += 1
        else:
            wins["D"] += 1

    # If odd number of games, do one more with A as White
    if N_GAMES % 2:
        result = play_game(ELO_A, SKILL_A, ELO_B, SKILL_B)
        if result == "1-0":
            wins["A"] += 1
        elif result == "0-1":
            wins["B"] += 1
        else:
            wins["D"] += 1

    print(f"Engine A (Skill={SKILL_A}, ≈{ELO_A}) wins : {wins['A']}")
    print(f"Engine B (Skill={SKILL_B}, ≈{ELO_B}) wins : {wins['B']}")
    print(f"Draws                               : {wins['D']}")


if __name__ == "__main__":
    main()
