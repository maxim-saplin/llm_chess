try:
    # When executed as a module: python -m data_processing.get_refined_elo
    from . import get_refined_csv as grc
except Exception:
    # When executed as a script: python data_processing/get_refined_elo.py
    import os
    import sys

    sys.path.append(os.path.dirname(__file__))
    import get_refined_csv as grc


def main() -> None:
    # Configure Elo mode and sensible defaults for a quick run
    grc.GAME_MODE = grc.GameMode.ELO
    grc.FILTER_OUT_BELOW_N_RANDOM = 10
    grc.FILTER_OUT_BELOW_N_MISC = 2
    # grc.DATE_AFTER = "2025.12.01_00:00"
    # 0 means always mix Random and Dragon blocks when Random is calibrated
    grc.ELO_DRAGON_ONLY_MIN_GAMES = 0
    grc.main()


if __name__ == "__main__":
    main()
