import get_refined_csv


def main() -> None:
    get_refined_csv.GAME_MODE = get_refined_csv.GameMode.DRAGON_VS_LLM
    get_refined_csv.FILTER_OUT_BELOW_N_MISC = 0
    get_refined_csv.main()


if __name__ == "__main__":
    main()


