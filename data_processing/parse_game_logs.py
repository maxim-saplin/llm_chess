"""Before May 1, the game logs did not contain a pgn field, so we need to reconstruct all moves from output.txt.

Note here we can assume that white is always random and black is always LLM, as this was before we implemented the engine.

"""

import re

def extract_moves_per_game(text):
    # Split on the line that starts each new “random player” game
    sessions = text.split("You are a random chess player.")
    all_games = []
    move_regex = re.compile(r"\bmake_move\s+([a-h][1-8][a-h][1-8][qrbn]?)\b")

    for session in sessions:
        lines = session.splitlines()
        moves = []
        i = 0
        while i < len(lines):
            m = move_regex.search(lines[i])
            if m:
                move = m.group(1)
                # look ahead for confirmation before another make_move
                j = i + 1
                confirmed = False
                while j < len(lines) and not move_regex.search(lines[j]):
                    if "Move made, switching player" in lines[j]:
                        confirmed = True
                        break
                    j += 1
                if confirmed:
                    moves.append(move)
                # continue scanning from j (so we don't double‐count)
                i = j
            else:
                i += 1
        if moves:
            all_games.append(moves)
    return all_games

if __name__ == "__main__":
    # replace 'transcript.txt' with your filename
    with open("transcript.txt", "r", encoding="utf-8") as f:
        text = f.read()

    games = extract_moves_per_game(text)
    for idx, moves in enumerate(games, 1):
        print(f"Game {idx}:")
        print(" ".join(moves))
        print()