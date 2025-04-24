# Mapping Stockfish Skill Levels to Elo Ratings

## Overview
This document outlines the process of empirically mapping Stockfish’s built‑in UCI “Skill Level” slider (0–8) to approximate human Elo ratings by playing head‑to‑head matches against the Maia engine at known Elo bands (1100, 1300, 1500).

## Methodology

1. **Select Maia Opponent Ratings**  
   Matches were run against Maia models pegged at Elo levels of 1100, 1300, and 1500.

2. **Conduct Matches**  
   For each Stockfish skill level (0–8) and each Maia rating, play 1,000 games (500 with each engine as White) with:  
   - Stockfish configured to the given skill level.  
   - Maia using its trained weights (unrestricted think time).  
   - Stockfish limited to 0.01 seconds per move.

3. **Collect Results**  
   For each matchup, record:  
   - **SF wins** (W)  
   - **Maia wins** (L)  
   - **Draws** (D)

4. **Compute Score Fraction**  
   For each matchup, calculate the score fraction S:
   
   ```math
   \
     S = \frac{W + 0.5 \times D}{W + D + L}
   \
   ```

5. **Invert Elo Expectation**  
   Solve for rating difference Δ using the Elo formula:
   ```math
   \Delta = -400 \times \log_{10}\left(\frac{1}{S} - 1\right)
   ```
   Then estimate Stockfish's Elo:
   ```math
   \hat{R}_{\text{SF}} = R_{\text{Maia}} + \Delta
   ```

6. **Aggregate Across Opponents**  
   Compute the mean and standard deviation of 
   ```math
   \hat{R}_{\text{SF}}\
   ``` 
   for each skill level across the three Maia ratings.

## Results Table

Skill Level | Maia 1100 (SF / D / M) | Maia 1300 (SF / D / M) | Maia 1500 (SF / D / M) | Maia 1700 (SF / D / M) | Maia 1900 (SF / D / M)
------------:|:---------------------:|:----------------------:|:----------------------:|:----------------------:|:----------------------:
0            | 27.6 / 12.0 / 60.4    | 24.5 / 9.2 / 66.3      | 16.9 / 7.8 / 75.3      | 15.9 / 7.0 / 77.1      | 14.7 / 8.3 / 77.0      
1            | 47.1 / 11.0 / 41.9    | 39.5 / 11.2 / 49.3     | 33.0 / 11.2 / 55.8     | 28.3 / 11.9 / 59.8     | 24.3 / 11.2 / 64.5     
2            | 58.2 / 10.6 / 31.2    | 49.9 / 12.1 / 38.0     | 44.4 / 10.2 / 45.4     | 40.2 / 11.6 / 48.2     | 33.4 / 12.0 / 54.6     
3            | 76.0 / 8.0 / 16.0     | 70.4 / 8.5 / 21.1      | 63.8 / 12.0 / 24.2     | 58.9 / 11.4 / 29.7     | 54.8 / 12.1 / 33.1     
4            | 80.2 / 7.7 / 12.1     | 78.3 / 9.0 / 12.7      | 72.4 / 9.9 / 17.7      | 69.2 / 10.9 / 19.9     | 59.3 / 11.6 / 29.1     
5            | 89.1 / 5.9 / 5.0      | 85.4 / 8.2 / 6.4       | 83.5 / 8.0 / 8.5       | 79.2 / 7.9 / 12.9      | 76.2 / 8.3 / 15.5     
6            | 93.5 / 3.5 / 3.0      | 90.9 / 5.1 / 4.0       | 88.9 / 5.7 / 5.4       | 86.9 / 6.4 / 6.7       | 84.6 / 6.4 / 9.0      
7            | 97.5 / 1.6 / 0.9      | 97.2 / 1.7 / 1.1       | 94.8 / 3.0 / 2.2       | 93.0 / 3.5 / 3.5       | 91.2 / 4.6 / 4.2      
8            | 99.2 / 0.7 / 0.1      | 98.8 / 1.1 / 0.1       | –                     | –                     | –                    

*SF / D / M = Stockfish wins % / Draws % / Maia wins %*
