# Parse console output and take out board states, used to animate board in index.html
def process_chess_log(file_path):
    with open(file_path, "r") as file:
        lines = file.readlines()

    boards = []
    current_board = []
    possible_start_chars = {
        "♔",
        "♕",
        "♖",
        "♗",
        "♘",
        "♙",
        "♚",
        "♛",
        "♜",
        "♝",
        "♞",
        "♟",
        "⭘",
    }

    for line in lines:
        stripped_line = line.strip()
        if (
            len(current_board) < 8
            and stripped_line
            and stripped_line[0] in possible_start_chars
        ):
            current_board.append(stripped_line)
        elif len(current_board) == 8:
            boards.append("\n".join(current_board))
            current_board = []

    # Add the last board if it was not added
    if len(current_board) == 8:
        boards.append("\n".join(current_board))

    # Join all boards with a delimiter
    formatted_output = "\n-\n".join(boards)

    return formatted_output


# Usage
file_path = "_logs/sample_game_random_vs_gpt4mini.md"
formatted_boards = process_chess_log(file_path)
print(formatted_boards)
