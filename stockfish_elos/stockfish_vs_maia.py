import chess
import chess.engine
import json
import datetime
from collections import Counter

# ——— Configuration ———
SF_PATH      = "/opt/homebrew/bin/stockfish"  # your Stockfish binary
LC0_PATH     = "/opt/homebrew/bin/lc0"           # your lc0 binary
MAIA_WEIGHT  = "maia_paths/maia-1200.pb.gz"     # download from CSSLab
SKILL_LEVELS = range(0, 6)                   # test Stockfish levels 1–10
N_GAMES      = 1000                             # games per level
SF_THINK     = 0.01                           # Stockfish time per move

def make_stockfish(skill):
    sf = chess.engine.SimpleEngine.popen_uci(SF_PATH)
    sf.configure({ "Skill Level": skill })
    return sf

def make_maia():
    return chess.engine.SimpleEngine.popen_uci(
        [LC0_PATH, f"--weights={MAIA_WEIGHT}"]
    )

def play_one_game(maia_as_white: bool, skill: int):
    board = chess.Board()
    sf   = make_stockfish(skill)
    maia = make_maia()

    while not board.is_game_over():
        if board.turn == chess.WHITE:
            engine, is_sf = (maia, False) if maia_as_white else (sf, True)
        else:
            engine, is_sf = (sf, True) if maia_as_white else (maia, False)

        limit = chess.engine.Limit(time=SF_THINK) 
        move  = engine.play(board, limit).move
        board.push(move)

    sf.quit()
    maia.quit()
    return board.result()  # '1-0', '0-1', '1/2-1/2'

def main():
    for skill in SKILL_LEVELS:
        logs = []
        tally = Counter()

        for i in range(N_GAMES):
            maia_white = (i % 2 == 0)
            result      = play_one_game(maia_white, skill)

            if result == "1-0":
                winner = "Maia" if maia_white else f"SF{skill}"
            elif result == "0-1":
                winner = f"SF{skill}" if maia_white else "Maia"
            else:
                winner = "Draw"

            tally[winner] += 1

            logs.append({
                "timestamp"    : datetime.datetime.now().isoformat(),
                "skill_level"  : skill,
                "game_number"  : i + 1,
                "white_engine" : "Maia" if maia_white else f"SF{skill}",
                "result"       : result,
                "winner"       : winner
            })

        # summary entry for this skill level
        logs.append({
            "timestamp"    : datetime.datetime.now().isoformat(),
            "skill_level"  : skill,
            "summary"      : {
                "SF_wins"   : tally[f"SF{skill}"],
                "Maia_wins" : tally["Maia"],
                "draws"     : tally["Draw"]
            }
        })

        filename = f"maia_logs/match_results_maia_1200_vs_sf_{skill}.json"
        with open(filename, "w") as f:
            json.dump(logs, f, indent=2)
        print(f"Wrote results for skill {skill} to {filename}")

if __name__ == "__main__":
    main()