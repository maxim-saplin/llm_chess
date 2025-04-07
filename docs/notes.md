# April 7, 2025: Matrix View

In addition to a Leaderboard offering simple ranking along the Win/Rate axis (capturing both instruction following/prompt stability and chess proficiency), the 2D view offers a look at models through:
- **Win Rate**, vertical axis, measures chess proficiency. It relaxes the Win/Rate from the leaderboard focusing solely on games where the model succeeded no matter the number of losses (most of them are technical losses due to violation of the game communication protocol anyway).
- **Game duration** horizontal axis - the secondary metric from the leaderboard, shows how durable the LLM is and if it can stay in the game loop without breaking the loop due to a random hallucination.

Hence vertical axis is chess proficiency/reasoning while horizontal is instruction following/durability.

Now there are 3 areas/clusters. Top right is occupied by OpenAI reasoning models (`o1`, `o3-mini`) demonstrating both good chess games and instruction following stability. Bottom right is where SOTA non-reasoning models (e.g. `GPT-4o`, `Claude Sonnet 3.7`) are gathered - they are fine making the moves yet struggle to make a win. The bottom left is where the majority of weak models are clustered, poor instruction following and hence no wins.

The Matrix view nicely splits the reasoning models from the rest, they are the only models that have non-zero win rates. Besides there are outliers, such as `R1`. It did score a reasonable number of wins yet it failed quite often breaking the game loop - I view it as some crazy wise man, can play chess decently yet sometimes loses sense of reality and starts mumbling nonsense. As for other "reasoning" models, such as `QwQ-32B` or `Gemini 2 Flash Thinking`, they are at the bottom left part, struggling to stay in the game - they do not qualify for any meaningful games due to poor instruction following.

# March 22, 2025: Metric Overhaul and Leaderboard Redesign

After months of testing various LLMs on chess games, I've completely redesigned the leaderboard and metrics to better capture what we're actually measuring. With the old approach the metrics weren't clearly communicating what they represented.

Two key insights drove this change:

1. We're simultaneously measuring TWO distinct abilities: chess skill AND instruction following capability
2. The previous metrics blended these abilities in confusing ways

The redesigned leaderboard now uses these core metrics:

- **Win/Loss**: This is now our primary ranking metric (0-100%). It combines BOTH chess skill AND instruction following ability. A model needs both to score well - understanding chess strategy AND adhering to the protocol correctly. 50% means equal wins/losses, higher scores indicate more wins than losses. This replaces the previous "Wins-Losses" metric but with clearer explanation of what it represents.

- **Game Duration**: This specifically isolates instruction following reliability (0-100%). A score of 100% means the model either completed a full game naturally or reached maximum 200 moves without protocol errors. Lower percentages indicate the model broke down in communication as the game progressed. This better captures what we previously tried to measure with "Avg Moves" but in a more intuitive way.

- **Tokens**: Unchanged, but with better explanation that this measures verbosity which can indicate either detailed reasoning (for stronger models) or garbage generation (for weaker ones).

This redesign eliminates several confusing aspects of the previous leaderboard:

- Clearer separation between chess skill and instruction following metrics
- Consistent 0-100% scale for main metrics making comparisons more intuitive
- No more confusion about whether higher or lower "Avg Moves" is better, or how to interpret "Mistakes" (per 1000 moves) absolute values

The reorganization also better showcases how some models (like GPT-4-32k-0613) can achieve perfect instruction following (100% Game Duration) while demonstrating mediocre chess strategy (48.5% Win/Loss). OR how Deepseek R1 while achieving solid Win rates (22%) also demonstrated horrible game stability (losing in 58% games due to game loop interruptions and multiple haluscinations) - something that was harder to discern in the previous format.


# March 9, Claude 3.7 Sonnet

The model took its place near the top of the list, yet it is behind Sonnet 3.5 v1 in terms of wins.
If you consider the rest of the metrics, I would place it below both `Sonnet 3.5 v1` and `v2`—it produced
significantly more mistakes (8.95 vs. 1.67 for v1 and 2.98 for v2) and became more verbose
(109 tokens vs. 80 for v1 and 91 for v2). Additionally, the model tends to lose more often (23% vs. 13% for v1 and 8% for v2).
I have noticed that there were 5 cases of "too many wrong actions" where the game failed to recover and persistently
selected illegal moves despite having requested the list of legal moves. A closer look showed that the model fabricated incorrect
positioning of the pieces in its head (e.g., not using the white side for ranks) and failed to realize its mistake
in subsequent retries—something not observed in previous versions.

Overall, it seems that for 3.5 v2 and 3.7, Anthropic made some compromises. While the models might perform better ерфе 3.5 v1 in
the set of benchmarks they used fro optimizations, based on LLM Chess, I think the reasoning and durability took a hit in newer Sonnet models 
— one might expect more surprises from newer models in production with diverse inputs.

# March 3, o1 Leads the Pack

The release version of OpenAI's `o1` at LOW reasoning effort has beaten `o1-preview` tested last year. With a win rate of 56% (vs. 47% for the release version), the model demonstrated better overall performance — 0 losses and 0 mistakes! At low reasoning effort, it generated on average 1641 completion tokens per move, which is significantly less than `o1-preview` and `o3-mini` (at medium reasoning effort). Curious what medium and high levels of `o1` can demonstrate...

o1 model (unlike o3) doesn't disdain to request both the board and list of legal moves before issuing the make move command. Below is the ratio of get board to get moves actions, higher values mean that the model only requested the printout of the board and didn't care to get the list of legal moves (deciding on the next move withount a hint). Requesting the list of legal moves can explain the 0 mistake rate of o1:
- o1-2024-12-17-low: 1.013
- o3-mini-low: 1.375
- o3-mini-medium: 2.613
- o3-mini-hard: 45.1
- o1-mini: 1.465

Besides the `o1` model, I also tested a few other models:

- Tested and added a release version of `gemini-2.0-flash-lite-001`, way better steerability and stability than the preview/experimental version, even 1 occasional win. I have observed a similar step change from 'exp' (preview) to '001' (release) version with `Gemini Flash 2.0`, when the first previews were garbage in terms of steerability.

- I also tried a preview of the flagship `Gemini 2.0 Pro` model (`2025-03-01_gemini-2.0-pro-exp-02-05`), yet the tests were riddled with odd "Service is not available" errors. I'm done with 'exp' variants of Google models—too much fuss.

- I made an attempt to evaluate another "thinking" model from a Chinese AI lab `MoonshotAI`—to no avail. The model struggled with basic instruction following; it also failed to properly enclose the thinking tokens with ◁think▷ sections (yeah, they used some Unicode triangles)—something observed with distilled `R1` models.

- `o3-mini` at high reasoning effort still can't reliably pass tests, this time due to some security filter errors happening occasionally (Invalid prompt: your prompt was flagged as potentially violating our usage policy. Please try again with a different prompt).

- Tested a yet another "best in class" fine-tune of `LLama 3`—`deephermes-3-llama-3-8b-preview@q8` - bottom of the list. It follows the trend of a fine-tuned version demonstrating top results in popular evals yet being horrible in LLM Chess (and verbose).

# February 12, Legacy GPT-4, get_current_board vs. get_legal_moves

The results for `gpt-4-0613` and `gpt-4-32k-0613` show they performed well, making zero mistakes and achieving numerous draws. 
However, older GPT-4 models completely ignored the opportunity to request the board state (`get_current_board` action), instead relying solely 
on the list of legal moves (`get_legal_moves` action) to make their moves immediately - mimicing the behavior of the random bot, mechanisitcally getting the list of moves and mechanistically picking one. Upon closer examination of outputs from few models, 
it was observed that reasoning models (`r1`, `o1`/`o3`) predominantly used `get_current_board`, demonstrating confidence in their ability to decide 
on a legal move without needing additional hints (by requesting `get_legal_moves`). For `o3` models, this confidence increased with higher reasoning effort. 
The majority of "traditional" LLMs (`GPT-4o`, `Claude 3.5 Sonnet`) utilized both `get_current_board` and `get_legal_moves` before making a move.

Here are the ratios for the number of actions issued by models, get_current_board/get_legal_moves:
- o3-mini-low: 1.375
- o3-mini-medium: 2.613
- o3-mini-hard: 45.1
- o1-mini: 1.465
- deepSeek-r1: 1.938
- gpt-4-32k: 0.006
- qwen-max-2025-01-25: 0.997
- gemini-2.0-flash-001: 0.952
- anthropic.claude-v3-5-sonnet-v2: 0.999
- gpt-4o-2024-11-20: 0.999

# February 10, OpenAI o3-mini

Testing `o3-mini` turned out to be a challenge, with plenty of errors. Some were timeout issues (tried 120 and 250 seconds), 
something I haven't seen with supposedly weaker (in terms of infrastructure) `Deepseek R1`, and never observed when testing other OpenAI models through Azure.
Had to ignore plenty of logs due to such interruptions.
The other errors were due to the server dropping the connection during the generation of the reply, treating these issues as model errors and giving a loss...

- Only low and medium reasoning efforts have been tested; most of the high modes ended up with timeout issues. Might retest in the future.

- `o3-mini` at low reasoning effort (`o3-mini-2025-01-31-low`) didn't impress, performing at the level of `Claude 3.5`/`GPT-4o`, yet with plenty of errors.

- `o3-mini-2025-01-31-medium`, on the other hand, is an interesting case. It took place right between `o1-preview-2024-09-12` and `o1-mini-2024-09-12`, demonstrating way fewer mistakes, suggesting better steerability.

- `o3-mini-2025-01-31-medium`, unlike the `o1` models, didn't score a single loss. It also maintained a greater material count by the end of each game. Yet, it often struggled to complete games where it dominated (resulting in stalemates and insufficient material).

- Low reasoning mode produced almost 4 times fewer tokens than medium (676 tokens per move vs. 2535), still way more tokens than `anthropic.claude-v3-5-sonnet-v1` (80).

# February 09, 2025: Google Gemini 2 Progress

Google made great progress with their Gemini 2 models. While the preview models initially looked mediocre, they have now performed much better!

- On **Feb 5, 2025**, they introduced a release version of `Gemini 2.0 Flash` (`gemini-2.0-flash-001`), as well as a preview of the smaller `Gemini 2.0 Flash Lite` (`gemini-2.0-flash-lite-preview-02-05`).

- `gemini-2.0-flash-001` performed significantly better than the preview version from December.
  - `gemini-2.0-flash-exp` on average lasted for 86 moves, while `gemini-2.0-flash-001` lasted for 159 moves.
  - A similar improvement was observed for `gemini-2.0-flash-thinking-exp-1219` (which was at the bottom of the list) and `gemini-2.0-flash-thinking-exp-01-21` (which performed better but was still subpar).
  - `gemini-2.0-flash-thinking-exp-01-21` exhibited odd instability, often failing to produce replies and returning empty messages around 50 moves.

- `gemini-2.0-flash-lite-preview-02-05` was disappointing, performing worse in evaluations than local runs of `Gemma 2 9B` and `27B`.

- `gemini-2.0-flash-001` ranked near the top of the leaderboard, between `Claude 3.5` and `GPT-4o`, due to scoring 3 wins in 67 games.
  - However, I wouldn't consider it equal to the top models from Anthropic and OpenAI. `Gemini 2.0 Flash` performed worse overall, achieving only 34% draws and suffering too many losses. It made mistakes too often and broke the game loop on average at 159 moves, whereas `Claude` and `GPT-4o` almost never broke the loop.

- Revisiting the ranking is necessary, as using Win Rate as the key metric can place models that are worse overall above better-performing ones.

# February 6, 2025: Amazon Nova, Tulu

I had the opportunity to test a few models from December 2024. Amazon released their state-of-the-art Nova models: 
`amazon.nova-pro-v1` and `amazon.nova-lite-v1`. Additionally, there was mention of "best-in-class" Tulu fine-tunes of Llama 3 models. 
Unfortunately, none of these models lived up to expectations:

- **Nova models**: Both Pro and Lite versions performed poorly, 
breaking the game loop at an average of just 11.76 moves for Pro and 4.62 moves for Lite.
They exhibited poor steerability and stability. It's difficult to understand how these models were rated
so highly across various benchmarks during their presentation.

- **Tulu** (`llama-3.1-tulu-3-8b@q8_0`): As is often the case with fine-tunes, 
Tulu performed worse than the original model. It overwhelmed responses with verbosity, generating 1996.33 tokens per 1000 moves compared
to just 162.1 tokens for the original `llama3.1-8b` model.

# February 2, 2025: Alibaba's Qwen

- Tested `Qwen-Max`, `Qwen-Plus`, `Qwen-Turbo`, `Qwen2.5-14B-Instruct`, `Qwen2.5-72B-Instruct`, and `Qwen2.5-7B-Instruct`.

- `Qwen-Max` impressed demonstrating perfect instruction following while reaching the best Win-Loss rate among non-reasoning models.

# January 24, 2025: x.ai's Grok

- Added `Grok-2` results (`grok-2-1212`), and it scored 2 wins in 32 games.
  - Latter I've added 17 more runs, no more wins, win rate and material diff went a bit down.

- Originally, I adhered to exactly 30 game runs per model. Recently, I have been conducting more runs
where possible (and financially reasonable—some models can be extremely expensive).

- More runs to some models might provide them with an advantage.
For instance, if a model is weak in chess and can barely score a single win, 
additional runs increase the chances of an occasional win, giving this model
an automatic edge over other models (potentially better all-around models)
that consistently achieve draws.

- `grok-2-1212`, with a 6% win rate, places the model at the top of the list among
other non-reasoning models (`GPT-4o`, `Claude 3.5 Sonnet`), yet it has a low draw rate.
The reason for this is that `Grok-2` sometimes fails to follow instructions, 
neglecting to pick the correct move from the list of legal ones (which it had responsibly requested).
Could this be due to the tokenizer or some "SolidGoldMagikarp" out-of-distribution token
combination?

- Despite this, `Grok-2` is an intriguing non-reasoning model. It maintained a positive 
material count throughout the games (with a material difference of 2.63).

- Example of `Grok-2` failing to pick a legal move and hallucinating one not on the list:

<div class="expandable-snippet">
    <button class="toggle-snippet" onclick="toggleSnippet(this)">Show Snippet</button>
    <pre class="snippet" style="display: none;">
<span style="color:green">Player_Black (to Proxy):</span>

Thank you for providing the current board status. Now, I'll check the legal moves available to me. Please provide the result of 'get_legal_moves'.

--------------------------------------------------------------------------------
<span style="color:green">Proxy (to Player_Black):</span>

h8g8,f8e7,f8d6,f8c5,f8b4,f8a3,e8d8,e8e7,e8d7,a8d8,a8c8,a8b8,e5e7,e5f6,e5e6,e5d6,e5g5,e5f5,e5d5,e5c5,e5b5,e5a5,e5f4,e5e4,e5d4,e5g3,e5c3,e5h2,e5b2,e5a1,h7g6,h7h6,c7c6,b7b6,a7a6,h7h5,c7c5,b7b5,a7a5

--------------------------------------------------------------------------------
<span style="color:green">Player_Black (to Proxy):</span>

After reviewing the current board and the list of legal moves, I will make my move. I choose to move the knight from e5 to f3, attacking the king and potentially setting up a fork. Please execute 'make_move e5f3'.

--------------------------------------------------------------------------------
<span style="color:green">Proxy (to Player_Black):</span>

Failed to make move: illegal uci: 'e5f3' in r3kb1r/ppp3pp/6P1/4q1N1/P3N3/1P1p3P/R1pP1P2/2B2K1R b - - 0 26

--------------------------------------------------------------------------------
<span style="color:green">Player_Black (to Proxy):</span>

Apologies for the mistake. Let me correct my move. I will move the knight from e5 to d3, which is a legal move and aims to challenge the opponent's control of the center. Please execute 'make_move e5d3'.

--------------------------------------------------------------------------------
<span style="color:green">Proxy (to Player_Black):</span>

Failed to make move: illegal uci: 'e5d3' in r3kb1r/ppp3pp/6P1/4q1N1/P3N3/1P1p3P/R1pP1P2/2B2K1R b - - 0 26

--------------------------------------------------------------------------------
<span style="color:green">Player_Black (to Proxy):</span>

I apologize for the confusion. Let me review the legal moves again and choose a different move. I will move the queen from e5 to e2, which is a legal move and aims to put pressure on the opponent's position. Please execute 'make_move e5e2'.

--------------------------------------------------------------------------------
<span style="color:green">BREAKING >>> Failed to make move: illegal uci: 'e5e2' in r3kb1r/ppp3pp/6P1/4q1N1/P3N3/1P1p3P/R1pP1P2/2B2K1R b - - 0 26</span>
<span style="color:green">Proxy (to Player_Black):</span>

Too many wrong actions
    </pre>
</div>

# January 22, 2025: R1 Challenges o1, thinking "surrogates"

Released on January 21, `DeepSeek-R1` made a significant impact by showing similar
or even better performance than OpenAI's `o1` models across a range of math and
coding benchmarks. All of this comes at a fraction of the cost when accessing
their 671B model through their API. Besides, the model weights are open, and
there are plenty of details about the training process—a stark contrast to
OpenAI's secrecy regarding the `o1/o3` family of models. And that's not all! For
those interested in local models, there are smaller "distilled" reasoning models
at 70B, 32B, 14B, etc., sizes.

So far, none of the so-called reasoning or thinking models have come close to `o1`
(`qwq-32b-preview`, `sky-t1-32b-preview`, `gemini-2.0-flash-thinking-exp-1219`). They
were a step back in instruction following and could hardly be steered when
compared to non-thinking models. Let alone, they didn't perform as well in chess.
I call them surrogates, verbosity generators mimicking but not replicating `o1`'s
behavior.

Deepseek-R1 (`deepseek-reasoner-r1`) was an extremely curious model to test, and
now there are evaluation results in the Leaderboard.

Additionally, Google has just released an update to its Gemini 2.0 Thinking Model
(`gemini-2.0-flash-thinking-exp-01-21`), which previously showed poor results. Two
very interesting releases in two days...

**NOTES:**

- There are now three models in a league of their own: `o1-mini`, `o1-preview`, and now
`deepseek-reasoner-r1`. These are the only models with significant wins (>10%) and
maintaining a positive material difference (~9) as opposed to a negative material
difference for the resetGameInterval.

- `deepseek-reasoner-r1` is much more verbose (almost twice as many tokens as `o1`) and
also makes more mistakes. Many games were lost due to the model making mistakes,
unlike `o1` models, which mostly fell out of the games due to losing or drawing
(e.g., stalemate, insufficient material).

- `deepseek-reasoner-r1` showed distinctive behavior: sometimes it made moves without
requesting the board state or legal moves list (i.e., issues make_move action in
the very first response), sometimes it only requested the board state without
getting the list of moves and decided on the move without a hint (in some cases
picking the right move, in others wrong).

- Overall, `o1` models are better all-round models (compared to R1), with better chess
performance, as well as instruction following (Mistakes) and Durability (not
falling out of the games, doing more moves on average).

- The rest of the "thinking" models (`sky-t1-32b-preview@q4_0`, `qwq-32b-preview@q4_k_m`,
`deepseek-r1-distill-qwen-32b@q4_k_m`, `deepseek-r1-distill-qwen-14b@q8_0`,
`gemini-2.0-flash-thinking-exp-1219`) can hardly follow prompt instructions, lasting
on average 2~14 moves.

- Distilled dense 14B and 32B versions of `Deepseek-R1` (`deepseek-r1-distill-qwen-32b@q4_k_m`,
`deepseek-r1-distill-qwen-14b@q8_0`) did not impress—very poor instruction following,
not even close to the full 671B MoE model. Could quantization have an effect?
Don't know.

- Distilled R1 models use `<think></think>` tags to enclose
"reasoning" tokens (those ones hidden for `o1`), sometimes they fail to put the
opening `<think>` tag (most often in the very first reply).

- The new Gemini Thinking model (`gemini-2.0-flash-thinking-exp-01-21`) did improve a
lot in instruction following. While the previous December version
(`gemini-2.0-flash-thinking-exp-1219`) was almost useless, staying in the game on
average for 2.3 moves (i.e., breaking instruction prompts in the 2nd move it was
asked to make), the new model lasted on average 40 moves and showed far fewer
mistakes.

In terms of chess, the newer `gemini-2.0-flash-thinking-exp-01-21` showed a negative
material difference and negligible draw count—way below other non-thinking models
(even Google's own Gemma 2 9B).

- `gemini-2.0-flash-thinking-exp-01-21` also demonstrated much less verbosity in the
outputs, providing to-the-point answers. Didn't investigate it deeply, yet it
seems that now Gemini Thinking does proper isolation of reasoning tokens. Per
[docs](https://ai.google.dev/gemini-api/docs/thinking), "On a standard
request, the model responds with two parts, the thoughts and the model response.
You can check programmatically if a part is a thought or not by seeing if the
part.thought field is set to True." Autogen doesn't seem to register thought
tokens in completion stats for Flash Thinking while it does so for R1.

- Most of the failures/losses from `gemini-2.0-flash-thinking-exp-01-21` 
were due to server errors. Occasionally, the server returned an empty message or flagged 
the request with a "RECITATION" error, among others. 
Clearly, there's some instability in generation on the server side.

- Earlier non-`o1` thinking models did not do well with splitting the reasoning/thinking part
from the final answer, R1 and newer Gemini Thinking do that (yet it didn't help
the distilled R1 models).

# January 21, 2025: More Models, More Tests

- Added the new Claude 3.5 Sonnet (`claude-v3-5-sonnet-v2`) and also retested the previous version (`claude-v3-5-sonnet-v1`), giving them more runs
(60 this time). What surprised me was not just the fact that `v2` showed some wins, but that `v1` demonstrated even more wins 
(although losing to the random player more often). 
Back in November, when I did 30 runs of Sonnet 3.5, there were 0 wins. 
Did Anthropic change something in `v1` as well, or was it just a question of stochasticity?

- Conducted more runs of GPT-4o models (`gpt-4o-2024-05-13`, `gpt-4o-2024-08-06`, `gpt-4o-2024-11-20`). The August version also achieved a win, yet
it also had its first non-zero mistake (previous 30-run result had a perfect 0 mistakes) - this time, that happened due to Azure's content
filter halting one of the games.

- OpenAI's and Anthropic's models are still the most durable models, i.e.,
demonstrating the least number of mistakes, staying in almost all games
until the very end without falling off due to a random glitch/hallucination
or breaking the prompt instructions. Clearly, it is a challenge for most models
to sustain a 100-turn (200-move game) with an average of 3-4 dialog interactions per game turn.

- Deepseeks R1 distilled into 32B Qwen (`deepseek-r1-distill-qwen-32b@q4_k_m`) didn't perform well
- barely able to move past a couple of turns in the chess game, no better than `QwQ` or Flash Thinking.

- `o1` models are still special being the only models maintaing positive material diff (gaining more piaces rather than losing them)
versus most other models having a significant negative diff suggesting the wins for non-`o1` models can hardly be attributed
to models reasoning performance (i.e. with the models meaningfully moving the pieces rather than faking a game).

# January 16, 2025: First wins by non-reasoning model

The November 2024 update to `GPT-4o` demonstrated a few wins, something non-o1 models couldn't do before. Yet, what is curious is that the updated
model not only scored wins but also lost to the Random Player more often than others.

# January 14, 2025: Reasoning Models, First Wins

In my initial notes (see below), I expressed skepticism about LLMs ever being capable of achieving meaningful wins against a Random Player 
(let alone a dedicated chess engine). I also mentioned the ARC Challenge as a similar benchmark that is difficult or unsolvable by LLMs.
Yet, in late December 2024, OpenAI introduced their o3 model, which excelled in 
[ARC-AGI-1](https://arcprize.org/blog/oai-o3-pub-breakthrough).

Around the same time, I received API access to o1-mini, and it was impressive! o1-mini scored 9 wins in 30 games (30%), 
making it the first model capable of meaningful chess games. Next, I tried o1-preview, achieving an even more impressive 46.7% win rate.

The o1 models did something different; they played a meaningful game rather than randomly moving pieces on the board as 
seen with older "non-reasoning" models. They formed a league of their own—a "strong" model capable of winning.

I also tested a number of other reasoning models introduced after o1—Google's Gemini 2.0 Flash Thinking (via API), 
QwQ 32B (4-bit quantized via LM Studio), and Sky T1 32B (also 4-bit quantized via LM Studio).
The results were underwhelming, to say the least—those 3 models couldn't complete even a single game, often failing 
after a few moves (due to breaking the communication protocol or making illegal moves).
Just like the o1 models, they produced lots of tokens, yet unlike o1, 
which seems to have 2 separate stages—thinking (those hidden tokens) and producing the 
final answer—the other "thinking" models just stream lots of tokens without caring about 
following any instructions as to what they are asked to produce.
Verbosity and failing to adhere to instructions seem to plague not just the o1 competitors 
but also newer models (e.g., check Deepseek v3).

**NOTES:**

- When LLMs achieve a 90% win rate against a Random Player, I will replace it with Stockfish.
- You can find conversation logs for 
o1-mini [here](https://github.com/maxim-saplin/llm_chess/blob/main/_logs/no_reflection/_21.12.2024_o1-mini-2024-09-12/output.txt) 
and for o1-preview [here](https://github.com/maxim-saplin/llm_chess/blob/main/_logs/no_reflection/_03.01.2025_o1-preview-2024-09-12_2/output.txt)

- Conversation logs for [Gemini 2.0 Thinking](https://github.com/maxim-saplin/llm_chess/blob/main/_logs/no_reflection/_09.01.2025_gemini-2.0-flash-thinking-exp-1219/output.txt),
[QwQ](https://github.com/maxim-saplin/llm_chess/blob/main/_logs/no_reflection/_14.01.2025_sky-t1-32b-preview_q4-0/output.txt)
and [Sky T1](https://github.com/maxim-saplin/llm_chess/blob/main/_logs/no_reflection/_14.01.2025_sky-t1-32b-preview_q4-0/output.txt)

- While o1 models used a lot of tokens (1221 tokens per move for o1-mini and 2660 
for o1-preview vs. below 100 tokens for an average model), their replies were concise (most of the tokens 
were hidden ones) and had few mistakes.

- OpenAI models might have an advantage over other models because the prompts have been crafted with GPT-4 models.
This might explain why many models perform worse. Contrary to this point, there are non-OpenAI models (e.g., Anthropic)
that do not struggle with instruction following. I believe the factor of prompts and adjusting prompts for each specific model plays a minor role.

- An idea: while other (non-o1) reasoning models might be poor instruction followers, why 
not introduce a deliberate step of final answer synthesizing? I.e., use a cheaper LLM (e.g., 4o-mini) 
to get the long scroll from a reasoning model and prompt it to produce a final answer. 
Will the reasoning models show better chess abilities?

# November 12, 2024: Initial Observations, Opinion

Language Models can make moves in a chess game, but they cannot actually play chess or progress towards a victory. 
The experiment started after taking a class at DeepLearning, which taught the Microsoft Autogen framework. One of the classes demonstrated
a simulation of a chess game between LLMs. I was immediately intrigued by the idea of putting different LLMs head-to-head in a chess game competition. 
However, I was surprised that the naive prompting strategy from the class never led to a game completion. Extending prompts didn't help. 
I ended up testing LLMs' performance in a chess game using a Random Player. A human player with reasonable chess skills would have no problems winning 
against a random player, yet LLMs failed miserably in this competition.

I suspect that crushing this "LLM Chess" eval might be as hard as the [ARC Challenge](https://arcprize.org)—a benchmark created to demonstrate 
the true nature of text-generating LLMs, exploit their weaknesses, and show how LLMs struggle with reasoning. "It's easy for humans, but hard for AI."

LLMs and Transformer-based models can be trained specifically to play chess. There are projects on the internet where people have fine-tuned LLMs
as chess players. Yet, those are specialized models that can't be good chat models.

I am looking forward to testing new releases of SOTA and frontier models. It would be great to see a model that starts scoring wins against
the chaos monkey while maintaining performance at traditional chat tasks.

**NOTES:**

- More data on game simulations is available [here](https://github.com/maxim-saplin/llm_chess/blob/main/docs/_data/refined.csv) and 
[here](https://github.com/maxim-saplin/llm_chess/blob/main/docs/_data/aggregate_models.numbers).

- No history of moves is available to LLM, no reflection used (giving the model "time to think").

- Experiments with reflection suggest that LLMs do even worse when they are prompted to evaluate options before making a move
([reflection results](https://github.com/maxim-saplin/llm_chess/blob/main/_logs/_not_OK_logs/reflection/aggregate_results.csv)).
Could LLMs improve their performance if given the whole log of the game?

- The chess engine ([Stockfish](https://stockfishchess.org)) has a 100% win rate with an average game taking 32 moves to complete.

- Stockfish 17, macOS, 0.1ms time limit (vs 0.1s default) - with decreased performance, Stockfish dominates over Random Player.

- Random Player (as white) wins over Random Player (as black) in 10.5% of cases - LLMs scored 0 wins.

- Indeed, giving the right of the first move gives an advantage to the white player.

- LLMs do worse than random players.

- It's as if an LLM had no goal to win, as if it was its intention to keep the game going. What if I prompted it and told it that 200 moves is the maximum and the game ends after? Would it try harder? Can adding to a system prompt an explicitly instruction to Win help?

- While some models are less verbose and follow the rules strictly (e.g., OpenAI), others are verbose.

- Initially, I used exact match when communicating with an LLM and prompted it to reply with action names (show board, get legal moves, make move) - worked well with OpenAI.

- After the list of models was extended, the original prompts had issues steering them.

- As a result, I changed the communication protocol to use regex and be tolerant to reply format, doing its best to extract action and arguments from LLM replies.

- Since models don't score any Wins there must be some alternative metric demosntrating game progress.

- For the time being using Draws, the more draws - the better.

- Yet most of the draws scored are due to hitting the 200 max moves limmit and hence the metric demonstrates the adherence to communication protocol/prompt cpnverntions.

- Logs also contain "Material Count" metrics - the weighted scores of piaces a player has, at the beginning a player has a total of 39 units of material.

- Material difference could be a good metric to evluate progress, the player having more material left as the game progress is at a better position.

- Yet most of the models demonstrated negative material difference and one of the models (gpt-35-turbo-0125) failed to make a single move having a material difference at 0 putting it above models that had negative material while staying in the game much longer.

- It might be resonable to create a computed metric that account for both the material and length of the game, addressing the endless pointless game concern, as well as never changing material diff due to failing to early.

- What if the model is not given the list of legal moves? Will the model figuring out legal moves on their own and struggle to progress? Can giving the models a list of legal moves essentially break reasoning turning the game into simple instruction following (i.e. pick one item from the list rather than win in the game)?

- The older GPT-4 Turbo did better than newer GPT-4o version, this is a yet another eval demonstrating how newer models performed worse supporting the claim the the 4o family of models are smaller and cheaper to run models.