# Post Submission

## Post Submission Goal

1\. Develop a more consistent and extensible framework for our benchmark. 

- Right now, it is not completely clear why we select models we do, why we play a certain number of games, or why we play them against certain opponents. So, it is not clear how we would add a model.   
- We also would like a more structured way our benchmark works so we can have one leaderboard for fairer comparisons.   
- Finally, the confidence bounds on our games are too high, making it hard to compare models.

2\. Comparison to other benchmarks

- E.g. one of recent studies demonstrated how RL on Math improves non-math performance [https://arxiv.org/pdf/2507.00432](https://arxiv.org/pdf/2507.00432), related question “Is Chess performance associated with better results in other tasks”

To address this, we have developed a procedure that can be applied to all new models, detailed below:

### **Evaluation Framework: Two-Phase Adaptive Testing Protocol**

Note since LLMs are currently poor chess players, we split our bots into two brackets and start with the first: 

* Bracket 1: Skills 1-12 (Elo \~250-1750)  
* Bracket 2: Skills 13-24 (Elo \~1875-3250)

We will have a separate leaderboard for models in each bracket. This is useful because it allows us not to waste compute when using a poor-performing model (because we will not test on high Elos, which it will easily lose to) or using a high-performing model (because we will not test on low Elos, which it will easily beat).

*Notes:*

- *We only use odd numbered skills since each differentiates only by 125 Elo.*  
- *There are 25 total levels, but the last one depends on bot compute and can be handled on its own if a model reaches that high of performance, which we expect to be far in the future.*

**Phase A: Skill Mapping** (n ≈ 30 random \+ 60-90 bot)

The goal is to first test the model against a random player. If it performs poorly (win/loss \< 50%), we do not need to test against our bots and can instead place it in a separate "Below Random" tier. If it performs well, we proceed to bot testing.

* Random baseline: 30 games, return if win/loss \< 50% ~~SPRT early stopping (α \= β \= 0.05)~~ (unfortunately the conf ints will not be enough with only 30 games, so we need only go by vibes).  
* Sparse sampling: 10-15 games at skills evenly spaced in Bracket 1 ({1, 3, 5, 7, 9, 11}).  
  * Promotion criterion: If P(win) \>= 0.7 at skill 11, redo the 10-15 games across evenly spaced skill levels in Bracket 2 and move to Bracket 2 for all future phases  
  * Note: We test all models across the full bracket range to ensure fairness and capture unexpected victories that could significantly impact Elo calculations  
* Output: Empirical win rate curve

**Phase B: Elo Refinement** (n ≈ 60-100 games)

Before starting, fix the desired CI size, e.g., ±25-50 Elo.

* Critical zone: Skills where P(win) ∈ \[0.3, 0.7\] from Phase A.  
* Dense sampling: 30 games per skill in critical zone  
* Output: Maximum likelihood Elo ± 95% CI via Fisher information

Before starting, fix the desired CI width, e.g., ±25-50 Elo.

* Critical zone identification: Skills where P(win) ∈ \[0.3, 0.7\] from Phase A ~~and their neighbors~~ (don’t do neighbors, let’s just focus on odd Elos bc the evens are not as much of a jump)  
  * This focuses computational resources where they provide maximum information gain  
  * Important: Test ALL intermediate skills to detect plateaus  
  * Example:   
    * If Phase A shows Skill 5: 69%, Skill 7: 35%, Skill 9: 18%  
    * Critical zone \= {5, 7} (both within 30-70% range)  
    * ~~Consider also testing skills {4, 8} on the boundary~~ (likely not necessary)  
* Dense sampling procedure:  
  * Play 20-30 games per skill in the extended critical zone  
  * This prevents missing performance plateaus where multiple skills yield \~50% win rate  
* Output: Maximum likelihood Elo ± 95% CI via Fisher information

After this procedure, we will have a leaderboard of LLMs with Elo ratings based on the bot's skill level mappings with small confidence intervals at a relatively low cost. We will have three parts of the leaderboard: ‘Random’, ‘Bracket 1’, and ‘Bracket 2’.

# For Submission

## May 5

- Compare ranking of LLM vs Random vs LLM vs Dragon Lvl 1 \- if it is consistent, random is representative, otherwise analyze why  
- Run exceptional experiment with o3-low with 20 minute timeout to see if it can qualify against Dragon lvl 2  
- Run NoN 04-low vs Lvl 1 Dragon

## 

## Apr 24, 2025 | [Matei’s Group Meeting](https://www.google.com/calendar/event?eid=bXJib3E3MmZkNG1tMTJzdTVndnAyNTA0dThfMjAyNTA0MjRUMjExNTAwWiBzYWlrb2xhc2FuaUBiZXJrZWxleS5lZHU)

Attendees: [Sai Kolasani](mailto:saikolasani@berkeley.edu) [matei.zaharia@gmail.com](mailto:matei.zaharia@gmail.com) [Jared Quincy Davis](mailto:jaredquincydavis@gmail.com)

Notes

* When to use get hint tool use  
* Larger paper on ensembles

Action items

- [ ] 

## 

## Apr 20, 2025 | [LLM Chess Weekly](https://www.google.com/calendar/event?eid=N2UzZjgyZWM5NnZlM3F0MDlqMXNhZWJjYTRfMjAyNTA0MjBUMTcwMDAwWiBzYWlrb2xhc2FuaUBiZXJrZWxleS5lZHU)

Attendees: [Sai Kolasani](mailto:saikolasani@berkeley.edu) [Maxim Saplin](mailto:smaxmail@gmail.com)[kylepmont@gmail.com](mailto:kylepmont@gmail.com) [ncrispino0@gmail.com](mailto:ncrispino0@gmail.com)

Notes

* there are two base stockfish parameters you can configure to handicap its elo \-- 1\) the skill level, and 2\) the max time per move  
* its not a perfect system, but in my preliminary experiment I pegged 800 elo at stockfish 0 with .01s per move, 1000 at stockfish 1 with 0.01s per move, etc. I then ran some benchmarks to confirm that the win rates between these stockfish versions matches the expected theoretical win rates given the elo system, with 10-15% margin of error  
* i'm not sure if the 800 score is quite right, but the relative scores are fairly correct, so if we find out what the lowest level is, we should be able to adjust everything up/down  
* based on my assessment of the games \-- i feel like the stockfish 0 with 0.01s felt roughly like an 800 player (on speed chess). maybe lower down to 400 FIDE on some moves, but DEF not higher than 1000 overall

Action items

- [ ] Ablation Studies:  
      - [ ] Play History  
      - [ ] Non-agentic Structure?  
      - [ ] Board state in text representation vs visual representation  
- [x] ~~Continue the Compound AI systems approach~~

## 

## Apr 17, 2025 | [Matei’s Group Meeting](https://www.google.com/calendar/event?eid=bXJib3E3MmZkNG1tMTJzdTVndnAyNTA0dTggc2Fpa29sYXNhbmlAYmVya2VsZXkuZWR1)

Attendees:  [Sai Kolasani](mailto:saikolasani@berkeley.edu) [matei.zaharia@gmail.com](mailto:matei.zaharia@gmail.com) [Jared Quincy Davis](mailto:jaredquincydavis@gmail.com)

Notes

* **Potential new direction (Very Far out in the Future):**  
  * Give chess puzzles and have the LLM solve them??  
    * Chess.com does this, actually  
* **Anchoring LLM Chess ELO to Stockfish**  
  * **Goal:** Assign interpretable, anchored ELO ratings to LLMs by benchmarking against known Stockfish levels.  
  * **Method:**  
    * Use **Stockfish at various skill levels/elos (1–20)** with approximate ELOs (ranging from \~800 to 3000+).  
      *   
    * Treat each level as a reference point with a known or estimated ELO.  
    * Run structured matches between each LLM and a range of Stockfish levels.  
  * **Execution Plan:**  
    * Run at least 30 games between each LLM and a range of Stockfish levels.  
    * Alternate colors and vary openings for statistical reliability.  
    * Use consistent time controls and prompting format (e.g., FEN → move response).  
  * **Output:**  
    * Plot win rate vs. Stockfish ELO level.  
    * Fit a performance curve (e.g., logistic function) to interpolate the LLM’s estimated ELO.  
    * Report examples like:  
       “GPT-4o plays at \~1500 ELO,”  
       “Claude 3.5 aligns with \~1400 ELO.”

Action items

- [ ] 

## 

## Apr 13, 2025 | [LLM Chess Weekly](https://www.google.com/calendar/event?eid=N2UzZjgyZWM5NnZlM3F0MDlqMXNhZWJjYTRfMjAyNTA0MTNUMTcwMDAwWiBzYWlrb2xhc2FuaUBiZXJrZWxleS5lZHU)

Attendees: [Sai Kolasani](mailto:saikolasani@berkeley.edu) [Maxim Saplin](mailto:smaxmail@gmail.com) [chi@chiwang.cc](mailto:chi@chiwang.cc) [chenguangwang.cs@gmail.com](mailto:chenguangwang.cs@gmail.com) [ncrispino0@gmail.com](mailto:ncrispino0@gmail.com) ~~[kylepmont@gmail.com](mailto:kylepmont@gmail.com)~~

Notes

* Potential ideas for the paper: Since we are framing this as a benchmarking paper we should have examples of:  
  * Good result, bad instruction following  
  * Good result, good instruction following  
  * Bad result, Bad following  
  * Bad result, good following

Action items

- [ ] More results:  
      - [ ] LLM vs LLM  
      - [ ] LLM with history vs LLM  
      - [ ] LLM with history vs random player  
- [ ] 9-10 player elo rating system with stock fish as one of the players  
- [ ] Continue running compound system simulations with weaker models  
      - [ ] Implement aggregation methods (most common vote. etc.)  
- [ ] 

## 

## Apr 3, 2025 | [Matei, Sai, and Jared](https://www.google.com/calendar/event?eid=NDJsbm5nbjE4aDU1YmFjajQ1ZzVkdXBxZGwgc2Fpa29sYXNhbmlAYmVya2VsZXkuZWR1)

Attendees: [Sai Kolasani](mailto:saikolasani@berkeley.edu) [matei.zaharia@gmail.com](mailto:matei.zaharia@gmail.com) [Jared Quincy Davis](mailto:jaredquincydavis@gmail.com)

Notes

* Angles to focus on conference submission  
  * Research on chess somewhere  
    * Anchor project in existing research on chess AI.  
    * Frame LLM Chess as a benchmarking task to evaluate LLM reasoning and instruction-following  
  * Using this as a task to try Compound AI Systems  
    * Team of o3(compound systems of calls)  
      * Ensemble results  
      * Voting  
  * Different multi-agent arichectures  
    * Ag2 vs Langchain etc.   
  * Explore inference time  
  * Better Logging/Benchmarking  
    * Inference latency per move  
    * Total runtime per game  
    * Cost-per-game for different setups (including cheap model ensembles)  
    * Elo Rating (Based on win rate)  
      * Elo makes it clearer how much better something is  
      * Relative to a human  
  * Play against chess engines  
    * Different versions of chess engines (stockfish resources)  
    * Support different difficulty levels and engine versions  
* Infrastructure & Experimentation Speed  
  * See if moving the game simulation and evaluation pipeline to cloud infrastructure is feasible  
  * Goal: Shorten iteration cycles, scale testing, and explore ideas faster.  
* Tune models to be better at chess using RL  
* LLM selector

Action itemsN

- [ ] Improved Logging  
      - [x] ~~Dollar cost~~  
      - [ ] Latency measure  
- [ ] Elo Rating System  
      - [x] ~~Implement Elo rating based on win rates.~~  
            - [ ] Start with the top 4 models for the elo ratings  
      - [ ] Extend to show relative skill gaps between models (e.g., how much better than Random? Human baseline?).  
      - [ ] Visualize Elo distributions over time or across architectures.  
- [ ] Add new Models  
      - [ ] Llama 4 Models  
      - [ ] Gemini 2.5  
- [ ] Play Against Chess Engines  
      - [x] ~~Integrate matches against chess engines (e.g., Sunfish, Stockfish).~~  
      - [x] ~~Use varying difficulty levels and versions for robustness.~~  
      - [ ] Include LLMs vs Stockfish baselines for benchmarks.  
- [ ] Multi-Model Team Agents   
      - [x] ~~Create “compound” agents with multiple LLM calls per turn.~~  
      - [ ] Implement ensemble voting systems.  
      - [ ] Compare naive voting vs specialized module voting.  
      - [ ] Implement and test LLM selector for ensemble agents to decide which model to use depending on the game state or task.  
- [ ] Get Resources  
      - [ ] Open AI   
      - [ ] Claude  
      - [ ] Test other major reasoning models  
            - [ ] Gemini 2.5  
            - [ ] Claude 3.7 Thinking  
            - [ ] ? llama-3.1-nemotron-ultra-253b-v1

# Maxim Updates

## May 5

- Added Dragon chess engine support  
  - Level 1 is equal to 250 Elo at [chess.com](http://chess.com)  
    - To be clarified, which kind of game (there are different modes at [Chess.com](http://Chess.com))  
  - Tested Dragon vs Randon, Dragon vs Stockfish: [https://github.com/maxim-saplin/llm\_chess/tree/main/\_logs/misc/dragon](https://github.com/maxim-saplin/llm_chess/tree/main/_logs/misc/dragon)  
  - Tested multiple thinking LLMs vs Dragon (o3, o3-mini, o4-mini, Claude 3.7): [https://github.com/maxim-saplin/llm\_chess/tree/main/\_logs/dragon\_vs\_llm](https://github.com/maxim-saplin/llm_chess/tree/main/_logs/dragon_vs_llm)  
- Tested LLMs vs LLMs: [https://github.com/maxim-saplin/llm\_chess/tree/main/\_logs/llm\_vs\_llm](https://github.com/maxim-saplin/llm_chess/tree/main/_logs/llm_vs_llm)  
- Completed in-depth testing of NoN for 4.1 Mini \- performance degrades as number of workers grown  
- New models tested:  
  - o4-mini high is \#2 in LB  
  - 4 and 8 bit quants of Phi 4 Reasoning Plus \- DNF, NoN didn’t help

## Apr 20-27

- Added Gemini 2.5 \- in between R1 and Claude 3.7 \- slightly better win rates, slightly better than R1 (but worse than Claude 3.7) in instruction following   
  - Lags behind 01-mini  
  - OpenAI a hands-down leaders  
- Leaderboard \- added Extended view with more columns and visible column selection  
- NoN/Ensemble AI  
  - Completed and merged n-workers-to-1-synthesizer NoN agent  
  - Testing multiple model mixes  
  - Non-reasoning model  
    - Improve in game duration, no better chess games  
  - Reasoning models  
    - o4-mini performance drops either as synthesizer+worker of as worker with non-thinking synthesizer  
    - Non-reasoning synthesizer improves reliability, “cures” prompts and completions for Gemini 2.5 Pro, R1 14B, R1  
      ![][image5]  
    - \[TBD\] Gemini 2 Flash Thinking  
  - Overall, the current approach seems like quality gate improving stability, not bringing much reasoning/chess improvements  
    ![][image6]  
- Found issues with o4/o3 models tested last week the results turned to come with medium reasoning effort (param was not properly passed) \- fixed that

## Apr 14-20:

- Tested quite a few models through Sai’s Lab Keys  
  - Sai contributed a PR for an easier OpenAI config  
- OpenAI models  
  - GPT 4.5 \- nothing special, \~ 0 wins  
  - GPT 4.1 Mini and Nano \- added to leaderboard, Nano is bad Mini is better than predecessor (in terms of game duration)  
  - GPT 4.1 can’t qualify \- multiple random breakdowns due to *“'The model produced invalid content.”*  
    - Same issue when testing through my Azure OpenAI subscription  
  - **o3-low \[in-progress\]** \- looks very strong YET there are occasional timeout issues, even with increased to 20 minute timeout (default is 10), treating as losses as model fails to return reply. Current results make o3 favourable due to increased timeouts (suspect more losses to come in with default timeout)  
  - **o4-mini (low, medium, high)** \-  o4-mini is \#2 now. Interestingly, medium and high performed worse \- just a coincidence I think, all results are within MoE, reasoning effort doesn’t seem to give any difference compared to o3 mini. Great chess games and perfect instruction following (100% game duration)  
  - **o1-medium \-** is the new king. Game Duration is not 100% due to a single model glitch  
    - *“Invalid prompt: your prompt was flagged as potentially violating our usage policy”*  
- Gemini 2.5 Pro \- still can’t test, under Sai’s API key the limits allowed only 20 moves before exhausting the quote  
- Claude thinking  
  - Now there’s support for Extended thinking with Claude (llm\_chess and AG2)  
    - AG2 didn’t support Extended Thinking, I merged a PR in AG2, starting form 0.8.7 there’s the features  
  - Thinking mode didn’t impress, 1024, 2048 and 500 thinking budgets yielded results similar to R1 (yet with better instruction following) and not that different from one another  (within MoE) \- still way behind o1/o3/o4  
    - I’ve seen mediocre effects of enabling Claude thinking in coding, i.e. in [Aider Leaderboard](https://aider.chat/docs/leaderboards/) Claude 3.7 gets 60% vs 65% with extended thinking  
- ELO \- Discussed with Sai, still don’t see a way forward. Elo is not absolute, it’s pool dependent.  
  - There’s no such thing as a beginner human player Elo score or professional Elo player score UNTIL we anchor elo to certain pool, e.g. FIDE or US Chess Federation.  
  - If we want to get a [FIDE rating ELO](https://ratings.fide.com/top_lists.phtml?list=open), we might need someone who is in the leaderboard to play against a model(s) and then we might get model’s ELO estimation using some approximation formula/stat model  
- Add timing to generate\_reply \- way to measure and log response time   
- MoA agent renamed NoN agent (Network of Networks)  
- Stockfish vs o4-mini-low \[in-progress\]

## Apr 6-13:

- Add cost accounting (see below)   
  - \+ estimates of the runtime based on token stats and assumed generation speed (100 tok/s)  
- Introduced Matrix view (Y-Wins vs X-Game\_Duration) that visually splits reasoning models from the rest  
  - \+ LB UI now allows to fix at the top double clicked rows for easier comparison  
- Used win/draw/loss rates to simulate 100 chess game outcomes for LLM vs Random Player, based on this [calculated ELO](https://github.com/maxim-saplin/llm_chess/blob/main/data_processing/elo.ipynb) for all models  
- Simulated LLM vs LLM matches (GPT-4o Mini vs Haiku 3.5, swapping sides)  
- Implemented trivial compound ai agent inspired by Mixture-of-Agents approach (probing multiple LLMs and using synthesizer LLM to pick the best completion to user query), a config with 2 worker agents and 1 synthesizing agent. Tested a few setups (synthesizer, worker 1, worker 2 ):  
  - GPT 4o Mini Temp 0.3, GPT 4o Mini Temp 0.0, GPT 4o Mini Temp 1.0  
  - Haiku 3.5 Temp 0.3, Haiku 3.5 Temp 0.0, Haiku 3.5 Temp 1.0  
  - Haiku 3.5 Temp 0.3, Gemini Flash 2 Thinking, Haiku 3.5 Temp 0.3

  ![][image7]

  - KNOWN Issues: accounting for usage is suspicious, logs only contrans total stats (no breakdown between workers and synthesizer), no max turns in dialog respected (Haiku used to go beyond allowed 10 turns)  
  - Followup Idea: test thinking model \+ llm (1 worker \+ 1 synthesizer) yet in this case synthesizer just taking care of game communication protocol taming crazy mode. QwQ, R1 had troubles with instruction following, adding traditional model might mitigate the issue  
- New models  
  - Tested and added Haiku 3.5, looks really good, on par with larger 4o  
  - Mercury-coder-small \- diffusion LLM, on par with Gemma 3 27B  
    ![][image8]  
  - Llama 4 Scont through Cerebras \[in-progress\]  
    - Looks bad  
    - I have my suspicion towards Groq/Cerebras, I previously observed their Llama 3 models did poorly compared to llama.cpp/gguf I ran locally  
- **Key Struggle \- the reasoning eval**  
  - *Frame LLM Chess as a benchmarking task to evaluate LLM reasoning and instruction-following*  
  - So far the angles are somewhat naive:  
    - Reasoning is the key skill of chess players  
    - LLM Chess nicely splits models claimed as reasoning ones from the rest  
    - 

- Testing Ensembles:  
  - Claude Haiku  
  - O3 mini low  
  - Gemini Flash  
  - Gemma  
  - GPT 35  
  - Llama 7b/8b  
  - 

# Worth Mentioning

- Every LLM is tested against a random player multiple times, no LLM vs LLM has been tested for far  
- No move history, upon each move a fresh LLM dialog is started where a model can request and get the current board state  
  - There’s a flag that can include PGN state along with the unicode board, few tests with Gemini 2.0 Flash showed marginal improvement vs no history shared  
  - Testing Stockfish with no past moves shared showed no difference in performance  
- The board is presented upside down, this requires some spatial thinking from a model. It is usual to have chess boards with white pieces at the bottom. LLMs play as black and they get PoV on the board with black at the bottom.  
  - Some models (sometimes) can be confused with that, e.g. Deepseek V3 0324 occasionally dropped this sort of reflection  
    ![][image9]

# 

# Dollar Cost \+ Runtime, Leaderboard as of April 13

\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|   \# | Player                                 | Win/Loss   | Game Duration   |   Tokens | Cost/Game       | Time/Game   |   Games | Total Cost   |  
\+=====+========================================+============+=================+==========+=================+=============+=========+==============+  
|   1 | o1-2024-12-17-low                      | 78.70%     | 100.00%         |  1638.9  | $13.4843±1.6520 | 36.9m       |      47 | $633.76      |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|   2 | o1-preview-2024-09-12                  | 68.30%     | 93.00%          |  2660.1  | $22.5618±3.7627 | 58.1m       |      30 | $676.86      |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|   3 | o3-mini-2025-01-31-medium              | 67.00%     | 98.00%          |  2514.2  | $1.5487±0.2005  | 59.7m       |      44 | $68.14       |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|   4 | o1-mini-2024-09-12                     | 55.00%     | 89.50%          |  1221.1  | $2.4130±0.4098  | 30.5m       |      30 | $72.39       |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|   5 | gpt-4-32k-0613                         | 48.50%     | 100.00%         |     6.66 | $2.2266±0.0583  | 13.9s       |      33 | $73.48       |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|   6 | qwen-max-2025-01-25                    | 48.30%     | 100.00%         |     6.06 | $0.1336±0.0035  | 12.5s       |      60 | $8.01        |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|   7 | gpt-4o-2024-11-20                      | 47.90%     | 100.00%         |    50.58 | $0.3153±0.0127  | 1.7m        |      71 | $22.39       |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|   8 | claude-v3-5-sonnet-v2                  | 47.50%     | 97.60%          |    90.85 | $0.5820±0.0293  | 3.0m        |      60 | $34.92       |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|   9 | gpt-4-turbo-2024-04-09                 | 46.70%     | 100.00%         |     6.03 | $0.8482±0.0484  | 12.2s       |      30 | $25.45       |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|  10 | claude-v3-5-sonnet-v1                  | 46.70%     | 98.60%          |    80.42 | $0.5423±0.0305  | 2.6m        |      60 | $32.54       |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|  11 | gpt-4-0613                             | 45.50%     | 100.00%         |     6.57 | $1.0685±0.0604  | 13.3s       |      33 | $35.26       |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|  12 | gpt-4o-2024-08-06                      | 43.30%     | 99.50%          |     7.7  | $0.2081±0.0089  | 15.1s       |      60 | $12.49       |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|  13 | claude-v3-5-haiku                      | 42.90%     | 94.50%          |    65.09 | $0.1386±0.0086  | 2.1m        |      42 | $5.82        |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|  14 | moa-gpt-4o-mini                        | 41.70%     | 93.00%          | 42821.1  | $0.0000±0.0000  | 22.34h      |      30 | $0.00        |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|  15 | claude-v3-opus                         | 41.70%     | 86.80%          |    72.86 | $2.3216±0.3418  | 2.1m        |      30 | $69.65       |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|  16 | claude-v3-7-sonnet                     | 40.50%     | 92.80%          |   108.84 | $0.5759±0.0618  | 3.2m        |      42 | $24.19       |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|  17 | gpt-4o-2024-05-13                      | 40.00%     | 95.90%          |    31.34 | $0.2669±0.0132  | 1.0m        |      60 | $16.01       |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|  18 | o3-mini-2025-01-31-low                 | 33.10%     | 80.30%          |   678.95 | $0.5229±0.0523  | 18.2m       |      65 | $33.99       |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|  19 | deepseek-reasoner-r1                   | 32.30%     | 62.40%          |  4585    | $0.9375±0.2229  | 1.23h       |      31 | $29.06       |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|  20 | gpt-4o-mini-2024-07-18                 | 30.00%     | 77.00%          |   108.22 | $0.0219±0.0037  | 2.8m        |      30 | $0.66        |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|  21 | llama-3-70b-instruct-awq               | 25.00%     | 74.30%          |    41.61 | $0.0205±0.0029  | 1.1m        |      30 | $0.61        |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|  22 | gemini-2.0-flash-001                   | 21.60%     | 83.40%          |    93.77 | $0.0147±0.0011  | 2.6m        |      67 | $0.98        |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|  23 | grok-2-1212                            | 19.40%     | 61.50%          |    66.23 | $0.1904±0.0318  | 1.3m        |      49 | $9.33        |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|  24 | gemini-1.5-flash-001                   | 16.70%     | 42.90%          |    19.91 | $0.0034±0.0013  | 17.6s       |      30 | $0.10        |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|  25 | gemma-2-27b-it@q6\_k\_l                  | 13.30%     | 56.70%          |    55.04 | $0.0199±0.0043  | 1.0m        |      30 | $0.60        |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|  26 | gemma-2-9b-it-8bit                     | 6.70%      | 35.50%          |    58.12 | $0.0014±0.0005  | 42.2s       |      30 | $0.04        |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|  27 | deepseek-chat-v3-0324                  | 5.60%      | 36.20%          |   410.71 | $0.0470±0.0110  | 5.2m        |      45 | $2.11        |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|  28 | llama-3.3-70b                          | 4.80%      | 37.90%          |   102.98 | $0.0140±0.0039  | 1.2m        |      42 | $0.59        |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|  29 | qwen-plus-2025-01-25                   | 4.50%      | 43.80%          |   440.41 | $0.0728±0.0175  | 6.7m        |      33 | $2.40        |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|  30 | gemini-1.5-pro-preview-0409            | 3.70%      | 32.80%          |    13.38 | $0.1550±0.0417  | 9.2s        |      40 | $6.20        |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|  31 | gemini-2.0-flash-exp                   | 3.30%      | 42.90%          |   168.15 | $0.0115±0.0037  | 2.5m        |      30 | $0.35        |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|  32 | qwen2.5-72b-instruct                   | 3.30%      | 33.60%          |   219.47 | $0.0110±0.0029  | 2.5m        |      30 | $0.33        |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|  33 | llama3.1-8b                            | 1.70%      | 13.50%          |   162.1  | $0.0009±0.0001  | 46.1s       |      90 | $0.08        |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|  34 | gemini-2.0-flash-lite-001              | 1.50%      | 43.00%          |   150.15 | $0.0075±0.0013  | 2.2m        |      66 | $0.49        |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|  35 | deepseek-chat-v3                       | 1.40%      | 29.40%          |   246.93 | $0.0258±0.0055  | 2.5m        |      70 | $1.80        |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|  36 | gemini-2.0-flash-lite-preview-02-05    | 0.00%      | 27.50%          |   144    | $0.0044±0.0013  | 1.3m        |      39 | $0.17        |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|  37 | gemini-2.0-flash-thinking-exp-01-21    | 0.00%      | 20.30%          |    17.77 | $0.0015±0.0003  | 7.6s        |      33 | $0.05        |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|  38 | claude-v3-haiku                        | 0.00%      | 16.70%          |   210.64 | $0.0216±0.0035  | 1.2m        |      40 | $0.86        |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|  39 | gemma-3-12b-it@iq4\_xs                  | 0.00%      | 14.90%          |   111.14 | $0.0000±0.0000  | 34.7s       |     134 | $0.00        |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|  40 | chat-bison-32k@002                     | 0.00%      | 13.20%          |    31.64 | $0.0000±0.0000  | 8.8s        |      36 | $0.00        |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|  41 | qwq-32b                                | 0.00%      | 12.30%          |  8158    | $0.0433±0.0099  | 35.1m       |      33 | $1.43        |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|  42 | mistral-small-24b-instruct-2501@q4\_k\_m | 0.00%      | 10.20%          |   110.95 | $0.0000±0.0000  | 23.7s       |      42 | $0.00        |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|  43 | qwen-turbo-2024-11-01                  | 0.00%      | 10.20%          |   192.37 | $0.0016±0.0003  | 41.3s       |      33 | $0.05        |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|  44 | gemma-3-12b-it@q8\_0                    | 0.00%      | 9.90%           |   151.11 | $0.0000±0.0000  | 27.3s       |      67 | $0.00        |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|  45 | llama3-8b-8192                         | 0.00%      | 7.50%           |    57.02 | $0.0004±0.0001  | 9.0s        |      60 | $0.03        |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|  46 | gemma2-9b-it-groq                      | 0.00%      | 7.40%           |    20.22 | $0.0020±0.0006  | 3.1s        |      35 | $0.07        |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|  47 | sky-t1-32b-preview                     | 0.00%      | 6.90%           |  1216.2  | $0.0000±0.0000  | 2.9m        |      30 | $0.00        |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|  48 | qwen2.5-14b-instruct@q8\_0              | 0.00%      | 6.60%           |   150.63 | $0.0096±0.0023  | 21.0s       |      30 | $0.29        |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|  49 | amazon.nova-pro-v1                     | 0.00%      | 5.90%           |   177.19 | $0.0000±0.0000  | 21.9s       |      33 | $0.00        |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|  50 | mercury-coder-small                    | 0.00%      | 5.90%           |   837.81 | $0.0000±0.0000  | 1.7m        |      42 | $0.00        |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|  51 | gemma-3-27b-it@iq4\_xs                  | 0.00%      | 4.80%           |   115.84 | $0.0000±0.0000  | 11.8s       |      67 | $0.00        |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|  52 | qwen2.5-7b-instruct-1m                 | 0.00%      | 4.80%           |   140.79 | $0.0001±0.0000  | 14.3s       |      42 | $0.00        |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|  53 | ministral-8b-instruct-2410             | 0.00%      | 4.70%           |    72.11 | $0.0000±0.0000  | 7.1s        |      30 | $0.00        |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|  54 | mistral-small-instruct-2409            | 0.00%      | 4.50%           |    88.24 | $0.0003±0.0001  | 8.4s        |      30 | $0.01        |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|  55 | qwq-32b-preview@q4\_k\_m                 | 0.00%      | 4.00%           |  2908    | $0.0117±0.0023  | 4.1m        |      30 | $0.35        |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|  56 | phi-4                                  | 0.00%      | 3.90%           |   333.54 | $0.0006±0.0001  | 27.1s       |      30 | $0.02        |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|  57 | qwen2.5-14b-instruct-1m                | 0.00%      | 3.70%           |   235.27 | $0.0085±0.0016  | 18.4s       |      42 | $0.36        |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|  58 | mistral-nemo-12b-instruct-2407         | 0.00%      | 3.40%           |    47.7  | $0.0000±0.0000  | 3.4s        |      30 | $0.00        |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|  59 | amazon.nova-lite-v1                    | 0.00%      | 2.30%           |   534.38 | $0.0000±0.0000  | 25.9s       |      42 | $0.00        |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|  60 | gpt-35-turbo-0613                      | 0.00%      | 2.10%           |    93.63 | $0.0027±0.0008  | 4.1s        |      30 | $0.08        |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|  61 | granite-3.1-8b-instruct                | 0.00%      | 2.10%           |   469.13 | $0.0029±0.0006  | 20.7s       |      30 | $0.09        |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|  62 | gpt-35-turbo-1106                      | 0.00%      | 1.80%           |    48.32 | $0.0011±0.0003  | 1.8s        |      30 | $0.03        |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|  63 | internlm3-8b-instruct                  | 0.00%      | 1.80%           |  1543.9  | $0.0125±0.0028  | 58.4s       |      30 | $0.38        |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|  64 | llama-3.1-tulu-3-8b@q8\_0               | 0.00%      | 1.80%           |  1996.3  | $0.0013±0.0002  | 1.2m        |      42 | $0.05        |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|  65 | deepseek-r1-distill-qwen-32b@q4\_k\_m    | 0.00%      | 1.80%           |  2173.8  | $0.0020±0.0004  | 1.4m        |      30 | $0.06        |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|  66 | deephermes-3-llama-3-8b-preview@q8     | 0.00%      | 1.60%           |   101.36 | $0.0014±0.0003  | 3.5s        |      42 | $0.06        |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|  67 | gpt-35-turbo-0125                      | 0.00%      | 1.40%           |    82.02 | $0.0018±0.0004  | 2.5s        |      30 | $0.06        |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|  68 | deepseek-r1-distill-qwen-14b@q8\_0      | 0.00%      | 1.30%           |  3073.1  | $0.0019±0.0002  | 1.4m        |      30 | $0.06        |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|  69 | gemini-2.0-flash-thinking-exp-1219     | 0.00%      | 1.20%           |   724.54 | $0.0010±0.0003  | 17.7s       |      30 | $0.03        |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|  70 | gpt-35-turbo-0301                      | 0.00%      | 1.10%           |    67.06 | $0.0012±0.0001  | 1.6s        |      30 | $0.04        |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+  
|  71 | llama-2-7b-chat                        | 0.00%      | 1.10%           |   116.31 | $0.0001±0.0000  | 2.6s        |      30 | $0.00        |  
\+-----+----------------------------------------+------------+-----------------+----------+-----------------+-------------+---------+--------------+

Total cost across all models: $1905.70

METRICS EXPLANATION:  
\- Win/Loss: Difference between wins and losses as a percentage (0-100%). Higher is better.  
\- Game Duration: Percentage of maximum possible game length completed (0-100%). Higher indicates better instruction following.  
\- Tokens: Number of tokens generated per move. Shows model verbosity/efficiency.  
\- Cost/Game: Average cost per game with margin of error. Lower is more economical.  
\- Time/Game: Estimated time per game (output at 100 tok/s \+ 5% input processing time).  
\- Total Cost: Total cost across all games for this model.