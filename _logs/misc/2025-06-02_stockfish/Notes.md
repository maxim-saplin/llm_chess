## Move History

Testing the Stockfish engine with and without move history. The original baseline was achieved with move history provided, yet LLMs are tested without history. Before changing the baseline to no history, both configurations were rerun to assess the impact on the results. Using default 100ms per move compute for Stockfish on MBP M1 Pro, Stockfish playing as black.

- With history: 100% wins, average_moves: 31.848, std_dev_moves: 13.31834352591471
- No history: 100% wins, average_moves: 31.486, std_dev_moves: 12.878884643852885

## Revising Baseline

Using Stockfish's skill levels (default at 1) and changing per move compute time (default 0.1s instead of previous 0.01s). It appears that compute time alone is hardware-agnostic but not entirely reproducible. Below are the results for different configurations:

### Results Summary

#### No History (M1 Pro, 100ms per move)
- Skill Level 1: 1000 games, 0 white wins, 1000 black wins, 0 draws, average_moves: 57.922, std_dev_moves: 30.9617
- Skill Level 10: 1000 games, 0 white wins, 1000 black wins, 0 draws, average_moves: 39.052, std_dev_moves: 17.2803
- Skill Level 20: 1000 games, 0 white wins, 999 black wins, 1 draw, average_moves: 28.26, std_dev_moves: 10.9261

#### No History (Intel i5-13600KF, 100ms per move)
- Skill Level 1: 1000 games, 0 white wins, 996 black wins, 4 draws, average_moves: 60.458, std_dev_moves: 30.9104
- Skill Level 10: 1000 games, 0 white wins, 997 black wins, 3 draws, average_moves: 39.432, std_dev_moves: 17.1461
- Skill Level 20: 1000 games, 0 white wins, 1000 black wins, 0 draws, average_moves: 28.486, std_dev_moves: 10.5481

### Hardware and Software Configurations
1. 14" M1 Pro MacBook Pro, Stockfish 17
2. Intel Core i5-13600KF, WSL, Stockfish 17 (stockfish-ubuntu-x86-64-avx2)