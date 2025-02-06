## Move History

Testing Stockfish engine with and without move history, the original baseline was achieved with move history provided yet LLMs are tested without history. Before changing the baseline to no history reruning both with and without move history to assess the impact on the results. Using default 10ms per move compute for Stockfish on MBP M1 Pro, Stockfish playing as black.

- With history: 100% wins, average_moves: 31.848, std_dev_moves: 13.31834352591471
- No history: 100% wins, average_moves: 31.486, std_dev_moves: 12.878884643852885

## Revising Baseline

Using Stockfishs skill levels (Default at 1) and changing per move compute time (default 0.1s instead of previous 0.01s) instead of just cmpute time - it seems that just compute time is hardware agnostics and is not quite reproducible.