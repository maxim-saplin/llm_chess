import get_refined_csv


def main() -> None:
    get_refined_csv.GAME_MODE = get_refined_csv.GameMode.RANDOM_VS_LLM
    get_refined_csv.main()


if __name__ == "__main__":
    main()


