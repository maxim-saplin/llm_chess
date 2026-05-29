# COLM Rebuttals

## Todo

- Collect experiments on new models  
- Respond to all rebuttals – focus on o9Fa with the lowest score. The second lowest score, ZDti, shares much with o9Fa, so we can use the answers to the former to better answer the latter.

# Reviewer o9Fa

#### **A broad, well-engineered agentic chess benchmark whose headline reasoning claims are confounded by protocol compliance and underpowered statistics, and whose anti-memorization premise is asserted rather than tested.**

Official Reviewby Reviewer o9Fa21 May 2026, 18:52 (modified: 22 May 2026, 06:58)Program Chairs, Area Chairs, Reviewers Submitted, Authors, Reviewer o9Fa[Revisions](https://openreview.net/revisions?id=Raole82QvL)  
**Summary:**  
This paper introduces LLM CHESS, a framework that probes reasoning and instruction-following by having an LLM play full games of chess in an agentic, multi-turn setting through a small set of tool calls, with no game history provided. Models are scored on a Win/Loss percentage and several per-ply move-quality metrics. Over fifty models play games against a random opponent, and a subset of strong reasoning models additionally plays a chess engine at varied skill levels for an Elo estimate. The framework, a leaderboard, and a game dataset are released.

The submission is clearly written and the engineering is substantial. The agentic reformulation is a genuine contribution over prior static chess-LLM work. My reservations are that the headline reasoning gap is largely explained by tool-call failures rather than chess ability, that the central claims are statistically underpowered, and that the anti-memorization pitch is argued by design rather than demonstrated.

**Reasons To Accept:**  
S1. The agentic reformulation is a real contribution. Casting chess as a multi-turn, tool-using interaction, and separating the ability to operate the protocol from the ability to choose good moves, is a more faithful test of deployed LLM behavior than static evaluations.

S2. The scale and openness are strong. A large model pool is evaluated, and the framework, leaderboard, dataset, and configuration details are released.

S3. The paper is honest about negative results. Even the strongest model scores poorly, the paper does not oversell, and the per-ply move-quality metrics give a useful signal beyond win rate.

**Reasons To Reject:**  
W1. The benchmark conflates chess reasoning with protocol compliance. The paper's own analysis shows that most non-reasoning losses, and a large share of all failures, come from instruction-following errors and unparsable tool calls rather than bad moves, and that non-reasoning models which complete games almost always draw. This suggests the headline reasoning gap is driven mainly by which models can operate the tool-calling format. The authors should report results restricted to games with no instruction-following failure, so reasoning ability is separated from protocol compliance.

W2. The main claims are statistically underpowered, and the Elo results are partly an artifact. Win/Loss is reported as a point estimate over a small number of games with no confidence intervals, so many claimed findings are differences likely within noise. The Elo and test-time-scaling results are also confounded by API timeouts, which the appendix itself counts as losses and identifies as the reason some models rank lower at higher reasoning effort. Confidence intervals should be added, and timeout-induced losses separated from genuine ones.

W3. The anti-memorization and anti-saturation framing is asserted, not tested. The abstract and conclusion lean heavily on this claim, but there is no contamination probe and no comparison against a static chess benchmark. Only the opponent difficulty is dynamic; the prompts and protocol are static and could themselves be fit. Direct evidence is needed.

W4. The task is heavily scaffolded and several design choices are under-justified. Providing legal moves on demand removes the need to track board state or derive legality, so the headline setting measures chess play under a strong scaffold; this should be stated plainly. The conversation-turn and attempt budgets, and the handling of special rules without move history, are also not adequately explained.

W5. The evaluation setup is narrow and dated. The evaluated models are already a generation behind the frontier, which weakens a paper whose headline conclusion is about current state-of-the-art models and whose pitch is saturation resistance; the model pool should be refreshed. The setup is also limited to one engine, one color, and a single hand-picked subset for Elo, with no play against human or other-LLM opponents.

**Questions To Authors:**  
See W1 to W5. Most important: how much of the reasoning gap survives once games with instruction-following failures are excluded; whether confidence intervals and timeout-corrected Elo will be added; and what direct evidence supports the anti-memorization claim.

**Rating:** 4: Ok but not good enough \- rejection  
**Confidence:** 4: The reviewer is confident but not absolutely certain that the evaluation is correct  
**Ethics Flag:** No

---

### Response

Thank you for your valuable insights and feedback. We address your concerns below:

\---

\#\#\# \`W1: Chess Reasoning Conflated with Protocol Compliance\`

We highlight that xxx and yyy non-reasoning models have low to no instruction following failures, but still perform worse than the reasoning models.

To address your claims, we present results on the top xx models on the 

We then have two main contributions, tied to the two phases of our benchmark: 1\) LLM vs. random. We play LLMs vs

\---

\#\#\# \`W2: Claims are Statistically Underpowered\`

Due to the scope of models we evaluate on, when playing against a random player, we only played 30 games. We view this more as a diagnostic than our final results, in which we can identify instruction following failures as well as consistently poor gameplay; we will clarify this in our revised version.

The Elo results presented in the paper have

We present the timeout results as losses, as they indicate an issue from the provider, which we hypothesize as long reasoning that may not converge.

\---

\#\#\# \`W3: Anti-memorization and Anti-saturation are Untested\`

We acknowledge that training will likely improve scores, though we argue that the increases in performance will likely drop as more and more data is used, as the combinatorial space of moves in chess makes it impossible to train on every board state.

We have not yet seen the models perform well enough to indicate a problem with saturation. In fact, the most powerful model we evaluate in our paper still performs relatively poorly, only reaching an estimated Elo of XXX, which is still a beginner or intermediate player. For saturation to occur, LLMs would need to reach the same performance as a dedicated chess engine like Stockfish. 

However, for models that are trained on more chess data, we will also test them on general capabilities to see if sacrifices have been made in pursuit of better chess performance.

\---

\#\#\# \`W4: Heavy Task Scaffolding\`

\---

\#\#\# \`W5: Narrow and Dated Evaluation Scope\`

\---

# Reviewer rsvL

**Summary:**  
This work presents a benchmark for evaluating large language models on chess through an agentic interaction setup. At each step, the model can call pre-defined actions and is evaluated through full-game play rather than static positions alone. The benchmark is used to evaluate more than 50 open- and closed-source models against a random agent, and a smaller subset of stronger reasoning models against the Dragon 1 chess engine to derive Elo estimates. Beyond win/loss, the paper reports behavioral metrics such as move legality, hallucinated actions, game duration, and per-move quality statistics.

**Reasons To Accept:**
The contribution is not only the engineering of an agentic chess environment, but the empirical measurement it enables. LLM CHESS turned out to be a clean behavioral litmus test for reasoning-style models: non-reasoning models remain largely flat even against a random legal-move agent, while reasoning models show a step change in game completion, Win/Loss, and continued improvement with increased reasoning effort. As random-agent play begins to saturate for stronger models, the Dragon/Komodo phase preserves resolution through an engine-grounded Elo ladder.

This Elo ladder also anchors LLM progress to human performance. Instead of reporting only benchmark-specific percentages, we can interpret model strength on a familiar chess scale: current top LLMs now reach roughly strong amateur/Class C performance, while remaining far below elite human players such as Magnus Carlsen. This human anchoring makes the benchmark useful as a longitudinal measure of reasoning progress, not merely as a packaged chess environment.
1. Chess is a strong testbed for reasoning, planning, and dynamic decision making. Compared with static math or coding benchmarks, it offers a more interactive and potentially less saturable setting for evaluating model capabilities. While this is not the first work to consider chess as an LLM evaluation domain, standardizing the task and providing a concrete agent interface is useful for the community, especially for benchmarking frontier models in a more realistic interactive setup.  
2. The evaluation goes beyond final win rate and includes additional behavioral metrics such as move legality, hallucinated actions, and per-move quality. This gives a more informative picture of whether models fail because they cannot play well or because they cannot reliably operate within the interaction protocol.

**Reasons To Reject:**

1. The work is valuable to the community, but overall it feels like an engineering contribution rather than a methodological advance. The related work already discusses several chess-based evaluation efforts, and the incremental novelty here is mainly in packaging the task as an agentic environment and introducing more metrics. The added metrics are mostly fairly direct, and the agentic environment itself also feels like an engineering contribution.  
2. This work places substantial emphasis on evaluating instruction-following , but this part of the design and analysis feels underdeveloped relative to how prominently it appears in the title and positioning. In practice, the operationalization seems to rely mainly on invalid actions, exceeding turn or attempt limits, and the performance against the random agent. This does capture some aspects of instruction following, but it doesn't offer strong insights.

**Rating:** 6: Marginally above acceptance threshold  
**Confidence:** 4: The reviewer is confident but not absolutely certain that the evaluation is correct  
**Ethics Flag:** No

---

### Response

Thank you for your valuable insights and feedback. We address your concerns below:

\---

\#\#\# \`W1: Lack of Contribution\`

Our 

Todo: emphasize COLM’s policy on contributions

\---

\#\#\# \`W2: Instruction-following Focus Underdeveloped\`

\---

# Reviewer C5pt

**Summary:**  
This paper presents LLM CHESS, a novel and highly valuable evaluation framework that probes both reasoning and instruction-following capabilities of large language models via extended agentic interaction in the domain of chess. The authors conduct rigorous experiments on over 50 open-source and closed-source models, revealing critical limitations of LLMs in long-horizon planning, tool usage, and robustness. A key strength of this benchmark is its stochastic and dynamic nature, which effectively mitigates overfitting and benchmark saturation.

**Reasons To Accept:**

1. This benchmark centers on multi-turn agentic interaction rather than static PGN completion or single-turn move prediction. By requiring models to autonomously select actions (query board state, get legal moves, make moves) within a conversation, it simultaneously evaluates both reasoning ability and instruction-following competence. The dynamic difficulty adjustment mechanism ensures the benchmark will remain relevant as models improve.  
2. This paper conduct comprehensive and Large-Scale Experiments. The authors evaluate an unprecedented number of models, covering both reasoning models and instruct models. The multi-dimensional evaluation metrics provide a holistic view of model capabilities, going far beyond simple win-rate metrics used in prior work.  
3. This is a complete work and easy to follow : ) The authors have open-sourced the full experimental framework, codebase, and detailed experimental settings. They also provide a public leaderboard and game dataset, enabling the community to build on this work and evaluate new models easily.

**Reasons To Reject:**

1. All experiments were conducted with LLMs exclusively playing as black. Although the authors added a 35-point white advantage correction in Elo calculation, this correction is derived from human chess game data, and its applicability to LLMs has not been empirically validated.  
2. The authors introduce a well-designed agentic framework with three tool actions, and set a maximum of 10 conversation turns per ply as the default configuration. However, this 10-turn limit is a critical hyperparameter whose rationality has not been empirically validated in the paper.  
3. The authors justify not providing move history by aligning with chess engines, but this differs significantly from human cognitive processes and may underestimate models' long-term planning capabilities.

**Rating:** 6: Marginally above acceptance threshold  
**Confidence:** 3: The reviewer is fairly confident that the evaluation is correct  
**Ethics Flag:** No

---

### Response

Thank you for your valuable insights and feedback. We address your concerns below:

\---

\#\#\# \`W1: LLMs Only Play As Black\`

Todo: point to appendix

\---

\#\#\# \`W2: Conversation Turn Limit Not Validated\`

Todo: point to case study 

\---

\#\#\# \`W3: Lack of Move History\`

Todo: point to explanation in appendix and previous rebuttals about how the LLMs still need to think ahead, even if given no history, and also to ablation.

\---

# Reviewer ZDti

**Summary:**  
This paper introduces using chess playing to benchmark language models with Elo scores. The authro suggests this evaluate models' reasoning and instruction-following abilities. The author considers the the stochastic and dynamic nature reduces overfitting and memorization while preventing benchmark saturation. The author also open source the code and data to facilitate public access of the benchmark.

**Reasons To Accept:**

1. The proposed framework target an important issues of overfitting and saturation of llm benchmark, and propose using chess with dynamic and stochastic nature as a solution, which is novel.  
2. The writing and the figure are clear and beautiful. The paper is easy to follow.  
3. The paper contains fruitful metrics and results, showing the comphrehensive landscape of current llms on the benchmark.

**Reasons To Reject:**

1. Some of the claims can be arguable. For example, chess is a too formalized settings to reflect diverse and vague expression in real-world instruction following, which could be the challenging part of instruction following. Also, chess is a narrow domain, and it is unclear how performance in chess correlate to real world tasks.  
2. Results do not contain many latest models.  
3. It is unclear what could contribute to higher performance on the benchmark. And the author does not show how specific training, for example sft on winning trajectories, could affect the model performance to show it is indeed a benchmark that is hard to overfit.

**Rating:** 5: Marginally below acceptance threshold  
**Confidence:** 4: The reviewer is confident but not absolutely certain that the evaluation is correct  
**Ethics Flag:** No

---

### Response

Thank you for your valuable insights and feedback. We address your concerns below:

\---

\#\#\# \`W1: Chess is too Narrow to Generalize\`

Historically, chess has been seen as a game with challenges reflecting those faced by AI, namely, long-horizon planning and a combinatorial move space. For this reason, we see chess as a valuable marker in AI progress. However, we agree chess is a specific domain, and for that reason has aspects that will not generalize.

The insights we gain from LLM Chess are more generalizable: in our simple agentic setup, we identify problems with instruction following in weaker models, as well as the strong performance of reasoning models, especially with increased scaling. The latter is very connected.

\---

\#\#\# \`W2: Dated Evaluation Scope\`

Todo: copy dated evaluation scope answer from Reviewer o9Fa

\---

\#\#\# \`W3: Unclear How to Achieve Higher Performance and Anti-saturation is Untested\`

Based on the results in LLM Chess, we see that higher performance is generally achievable by stronger reasoning models, which matches our intuition regarding the difficulty of making a move in chess.

Todo: copy anti-saturation answer from Reviewer o9Fa

\---

# Socials Posts

## Twitter/X

\*\*1/6:\*\* Excited to share our latest work, now on arXiv and at FoRLM @ NeurIPS'25\! 🎉

Introducing \*\*LLM Chess\*\*: a benchmark for evaluating reasoning and instruction-following in LLMs through chess.

LLMs now reach experts in math & coding, but can they \*reason\* in dynamic, multi-step strategic environments? We tested 50+ models. The results? Many models struggle to beat an opponent making \*random\* moves, and even powerful reasoning models cannot beat a \*weak skilled opponent\*.

\*\*\[Image: First page of the paper PDF\]\*\*

\---

\*\*2/6:\*\* Why chess? It's been the "drosophila of AI" since the 1950s, used as a measuring stick for AI progress and a testbed for planning, strategy, and long-horizon decision-making.

Unlike static benchmarks that get contaminated or saturated, chess offers:  
✅ Dynamic, stochastic gameplay  
✅ Adjustable difficulty via engine skill  
✅ Resistance to memorization

\*\*\[Image: Figure 1 — the LLM Chess framework overview diagram\]\*\*

\---

\*\*3/6:\*\* Our setup: LLMs play in an agentic environment, making moves through tool calls.

\*\*Phase 1:\*\* 50+ models play 30 games each vs a random agent, a simple test that many models \*fail\* due to instruction-following failures or poor performance.

\*\*Phase 2:\*\* Top reasoning models face the Komodo Dragon engine at various Elo scores from 250 to 1375 for performance estimation grounded in the real world (tied to [chess.com](http://chess.com) Elo). 

\---

\*\*4/6:\*\* Key findings for Phase 1:

♟️ Reasoning models crush non-reasoning: \*\*45.4% vs 0.7%\*\* win rate, with many models struggling to reach even 50% Win/Loss vs a random player  
♟️ Instruction failures \*\*3× higher\*\* in non-reasoning models (71.9% vs 24.4%)  
♟️ Test-time scaling for reasoning effort boosts performance up to \*\*+20%\*\*

\*\*\[Image: Figure 2 — Win/Loss bar chart of LLMs vs random opponents\]\*\*

\---

\*\*5/6:\*\* Key findings for Phase 2:

📉 The best LLM we tested (o3-low) peaks at only \*\*\~758 Elo\*\*.

While LLMs match experts in math & coding, they play chess around the average online player (\~611 Elo on [chess.com](http://chess.com)) and far below human masters (\~2800 Elo).

\*\*\[Image: Figure 3 — Elo ratings of top reasoning models\]\*\*

\---

\*\*6/6:\*\* 

🔄LLM Chess is extensible. As models improve, we scale difficulty. No saturation, no contamination.

Check it out and let us know what you think\! We are continually evaluating more models on the benchmark.

Come and see us at the FoRLM workshop at 3:00-4:15pm on Sunday December 7th, 2025 @ Upper Level Room 33ABC at NeurIPS\!

📄 Paper: [https://arxiv.org/abs/2512.01992](https://arxiv.org/abs/2512.01992)  
🏆 Leaderboard: https://maxim-saplin.github.io/llm\_chess/  
💻 Code: https://github.com/maxim-saplin/llm\_chess

Huge thanks to @msmxm, @SaiKolasani1, @nrcrispino, @kylepmongt, @matei\_zaharia, @jaredq, @Chi\_Wang\_, @ChenguangWang 🙏

## LinkedIn

🎉 Excited to share our latest work, now on arXiv and at FoRLM @ NeurIPS'25\!

Introducing LLM Chess — a benchmark for evaluating reasoning and instruction-following in large language models through the game of chess.

LLMs now reach expert level in math and coding, but can they reason in dynamic, multi-step strategic environments? We tested 50+ models. The results? Many models struggle to beat an opponent making random moves, and even powerful reasoning models cannot beat a weak skilled opponent.

Why chess? It's been the "drosophila of AI" since the 1950s, used as a measuring stick for AI progress and a testbed for planning, strategy, and long-horizon decision-making. Unlike static benchmarks that get contaminated or saturated, chess offers dynamic gameplay, adjustable difficulty, and natural resistance to memorization.

Our setup: LLMs play in an agentic environment, making moves through tool calls.

→ Phase 1: 50+ models play 30 games each vs a random agent — a simple test that many models fail due to instruction-following failures or poor performance

→ Phase 2: Top reasoning models face Komodo Dragon engine at various Elo scores from 250-1375 for real-world performance estimation tied to chess.com ratings

Phase 1 findings:

♟️ Reasoning models crush non-reasoning: 45.4% vs 0.7% win rate, with many models struggling to reach even 50% Win/Loss vs a random player

♟️ Instruction-following failures 3× higher in non-reasoning models (71.9% vs 24.4%)

♟️ Test-time scaling boosts performance up to \+20%

Phase 2 findings:

♟️ The best LLM we tested (o3-low) peaks at only \~758 Elo — around the average online player (\~611) and far below human masters (\~2800)

The takeaway? While LLMs match domain experts in math and coding, they remain at beginner level in strategic reasoning. LLM Chess is extensible: as models improve, we scale difficulty. No saturation, no contamination.

Check it out and let us know what you think\! We are continually evaluating more models on the benchmark.

🏆 Leaderboard: https://maxim-saplin.github.io/llm\_chess/ 

💻 Code: https://github.com/maxim-saplin/llm\_chess 

📄 Paper: https://arxiv.org/abs/2512.01992

Huge thanks to our amazing collaborators: Maxim Saplin ([https://www.linkedin.com/in/maxim-saplin/](https://www.linkedin.com/in/maxim-saplin/)), Sai Kolasani, Nicholas Crispino, Kyle Montgomery, Jared Quincy Davis, Matei Zaharia, Chi Wang, and Chenguang Wang\! 🙏

\#NeurIPS2025 \#LLM \#AI \#MachineLearning \#Chess \#Reasoning \#Benchmark

\*\*\[Images: Paper first page, Figure 2 (Win/Loss chart), Figure 3 (Elo ratings)\]\*\*  
![][image1]![][image2]![][image3]

# ICLR Rebuttals

## Summary

\#\#\# TL;DR of Our Work  
We introduce LLM CHESS, a benchmark designed to evaluate reasoning and instruction-following capabilities of LLMs through chess. We evaluated over 50 models using a simple agentic framework where LLMs play full games. Our evaluation is split into two phases: first using the full set of models against a random agent to assess baseline instruction-following, then using a more targeted set of powerful reasoning models against a chess engine to estimate Elo ratings. Key findings reveal that most models struggle to defeat even a player making random moves due to instruction-following failures, and even the top-performing model we tested achieved only 758 Elo, only slightly higher than an average human player.

In response to the feedback from the reviewers, we have made corresponding improvements in the paper, with the revisions highlighted in yellow. 

\#\#\# Reviewers' Recognition

Reviewers find LLM CHESS well-constructed and valuable.

\- \`cZAL\`: "The choice of chess as the testbed is conceptually solid. It naturally embodies combinatorial search, long-horizon planning, and rule-based reasoning"  
\- \`RA9T\`: "The agentic framework is a key innovation. It not only evaluates the quality of moves but also tests the model's integrated ability to follow instructions and use tools."  
\- \`y5WN\`: "The paper is clear and easy to follow”; “Overall feels like a solid work"

Reviewers appreciate the scale and reproducibility of the evaluation.

\- \`RA9T\`: "The breadth of the study, covering over 50 models, is commendable. This large scale provides a robust foundation for drawing conclusions"  
\- \`cZAL\`: "The framework is reproducible and extensible, with open code, public leaderboards, and adjustable opponent strengths"

Reviewers find the ablation studies insightful.

\- \`RA9T\`: "The well-designed ablation studies offer deep insights into why models fail, demonstrating that model performance is highly sensitive to prompting and interaction formats."

\#\#\# Reviewers' Concerns and Our Rebuttals

\*\*\`RA9T\` requests clearer definition of "reasoning-enhanced" models — addressed.\*\*

\- "The argument would be strengthened if the paper provided a more explicit and operational definition for this classification."

We define "reasoning-enhanced" models as those specifically advertised by developers as "reasoning" (e.g., OpenAI) or "thinking" (e.g., Anthropic, Google). These models split responses into reasoning/thinking intermediary sections and final answers. Examples include all "o" family models, Claude 3.7 Thinking, Grok 3 Mini, Gemini 2.5 Pro, and Deepseek-R1. We include this detailed description in Appendix B in the new version.

\*\*\`RA9T\` and \`cZAL\` raise concerns about entanglement of instruction-following and reasoning — addressed.\*\*

\- \`RA9T\`: "The default agentic setup concurrently tests strategic thinking, tool use, and format adherence... a model might be a strong strategist but a poor tool-user."  
\- \`cZAL\`: "The agentic interface itself adds heavy cognitive and formatting burdens. Since removing it in ablations leads to more than 20 % performance gains, failures may be caused by API-understanding errors rather than reasoning problems."

Our two-phase design helps isolate these abilities. Phase 1 (vs player making random moves) serves as a sanity check for instruction-following; Phase 2 focuses on models that completed Phase 1 with minimal to no instruction-following errors to better isolate reasoning. For example, o3, o4-mini, and Grok 3 Mini all have 0% instruction-following failures. The goal of this is to penalize models with good reasoning but poor instruction-following, which in practice will be difficult to use in real agentic workflows. We clarify the purpose of each phase in Section 2.1 in the updated paper.

\*\*\`RA9T\` requests more granular error analysis — addressed.\*\*

\- "It would be very informative to see a more fine-grained classification of these errors."

We categorized failures across 76 models (54 with abnormal finishes): Too many wrong actions (64.79%), Max turns reached (13.96%), and Model errors (21.25%). Per 1000 moves: wrong actions (122.70, 62.1%) vs wrong moves (74.86, 37.9%). Wrong actions stem from non-parsable responses; wrong moves are hallucinations where models request illegal moves despite having legal moves listed in context. This analysis is described in Appendix C.6 in the updated paper.

\*\*\`cZAL\` questions benchmark validity without cross-task correlation — addressed.\*\*

\- "The paper implicitly equates chess reasoning with general reasoning ability, yet with no cross-task validation"

We calculated correlation between our Elo scores and LiveCodeBench performance, finding a Pearson correlation of 0.686 (p=0.0888), indicating moderately strong positive correlation. We emphasize that good chess performance doesn't equate to general reasoning, but a claimed "general reasoner" should perform sufficiently well at chess. We have updated the paper with this analysis in Section 3.2 and Appendix C.5.

\*\*\`y5WN\` questions what lessons can be drawn from the benchmark — addressed.\*\*

\- "It is unclear what information/inferences use of the resource will offer."

Our benchmark shows: 1\) instruction-following varies greatly even in simple agentic settings, 2\) reasoning models perform better with scaling reasoning effort in chess, and 3\) unlike math/coding benchmarks, top models show low chess performance. For example, o4-mini (high) scores 92.7 on AIME 2025 but only 407.61 Elo, below the average chess.com player (618 Elo). This highlights limitations in LLMs' general reasoning capabilities. The goal of LLM CHESS is a living benchmark that allows people to understand how well LLMs perform at chess in an easily extensible way, with conclusions about reasoning and instruction-following that could potentially have impacts on other agentic or reasoning tasks. We have added comparisons with human Elo scores in Appendix B.5 and correlation with a strong reasoning benchmark (LiveCodeBench) in Appendix C.5 to address where LLM CHESS fits in the real world.

\*\*\`cZAL\` requests runtime and API costs — addressed.\*\*

\- "Runtime and API costs are not reported, which is necessary to assess practicality and reproducibility."

Our leaderboard reports average game costs (e.g., $8.16 per game for o3-low). Game logs contain token accounting used for cost calculations. We include cost summaries in Appendix B.3 in the updated version.

\*\*\`cZAL\` raises concerns about fine-tuning inflation — addressed.\*\*

\- "Will targeted fine-tuning on its trajectories quickly inflate leaderboard scores"

Unlike knowledge-based benchmarks, chess is immune to memorization given its dynamic, combinatorial nature. Training on every board state is infeasible. After initial fine-tuning gains, increased general reasoning ability would be necessary to improve further.

—

Summary of Criticisms:

- Conflation of reasoning and instruction-following. Ablations are an attempt to isolate but are not truly isolated.  
  - Response: I suppose our focus is mostly on testing reasoning given a strong enough instruction-following ability. We find that there are a lot of current models with poor instruction-following abilities that may even be purported as stronger reasoners. To use these models in the real-world, we do want some base form of strong enough instruction following abilities, else their reasoning isn’t useful. This is what our evaluation portrays.

Feedback:  
improve the writing style of the responses. make it more sharp and explicit and cite paper lines if certain things were missed or misunderstandings from the review. e.g., for RA9T,  "The argument between "reasoning-enhanced" and "standard" models would be strengthened if the paper provided a more explicit and operational definition for this classification. \- fair criticism, in fact in our paper (lines x-y) we have definite it as xxx, and we have added the following definition to the new version.xxx”  
add corresponding additional experiments or studies (e.g., error analysis) when asked e.g., RA9T’s error analysis and cZAL’s cross-test validation.  
highlight novelty and key contribution of the work and make them explicit in the paper (e.g., its difference with existing reasoning/instruction following benchmark, its new/different findings, its scale of experiments (e.g., number of models tested))  
add "thank you for recognition of our key contributions and xxx. we are committed to high quality research and have addressed them in the new version.“

# Reviewer RA9T

#### **Official Review of Submission22381 by Reviewer RA9T**

Official Reviewby Reviewer RA9T04 Nov 2025, 18:45 (modified: 12 Nov 2025, 02:09)Everyone[Revisions](https://openreview.net/revisions?id=cunnsQAbue)  
**Summary:**  
This study proposes LLM CHESS, a novel and comprehensive benchmark framework designed to evaluate the reasoning and instruction-following capabilities of Large Language Models (LLMs) within the complex, strategic domain of chess. Its core methodology utilizes an agentic interaction setup where LLMs play full games via tool calls: get\_current\_board, get\_legal\_moves, and make\_move. The study presents a large-scale evaluation of over 50 models. It first assesses their baseline capabilities and instruction adherence by playing against a random agent. Subsequently, high-performing models are pitted against a chess engine (Komodo's Dragon 1\) with configurable skill levels to estimate their Elo ratings. Key findings reveal a significant performance gap between so-called "reasoning-enhanced" LLMs and standard ones. Most models struggle to reliably defeat even a random player due to instruction-following failures. Even the top-performing model achieves an Elo of only \~758, highlighting a stark discrepancy between LLM capabilities in dynamic, strategic environments and their performance on other reasoning tasks like math and programming. To foster future research, the authors have open-sourced the experimental framework, a public leaderboard, and the dataset of games.

**Soundness:** 3: good  
**Presentation:** 3: good  
**Contribution:** 3: good  
**Strengths:**

1. The agentic framework is a key innovation. It not only evaluates the quality of moves but also tests the model's integrated ability to follow instructions and use tools. The design is highly scalable—difficulty can be increased by simply raising the opponent's skill level—ensuring the benchmark's long-term relevance.  
2. The breadth of the study, covering over 50 models, is commendable. This large scale provides a robust foundation for drawing conclusions about the current state of LLMs on this task, making the findings more convincing.  
3. The well-designed ablation studies offer deep insights into why models fail, demonstrating that model performance is highly sensitive to prompting and interaction formats. This points to a lack of robust generalization capabilities.

**Weaknesses:**

1. ~~A core part of the analysis distinguishes between "reasoning-enhanced" and "standard" models. The argument would be strengthened if the paper provided a more explicit and operational definition for this classification (e.g., based on specific test-time algorithms, architectural features, or training methods).~~  
2. The analysis could be enriched by more granular case studies of errors. For instance, analyzing the types of mistakes (distinguishing between simple tactical blunders and deeper strategic misunderstandings) or identifying common patterns in instruction-following failures could offer a more nuanced understanding of the models' cognitive limitations.  
3. ~~The default agentic setup concurrently tests strategic thinking, tool use, and format adherence. While the ablation studies help to deconstruct this, it raises the question of whether the benchmark could be designed to isolate these skills more directly. For instance, a model might be a strong strategist but a poor tool-user, and the current primary metrics may not clearly differentiate between these two cases.~~

**Questions:**

1. ~~Could you provide a more formal or operational definition for "reasoning-enhanced" models as used in this study? Is this distinction based on specific test-time algorithms (e.g., search, self-consistency), architectural features, or particular training methodologies? **Addressed in W1**~~

	**Maxim:** under reasoning enhanced models we mean the models that are specifically advertised/characterized by their developers as “reasoning” (e.g. OpenAI) or “thinking” (e.g. Anthropic, Google) without going into detail as to how those models are built (generally RL and test-time compute are mentioned, yet the detail and disclosure varies between the AI shops). On the surface the reasoning enhanced models manifest their nature by splitting the response into 2 sections:

- Reasoning/Thinking intermediary \- delimited via special markdown (such as \<think\> tag) or residing in a separate API response section (e.g. [thinking](https://docs.claude.com/en/api/messages#body-thinking) block in Anthropic API)  
- Final answer

In our data we find that only models characterized as reasoning/thinking by their developers generate way more tokens per move as seen in LLM Chess Logs (confirming the test-time compute mode of operation of such models) AND show a step change in performance when playing against a random player.

2. The high rate of instruction-following failures is a key finding. It would be very informative to see a more fine-grained classification of these errors. For example, do models get stuck in loops (e.g., repeatedly calling get\_current\_board), fail to parse the available actions, or generate syntactically invalid moves in the make\_move tool call? This could help differentiate between failures in attention, comprehension, or action generation. **Addressed in W2**  
3. The Mixture-of-Agents (MoA) experiments yield interesting but limited gains, and performance appears highly sensitive to the choice of proposer and aggregator models. Could you please elaborate on the model's sensitivity to this configuration? For instance, what might the results be if a stronger model were used as the aggregator? Furthermore, what specific prompt or mechanism was used by the aggregator to synthesize the proposals?  
4. ~~Regarding line 404, does the phrase "by removing actions and instead supplying the removed information automatically" mean that the current board state and legal moves are provided to the LLM automatically, bypassing the need for it to call the corresponding tools?~~  
5. ~~On pages 20 and 21, some of the prompt text extends beyond the page margins. We suggest adjusting the formatting to improve readability.~~

**Flag For Ethics Review:** No ethics review needed.

---

### Response

Thank you for your valuable insights and feedback. We address your concerns below:

\---

\#\#\# \`W1 & Q1: Lack of distinction between “reasoning-enhanced” and “standard models\`

We define “reasoning-enhanced” models as those that are specifically advertised/characterized by their developers as “reasoning” (e.g. OpenAI) or “thinking” (e.g. Anthropic, Google) without going into detail as to how those models are built (generally RL and test-time compute are mentioned, yet the detail and disclosure varies). On the surface the reasoning enhanced models manifest their nature by splitting the response into two sections: 1\) reasoning/thinking intermediary, delimited via special markdown (such as \<think\> tag) or residing in a separate API response section (e.g. thinking block in Anthropic API), and 2\) the final answer.

E.g., aligned with their advertised functionalities, we designate as reasoning the following: all “o” family of models (e.g., o1, o3, o4-mini), Claude 3.7 Thinking, Grok 3 Mini, Gemini 2.5 Pro, and Deepseek-R1.

We will include this more detailed description in an updated version to be released soon.

\---

\#\#\# \`W2 & Q2: Should include more granular case studies of errors\`

During games, we find various instruction-following issues such as models responding with non-parsable text, where an action can’t be identified by simple string matching (i.e., wrong actions), or requesting illegal moves by issuing a parsable **make\_move** action (i.e., wrong moves). Evaluation of conversation traces shows that wrong moves are typically attributed to models’ inability to respond with relevant actions, filling the response with verbosity and failing to recognize the desired response format. Wrong moves can be attributed to hallucinations; e.g., even with prior get\_legal\_moves requests and a list of available legal moves in the context, the model can still fail to request a legal move, choosing one not allowed/not listed in the previous message instead.

All games interrupted due to issues can be categorized as the following:  
\- Too many wrong actions: the model produced more than 2 responses that the game bot failed to parse OR make a valid move  
\- Max turns reached: while deciding on a next move, the chat completions dialog lasted for more than 10 turns. This typically indicates repetitive loops, such as going in circles with actions like get\_current\_board/get\_legal\_moves  
\- Model Errors: e.g. timeouts when a model failed to respond within a reasonable amount of time or when a specific API code was returned that means model error. Connectivity and infrastructure issues are discarded (log deleted) and the corresponding games are rerun.

Please see below stats on a subset of 76 evaluated models:

\- \*\*Models with abnormal finishes:\*\* 54 out of 76  
\- \*\*Percentage:\*\* 71.1%

\#\#\#\# Breakdown of Termination Reasons  
\*(Relative to failed games)\*

Average breakdown of failure reasons (sums to \~100%):  
\- \*\*Too many wrong actions:\*\* 64.79%  
\- \*\*Max turns reached:\*\* 13.96%  
\- \*\*Unknown issue:\*\* 0.00%  
\- \*\*Error:\*\* 21.25%

\#\#\#\# Breakdown of Wrong Actions vs Wrong Moves

Average mistakes per 1000 moves:  
\- \*\*Wrong actions:\*\* 122.70 (62.1%)  
\- \*\*Wrong moves:\*\* 74.86 (37.9%)  
\- \*\*Total:\*\* 197.56

We will place this analysis in an updated version and release our code used to do this analysis upon acceptance.

\#\#\# \`W3: Entanglement of instruction-following and reasoning abilities in the benchmark\`

The goal of our benchmark is to evaluate both instruction-following and reasoning abilities in chess. We acknowledge that these two concepts may be entangled. However, we believe the design of the benchmark is still valuable towards drawing conclusions regarding these abilities. Importantly, by designing a simple agentic setting requiring consistent tool calling and valid moves (described in Section 2.1), we focus on a realistic setting where both instruction-following and reasoning are necessary. Our core belief driving these choices is that a model with very good reasoning ability but poor instruction-following will seldom be used.

We believe that our two phases, of LLMs vs random player (Section 3.1) then LLMs vs chess engine (Section 3.2), helps us to isolate instruction-following and reasoning, respectively. We consider the first phase less of a full reasoning evaluation and more of a sanity check to ensure that models are strong enough at instruction-following to behave reliably in our agentic setting. We argue that beating a random player is something we should expect most current LLMs to do on a regular basis given their stated reasoning abilities. The fact that many LLMs we evaluate can’t even reach a 50% Win/Loss signifies that there are pressing problems with how the LLMs behave (Figure 2). This shows that these LLMs have not even reached the bare minimum of what we would expect in a simple agentic setting in chess. While we might not be able to evaluate pure reasoning ability in the models that perform poorly in phase 1, we can still make conclusions about reaching the sufficient level of instruction-following and reasoning that we require.

Then, for the second phase, we generally focus on models that were only able to complete the first phase without instruction-following errors, so can better isolate reasoning performance. For example, in Table 8 we see that o3, o4-mini, and Grok 3 Mini all have 0% instruction-following failures over all games vs random players. We note that o3-mini (low) and o3-mini (medium) still have instruction-following errors, so perhaps these models are thus underestimated in their performance. However, these models generally follow the expected rankings when we scale their reasoning effort, meaning reasoning is having a similar effect as it does in o4-mini. We note the other models are strong enough to pass the base level of instruction-following that we require. Thus we can say that reasoning makes up most performance differentials, not instruction-following.

\---

\#\#\# \`Q3: Lacks details on MoA experiments\`

We provide additional details on our MoA experiments below, which we will place in an updated version of the paper in the near future:

The aggregator works by independently querying a list of proposer/worker models and concatenating their outputs into a single message. This context is fed to the synthesizer model, which operates under a specific system prompt:

\`\`\`  
**You will be provided with a set of responses from various open-source models to the latest user query.**  
**Your task is to synthesize these responses into a single, high-quality response in British English spelling.**  
**It is crucial to critically evaluate the information provided in these responses, recognizing that some of it may be biased or incorrect.**  
**Your response should not simply replicate the given answers but should offer a refined, accurate, and comprehensive reply to the instruction.**  
**Ensure your response is well-structured, coherent and adheres to the highest standards of accuracy and reliability.**  
**\`\`\`**

While in the paper we presented MoA results for only o4-mini, we also ran additional experiments with different ensembles of reasoning and non-reasoning models. We found that none of the tested non-reasoning models (Claude Haiku 3.5, gpt-4.1-mini) improved on game proficiency (0 win rate vs random player) while also improving on instruction following (100% game duration, meaning all of the games completed naturally, i.e. they were not interrupted due to e.g. hallucinated moves). We found it surprising that using o4-mini as the synthesizer failed to improve win rates. Additionally, using reasoning models with instruction-following issues (Deepseek R1, Gemini 2.5 Pro) as one of the proposers and weak synthesizer (gpt-4.1-mini) did significantly boost win rates due to recovered instruction following, achieving 100% game duration. Results with the Win/Loss vs a random player and the game duration are below and will be placed in a new version of the paper:

| Model | Win/Loss | Game Duration |  
|-------|---------------|---------------|  
| Deepseek R1 | 32.3% | 62.4% |  
| Deepseek R1 MoA | 62.9% | 100% |  
| Gemini 2.5 Pro | 41.9% | 73.6% |  
| Gemini 2.5 Pro MoA | 78.9% | 100% |

\*\*Deepseek R1 MoA Configuration:\*\*  
Worker models: Deepseek-R1, GPT-4o Mini (temp 0.3), GPT-4o Mini (temp 1.0). Synthesizer: GPT-4o (temp 0.3).

\*\*Gemini 2.5 Pro MoA Configuration:\*\*  
Worker models: Gemini 2.5 Pro (preview version, 03-25), GPT-4o Mini (temp 0.3), GPT-4o Mini (temp 0.0). Synthesizer: GPT-4o (temp 0.3).

\---

\#\#\# \`Q4 & Q5: Additional clarifications\`

Yes, in line 404 we mean that board state and legal moves were provided to the LLM automatically when removed as tools so that the model retains the same amount of information when making its moves. This corresponds to the “Only make\_move” setting in Table 6\.

Thank you for pointing out the page margin issues on pages 20 and 21, we have fixed this in an updated version we will release soon.

\---

# Reviewer y5WN

#### **Official Review of Submission22381 by Reviewer y5WN**

Official Reviewby Reviewer y5WN29 Oct 2025, 23:24 (modified: 12 Nov 2025, 02:09)Everyone[Revisions](https://openreview.net/revisions?id=sdE50ZczJn)  
**Summary:**  
This paper benchmarks language models as chess-playing agents, finding that reasoning models perform at near the median player on chess.com (looking briefly online at the distribution of elo scores.) Most of the models without reasoning (long think chains) fail to beat an agent playing random moves.

I think there are fair concerns about why/whether we would use an LLM for a task like this, but it seems like this paper offers a resource that should exist and I think that people will enjoy seeing.

**Soundness:** 3: good  
**Presentation:** 3: good  
**Contribution:** 2: fair  
**Strengths:**

* The paper is clear and easy to follow  
* Overall feels like a solid work  
* I like how you setup Figure 4a (and b)

**Weaknesses:**

* The primary contribution is the resource here. However, it is unclear what information/inferences use of the resource will offer. What will future users of the benchmark learn from the results? (See questions)

**Questions:**

* Q: What lessons would you draw from this work? What lessons would you draw from future results on this benchmark?  
* Chess was/is a good test bed for reasoning, but now we have models that are pretty good at reasoning, and we have chess models that are good at chess. It is not clear why or where this benchmark fits in. There is an analogy to arithmetic but I'm not sure it fully answers the question.  
* Q: Have you seen this https://www.kaggle.com/game-arena? Any comments or comparisons?  
* I would recommend using something other than "Random Player". It sounds like you're randomly picking human players off of chess.com or something. Perhaps "Random Agent"

---

### Response

Thank you for your valuable insights and feedback. We address your concerns below:

\---

\#\#\# \`W1 and Q1: Lacks detail on what we can learn from the benchmark\`

The main goal of the benchmark is to evaluate LLMs on reasoning and instruction-following using chess as a testbed. We believe this is important for testing if reasoning abilities in LLMs, largely tested on math and code, can generalize to the domain of chess, which has an important history in testing AI. After testing a variety of models, we find that 1\) instruction-following performance varies greatly among models in our agentic setting, signifying that even in a simple agentic setting, reasoning performance may be constrained by the ability to follow instructions, 2\) reasoning models perform better, making much less instruction-following errors and seeing increased performance with scaling reasoning effort, and 3\) unlike on current math and coding benchmarks, top models show relatively low performance on LLM Chess.

As an example, o4-mini (high) achieves a score of 92.7 on AIME 2025, an elite high school math competition benchmark \[1\] but achieves only a 407.61 Elo on LLM Chess. While o4-mini is able to perform better than most of the top high school math competitors, on LLM Chess it reaches that of only a beginner player, below the average [chess.com](http://chess.com) player who has an Elo of 618\. For context, Magnus Carlsen is the highest ranked player with an Elo of 2839, and the highest player under 20 has Elo of 2768 as of November 19 \[2\]. This illustrates a stark contrast: o4-mini (high) is able to achieve world-class performance in math but only reaches that of a beginner in chess. Therefore, our work highlights a limitation of current LLMs to embody general reasoning capabilities, with top performance limited to certain domains. As models get better, we will continue to monitor performance, seeing if smaller models stop having basic instruction-following errors and if the most powerful models can reach world-class performance in chess like they have in other domains. Additionally, given this current low performance and the dynamic nature of chess, we believe that it will be harder to saturate LLM Chess, so it can have more longevity.

\---

\#\#\# \`Q2: Unclear where benchmark fits among reasoning and chess models\`

We draw from the history of using chess as a benchmark to evaluate AI models. The main idea is not that we believe all reasoning models should be trained to be good at chess. However, for a model to be a general reasoner, we believe it should have sufficiently strong performance across many domains, one of which is chess. Currently, from the information we have, it doesn’t seem that LLM reasoning models are being trained on games like chess, with much of a focus on coding and math. We believe at this point in time, this fact allows us to measure one aspect of the generalizability of reasoning abilities (though noting that good performance at chess does not imply good general reasoning performance). We believe that chess can be used as another signal, perhaps more grounded in the real-world and understandable to the general public, to help keep track of the progress LLMs are making.

\---

\#\#\# \`Q3: Comparison to existing game-arena benchmark\`

The attached game-arena benchmark aligns with our view that chess can be useful as a measure of general model ability. The primary difference between their benchmark and ours is that they use direct LLM-to-LLM comparison, where we focus on LLMs playing against the same non-LLM (either an agent taking random moves or a chess engine). This gives us a more fixed comparison. Additionally, we model our LLMs as agents that can utilize tools, which allows us to evaluate more instruction-following capabilities. We will be sure to include this in the related work in an updated version.

\---

Thank you for the suggestion about the “Random Player” label; we will adjust that to be less ambiguous in the final version.

\---

\#\#\# References

\[1\] OpenAI. "Introducing OpenAI o3 and o4-mini." *OpenAI*, 16 Apr. 2025  
\[2\] Live Chess Ratings & Chess Rankings (November 2025)." *Chess.com*

# Reviewer cZAL

#### **Official Review of Submission22381 by Reviewer cZAL**

Official Reviewby Reviewer cZAL29 Oct 2025, 00:27 (modified: 12 Nov 2025, 02:09)Everyone[Revisions](https://openreview.net/revisions?id=7m2jtRIqrR)  
**Summary:**  
LLM CHESS introduces an agentic, chess-based benchmark to jointly evaluate reasoning and instruction-following in 50+ LLMs using full-game play, per-ply quality metrics, and engine-grounded Elo, with code and a public leaderboard released for reproducibility. Empirically, most models struggle even versus a random opponent while reasoning-enhanced models fare better.

**Soundness:** 3: good  
**Presentation:** 2: fair  
**Contribution:** 2: fair  
**Strengths:**

1. The choice of chess as the testbed is conceptually solid. It naturally embodies combinatorial search, long-horizon planning, and rule-based reasoning, making it a meaningful domain.  
2. The analyses and experiments are extensive. The consistent advantage of reasoning-enhanced “thinking” models over standard LLMs provides credible support for the benchmark’s claims.  
3. The framework is reproducible and extensible, with open code, public leaderboards, and adjustable opponent strengths, allowing the benchmark to evolve as models improve.

**Weaknesses:**

1. Most LLMs obtain nearly zero Win/Loss in Table 4, suggesting that the current difficulty curve may be poorly calibrated. It remains unclear whether the benchmark measures reasoning limitations or simply overwhelms models with excessive interaction complexity.  
2. Figure 1 conveys little information, with too much large white space and minimal data illustration. Core analyses such as the ablation in experiments should be added into the main passage instead of in the appendix.  
3. The agentic interface itself adds heavy cognitive and formatting burdens. Since removing it in ablations leads to more than 20 % performance gains, failures may be caused by API-understanding errors rather than reasoning problems.  
4. The paper implicitly equates chess reasoning with general reasoning ability, yet with no cross-task validation (e.g., MATH or BBH scores). The validity of reasoning in this benchmark remains unverified.  
5. Writing quality and narrative flow are weak.

**Questions:**

1. The evaluation focuses exclusively on LLMs; including non-LLM or rule-based baselines would anchor what the result actually represents and clarify how the benchmark scales across architectures.  
2. Can this framework extended to other board games?  
3. Runtime and API costs are not reported, which is necessary to assess practicality and reproducibility.  
4. Because the benchmark uses open interaction protocols, will targeted fine-tuning on its trajectories quickly inflate leaderboard scores, without improving underlying reasoning?

**Flag For Ethics Review:** No ethics review needed.  
**Details Of Ethics Concerns:**  
No ethics review needed

**Rating:** 4: marginally below the acceptance threshold. But would not mind if paper is accepted  
**Confidence:** 3: You are fairly confident in your assessment. It is possible that you did not understand some parts of the submission or that you are unfamiliar with some pieces of related work. Math/other details were not carefully checked.  
**Code Of Conduct:** Yes

---

### Response

Thank you for your thoughtful feedback. We've outlined responses to your concerns below:

\---

\#\#\# \`W1 & W3: Entanglement of reasoning ability with interaction complexity\`

The goal of our benchmark is to evaluate both instruction-following and reasoning abilities in chess. We acknowledge that these two concepts may be entangled. However, we believe the design of the benchmark is still valuable towards drawing conclusions regarding these abilities. Importantly, by designing a simple agentic setting requiring consistent tool calling and valid moves (described in Section 2.1), we focus on a realistic setting where both instruction-following and reasoning are necessary. Our core belief driving these choices is that a model with very good reasoning ability but poor instruction-following will seldom be used.

We believe that our two phases, of LLMs vs random player (Section 3.1) then LLMs vs chess engine (Section 3.2), helps us to isolate instruction-following and reasoning, respectively. We consider the first phase less of a full reasoning evaluation and more of a sanity check to ensure that models are strong enough at instruction-following to behave reliably in our agentic setting. We argue that beating a random player is something we should expect most current LLMs to do on a regular basis given their stated reasoning abilities. The fact that many LLMs we evaluate can’t even reach a 50% Win/Loss signifies that there are pressing problems with how the LLMs behave (Figure 2). This shows that these LLMs have not even reached the bare minimum of what we would expect in a simple agentic setting in chess. While we might not be able to evaluate pure reasoning ability in the models that perform poorly in phase 1, we can still make conclusions about reaching the sufficient level of instruction-following that we require.

Then, for the second phase, we generally focus on models that were only able to complete the first phase without instruction-following errors, so can better isolate reasoning performance. For example, in Table 8 we see that o3, o4-mini, and Grok 3 Mini all have 0% instruction-following failures over all games vs random players. We note that o3-mini (low) and o3-mini (medium) still have instruction-following errors, so perhaps these models are thus underestimated in their performance. However, these models generally follow the expected rankings when we scale their reasoning effort, meaning reasoning is having a similar effect as it does in o4-mini. We note the other models are strong enough to pass the base level of instruction-following that we require. Thus we can say that reasoning makes up most performance differentials in the second phase, not instruction-following.

\---

\#\#\# \`W2: Lack of information in Figure 1 and ablation studies in appendix\`

Thank you for pointing these out. For Figure 1, we will enhance it to show more detail. Regarding the ablation studies, we have moved the corresponding table to the main body. We will share these soon in an updated version.

\---

\#\#\# \`Q1: Lack of including non-LLM baselines\`

We agree that including non-LLM baselines would help to increase explainability in our benchmark. We offer the following baseline performance levels into our leaderboard for comparison:

- Chess world champion Magnus Carlsen has an active profile at [chess.com](http://chess.com) and has Elo rating of 2839  
- The average [chess.com](http://chess.com) user has an Elo rating of 618  
- Random player vs Dragon has a rating of \-122.3 (when played against 1000 games each of skills 1-4)

We note that of our evaluated models, only o3 (low) is able to perform better when compared to the average [chess.com](http://chess.com) player, with all models thus showing significant room for improvement. We will include these baselines in an updated version of our paper and adjust the analysis accordingly.

\---

\#\#\# \`Q2: Can you extend this benchmark to other board games\`

We believe that this framework can be extended to other board games, as long as there is an engine or way to control the difficulty of the opposing non-LLM player. We believe future work could do this and thus give more power to claims of generalization.

\---

\#\#\# \`Q3: No report of runtime and API costs\`

To keep track of costs, we have created a user-friendly leaderboard website that reports an average game cost. For example, a single game simulation for o3 (low) cost $8.16. This will be released with the final version of the paper.

For background, each game log contains accounting of prompt and completion tokens that we used to calculate costs in the leaderboard. Though the logs contain response timings, we found that such times could vary significantly as often we used free API tiers and so saw more variation. We will include a summary of the cost information displayed in the leaderboard in the appendix in an updated version of the paper in the future.

\---

\#\#\# \`Q4: Will targeted fine-tuning quickly inflate leaderboard scores?\`

As with many tasks, we anticipate that fine-tuning would increase performance as the model learns the interaction setting and more knowledge about chess. However, we expect after a certain point, this improvement will stop. A key difference between our chess benchmark and other benchmarks is that chess is much more immune to memorization given its dynamic nature and combinatorial properties. Because of this, the games are dynamic: it is realistic for new board states to be seen during inference that were not in the training data. Training on every board state is infeasible in chess, as opposed to knowledge-based benchmarks that could all potentially be memorized. Hence we speculate that after some point of fine-tuning, increased general reasoning ability would be necessary to improve performance.

\---

\#\#\# \`W4: Implicitly equates chess reasoning with general reasoning\`

We acknowledge that we have emphasized the importance of reasoning in chess, and have noted that in some sense we can test the generalization of reasoning with this benchmark. By this we do not claim that good performance in chess equates to good general reasoning abilities, but instead that if we claim to have a general reasoner (which may be attributed to the reasoning-enhanced LLMs), it should be able to perform sufficiently well at chess. We also believe chess has insights that may be of general interest and be understood well by the public, as AI models historically have frequently used chess as a signal of progress.

Though we don’t run any experiments on other tasks outside of chess, we emphasize that the performance trends we witness are similar to those in popular math or coding benchmarks, though significantly less impressive. We see that non-reasoning models in general perform poorly against even a player making random moves, with no model reaching 50% Win/Loss in Figure 2\. However, powerful reasoning models (e.g., o3) are able to beat the random player almost everytime. These large differentials correspond to the large differences observed in reasoning vs non-reasoning models on other benchmarks. Additionally, in Figure 4a, we see that scaling the reasoning effort results in increased performance, as expected.

To compare our performance directly with a real task, we calculate the correlation between our Elo scores versus LiveCodeBench \[1\] performance on the intersection of all models in our chess engine experiments and the LiveCodeBench leaderboard. LiveCodeBench is a popular benchmark for competitive programming where reasoning models perform well. We take the Pass@1 score for comparison. We find that the scores have a pearson correlation coefficient of 0.686 (p-value: 0.0888), indicating a moderately strong positive correlation between scores on either benchmark. The corresponding table is below. We will update the paper in the future to include this.

| Model              | LiveCodeBench Score | ELO Rating |  
|--------------------|--------------------:|-----------:|  
| Grok-3-Mini (High) | 66.7               | 456.35     |  
| o3-Mini (High)     | 67.4               | 438.52     |  
| o3-Mini (Med)      | 63.0               | 210.75     |  
| o3-Mini (Low)      | 57.0               | \-85.30     |  
| o4-Mini (High)     | 80.2               | 407.61     |  
| o4-Mini (Medium)   | 74.2               | 311.11     |  
| o4-Mini (Low)      | 65.9               | 140.31     |

Together, these results suggest that our chess benchmark reflects the general trends on other reasoning tasks, albeit in their current form LLMs aren’t able to reach world-class performance in chess.

\---

\#\#\# References

\[1\] Jain, N., Han, K., Gu, A., Li, W. D., Yan, F., Zhang, T., ... & Stoica, I. (2025). LiveCodeBench: Holistic and contamination free evaluation of large language models for code. In International Conference on Learning Representations (ICLR 2025).

# ICLR

### TODO

#### Writing (Nick/Kyle)

1. Infuse rebuttals into main paper  
   1. ~~Justify assumptions~~  
   2. Justify the 30-game random rule  
   3. Go thru all the feedback, add it somewhere in paper, then check it off.  
2. Try to add bounds to the ablation studies (can we include via statistics)  
   1. See if we can treat each move independently or semi-independently so we can get realistic bounds (ask chat)?  
      1. Apparently this may not be really accurate since each move technically depends on previous moves, so the distribution of moves we see is not actually independent.  
      2. Maybe we can do some statistical analysis that says whether one is higher or lower than the other?

#### Experiments (Maxim)

1. Include experiments we already did  
   1. [https://github.com/maxim-saplin/llm\_chess/blob/main/data\_processing/dragon\_refined.csv](https://github.com/maxim-saplin/llm_chess/blob/main/data_processing/dragon_refined.csv)  
      1. New Dragon results since NeurIPS submission:  
         1. gpt-5-low: 35 (24 vs lvl 5 and 11 vs lvl 7, both still in-progress)  
         2. gpt-5-mini-high (33 vs lvl 5\)  
         3. gpt-5-nano (low, medium, high \- each level had 33 games vs levels 1, 3, 5\)  
         4. o3-mini-high (30 vs lvl 2, 33 vs lvl 3, 22 vs lvl 5 \- in-progress)  
         5. o3-mini-low (23 vs lvl 2\)  
         6. o4-mini-high (30 vs lvl 2, 33 vs lvl 3, 23 vs lvl 5 in-progress)  
         7. o4-mini-low (16 vs lvl 2\)

      2. Can you write the number of games vs random, vs each skill that we have too? For these new results or in total is fine as well  
         *A: When you hover over a model in the LB there’s a popup:*  
         ![][image4]  
         *Source data for vs Dragon is in [dragon\_refined.csv](https://github.com/maxim-saplin/llm_chess/blob/main/data_processing/dragon_refined.csv), elo data combining Dragon and Random is here: [https://github.com/maxim-saplin/llm\_chess/blob/main/data\_processing/elo\_refined.csv](https://github.com/maxim-saplin/llm_chess/blob/main/data_processing/elo_refined.csv)*  
           
2. Possibly do more experiments  
   1. Elo if necessary  
   2. Majority voting with gpt-5-nano on 3x, 5x, 7x?  
3. Add human performance for comparison, e.g., 1500 for class c players.

#### Miscellaneous

1. ~~Anonymize Repo via [https://anonymous.4open.science/](https://anonymous.4open.science/) and remove any details (e.g., AZURE\_OPENAI\_KEY\_W in `.env.example`)~~  
   1. Placing in \`[https://github.com/ncrispino/llm\_chess\_anon](https://github.com/ncrispino/llm_chess_anon)\`

# Rebuttals \-- Summary

\#\#\# Summary (for after discussion period)

We thank the reviewers for their thoughtful feedback and are encouraged by the recognition of the novelty and extensibility of the benchmark. Below, we briefly reiterate our contributions, highlight reviewer endorsements, and respond to remaining concerns.

\---

**Nick: Fill out the below:**

TLDR

We present \*\*LLM Chess\*\*, a benchmark for evaluating instruction-following and reasoning in the domain of chess. While chess performance has been measured before, we are the first to evaluate performance in a comprehensive setting with targeted evaluation goals.

While existing work has addressed how to generate and apply steering directions, \*\*selection remains heuristic or manual\*\*. COSMIC addresses this gap with a \*\*principled, output-independent similarity-based selection mechanism\*\*, choosing directions that \*\*maximize internal activation similarity\*\*. This approach:

\- Generalizes across adversarial and weak alignment settings

\- Is compatible with any existing activation steering method

\- Outperforms or matches prior techniques across a range of tasks

Our findings show that COSMIC:

\- Matches or exceeds existing direction selection methods under standard settings.

\- \*\*Robustly generalizes\*\* where heuristic or manual methods struggle or fail.

\---

Endorsements of Reviewers

We are happy that reviewers acknowledged the following benefits of COSMIC:

\#\#\# Intuitive and applicable within the field

\- j9ZX: \*“Evaluated against state-of-the-art intervention techniques”\*

\- 3uLe: \*”Interesting and very relevant and timely direction of work. Problem is well motivated and builds on recent work in the area”\*

\- jiNx: \*”proposed unsupervised target layer selection method is intuitive and could be considered a principled approach for steering positions in future applications”\*

\#\#\# Can be used successfully with standard steering methods for refusal

\- j9ZX: \*“Drop-in Replacement: COSMIC is a plug-and-play alternative for existing direction selection methods in activation steering.”\*

\- ZKHg: \*”similar-performing approach to existing methods using less assumptions on refusal behavior and negated the need for manual inspection of the refusal behavior”\*

\#\#\# Generalizes beyond the standard refusal steering scenarios

\- j9ZX: \*”Robust Across Scenarios: It successfully identifies refusal directions in: Adversarial setups, Weakly aligned models”\*

\- ZKHg: \*”experiments on adversarial settings and weak safety alignment go beyond a pure work on model steering and emphasize the robustness and usefulness”\*

\---

Concerns of Reviewers and Our Rebuttals

We are grateful for the reviewers’ detailed and constructive suggestions. Below, we address common themes from the reviews and explain the actions we’ve taken in response.

\#\#\# Dataset size concerns – \*\*New Results\*\*

\- \*\*j9ZX, ZKHg\*\* expressed concern over dataset size and robustness of evaluation.

\- \*\*New Results\*\*: After increasing our dataset sizes for generation, selection, and evaluation, we report preliminary results on three of our benchmarked models. We find that results are \*\*generally consistent\*\* across the experiments in Section 4 and 5, and that the experiment in Section 6 reports \*\*stronger results\*\* that specifically target harmful prompts with minimal effect on harmless prompts. We will include the full result sets in our final version.

\#\#\# No metric for text quality was reported – \*\*New Results\*\*

\- \*\*3uLe\*\* noted that we did not report effects of steering on text quality.

\- \*\*Action\*\*: We now include experiments using COSMIC \+ ACE/LCE on:

 \- The Pile (uncopyrighted subset, \~900K tokens)

 \- ALPACA (\~270K tokens)

Results show \*\*minimal degradation in text quality\*\*, consistent with baseline ablations reported in \[1\].

\#\#\# Use of the term "optimal" was misleading – \*\*Clarified\*\*

\- \*\*j9ZX, ZKHg, jiNx\*\* noted that the term "optimal" was used without sufficient support.

\- \*\*Clarification\*\*: We will remove references to “optimal” and clarify that COSMIC \*\*locally maximizes a scoring function\*\* as formalized in Section 3.3 based on activation similarity, rather than identifying a global optimum. 

\#\#\# Clarifications needed on pairing methodology and intuition – \*\*Clarified\*\*

\- \*\*j9ZX, 3uLe\*\* requested more detail on how activation pairs are constructed and why.

\- \*\*Clarification\*\*: We clarified that COSMIC pairs:

 \- Refusal activations (from harmful prompts) with \*\*steered refusal\*\* activations (from harmless prompts).

 \- Non-refusal activations (from harmless prompts) with \*\*steered non-refusal\*\* activations (from harmful prompts).

 

 By aligning these pairs via similarity, COSMIC better identifies consistent refusal directions. We have revised the explanation in Section 3\.

\#\#\# Theoretical grounding in metric space geometry – \*\*Intentionally Agnostic\*\*

\- \*\*jiNx\*\* requested a stronger theoretical foundation for COSMIC’s similarity-based approach.

\- \*\*Response\*\*: COSMIC is \*\*explicitly designed to explore\*\*, rather than assume, competing hypotheses about representational geometry—namely, the linear representation hypothesis motivating LCE and the affine function hypothesis underlying ACE. Grounding in either would bias the method. Instead, COSMIC’s neutrality allows it to \*\*test which assumptions best fit the model\*\*—a key strength, not a weakness.

\---

We once again thank all the reviewers for their useful suggestions and feedback.

# Rebuttals \-- Experiments

\#\#\# Experiments todo (prioritize jQFV as they are lowest score)

1. **TODO jQFV:**   
   1. 1\) Run Maia on various settings (this may already kind of be implemented? I saw some Maia in the repo) and   
   2. 2\) run Dragon 1 with higher Elo from 1100-1500. We can probably just choose o3 (low) vs. grok 3 mini (high), our top models, for this? I think we already have skill 10 for o3 (low).  
   3. [saikolasani@berkeley.edu](mailto:saikolasani@berkeley.edu)did Maia experiments  
   4. **\[DONE\]** Maxim: Run Dragon 1 skill 10 on grok 3 mini (high)  
      1. \_logs/dragon\_vs\_llm/lvl-10\_vs\_grok-3-mini-beta-high  
2. **TODO: Svei.** Wants reasoning model vs. reasoning model games. We can run an initial experiment with our top models, o3 (low) vs. grok 3 mini (high). Possibly can include others too depending on compute, but this is fine for now. This should be easy to do as it’s already implemented.  
   1. Maxim:   
      1. **\[DONE\]** we have runs for o3-mini (low/medium) vs o4-mini (low/medium): [https://github.com/maxim-saplin/llm\_chess/tree/main/\_logs/llm\_vs\_llm](https://github.com/maxim-saplin/llm_chess/tree/main/_logs/llm_vs_llm)  
      2. **\[DONE\]** o3 (low) vs grok 3 mini (high) is likely the only experiment we need  
      3. **\[PARTLY DONE\]** o4-mini low/medium vs Grok-3-mini low/high  
3. **TODO: Svei.** Take our ablation models **(Grok 3 Mini (low) o4-mini (low))** and test out a couple variations on the prompt, i.e., wording things differently. Maybe we have one that is reworded, one with added few-shot examples of successful traces of calling each function.  
   1. **\[DONE\]** Maxim – come up with 1 prompt variation, then 1 setting where we add examples to the existing prompt  
      1. *\_logs/ablations/llm\_vs\_random\_previous\_moves*  
4. **TODO Svei (no experiments needed).** Create a unified script that will run all the games against the certain skill levels (i.e., 1-5) and call the Elo script to calculate results  
5. **TODO Svei (no experiments needed).** Add license discussion in readme, remove komodo weights instead replacing with information on how to download. Also include more information on 1\) how to set up local models and 2\) how to calculate the Elo score.  
   1. **\[DONE\]** Maxim \- will do license concerns, local model setup, Elo calc – in paper repo ([https://github.com/LLM-CHESS/llm\_chess\_minimal](https://github.com/LLM-CHESS/llm_chess_minimal))  
6. **TODO USES.** Run top 2 (o3 (low) and Grok 3 Mini (high)) models in the only make\_move setting against our 1-5 (or some subset of these, e.g., {1,3,5} for cost) Elos, always providing the legal moves and current board like in the ablation. This will help us isolate instruction-following from reasoning abilities and thus make better conclusions.  
   1. We also can consider running the top non-reasoning models of gpt-4o and Qwen-2.5-Max against at least random and maybe our 1-5 (or, again, some subset) Elos since they do not make instruction-following mistakes so we can see if they are able to do reasoning or if they fail (this will help us isolate the reasoning abilities of playing against Dragon 1 vs. playing against random for non-reasoning models). Basically, if gpt-4o vs random in the original setting is equivalent to the results in this setting, that means that instruction following didn’t interfere with reasoning; else, it did.  
      1. **\[RUNNING\]**: Nick run gpt-4o, gpt-4o-mini, o3-mini (low) on only\_make\_move setting vs. random. This will tell us whether failures are due to reasoning vs. instruction-following.  
   2. **\[DONE\]**: Nick run grok 3 mini (high) vs. Elos {1,3,5} or some subset of them (ran on 1-5).  
      1. Should run o3 (low) but was getting timeout issues; I think it’s fine with just the grok since I ran vs more skills.  
7. **TODO jQFV, USES, 9zRm, SeKK**. Run top 2 (o3 (low) and Grok 3 Mini (high)) models in a new setting where only the list of UCI moves are provided, only make\_move is provided, and no legal moves or current board is provided (\`ablation/realistic.json\` in \`ablation\` branch – maybe can call ‘Previous Moves Alone’). This will again allow us to isolate the agentic approach and find out how much having a current board or legal moves matters. This is the ‘hard’ mode. Note in this setting if we ‘Failed to make move’ we don’t provide the FEN, we just tell it to try again. This is necessary bc we don’t provide the board state.  
   1. **\[DONE\]** Nick running o4-mini (low), grok 3 mini (low) vs. random.  
      1. if time & money can run o3 (low) vs random or Elo.

*(below we should prioritize less)*

8. **TODO: Svei**. Could benefit from the impact of finetuning on agent conversations in this framework. We could try this, not sure if this is really a priority though. It may be difficult to get correct traces given the way we saved everything.

\#\#\# Summary  
I would categorize the problems into the following:

1) The setting in the benchmark is weird and unaligned with what we think of when we think of chess. Specifically, previous moves should be provided, legal moves should not, the board state is not something that needs to be provided (we can just have a list of UCI moves that defined the whole game)  
- **Fix:**   
  - We should run the top two reasoning models on 1-5 Elo in a very constrained state where we have only make\_move but otherwise equivalent to our setting (legal moves, board are provided). This removes agentic and instruction-following concerns.  
  - We should run the top two reasoning models on 1-5 Elo in a very constrained state with only the list of moves from the start in UCI format. This makes it as difficult as possible.  
  - We want to clarify that we are not explicitly testing chess in the same settings that a human would play it but instead designing an agentic setting that uses chess.  
2) Need various ablations, clarifications.

# Rebuttals \- jQFV

#### **Official Review of Submission1125 by Reviewer jQFV**

#### **Summary:**

### This research introduces a chess-based benchmark for evaluating LLM reasoning capabilities, offering notable advantages through its extensible design that avoids contamination issues plaguing static benchmarks by scaling opponent difficulty rather than relying on fixed positions. The work is well-written and addresses an interesting problem using chess as a dynamic testbed. However, the benchmark's chess-specific design can be improved in detail, and the related works should be better covered.

### **Strengths Contributions:**

### S1: The investigated problem of using chess as a testbed to evaluate the reasoning capabilities of LLMs is interesting and significant

### S2: This paper is well written and easy to follow

### S3: Unlike other reasoning benchmarks that can be contaminated or easily saturated, the proposed benchmark is extensible by scaling the difficulty of the opponents and is not reliant on static board positions that can be included in training data

### **Limitations Weaknesses:**

### W1: Why only derive ELO estimate on a subset of models?

### W2: By having the two functions for get\_current\_board and get\_legal\_moves, the difficulty is significantly reduced because LLMs don’t need to correctly track board states and find legal moves by themselves anymore. But some benchmark works have shown that LLMs are still struggling in these basic concepts in chess. Such a design does not evaluate the real chess playing capabilities of LLMs. Instead, it’s using such a trick to enforce LLM to play blindly without ensuring the moves made are LLMs genuine understanding in chess. An extreme example is that, a function can be called to include Stockfish evaluations, which is apparently “cheating” but it’s also the so-called “agentic function calling”.

### W3: Why 10 conversations per ply are needed? The function will provide legal moves already, why 3 attempts needed to provide a legal action?

### W4: The design does not include move history of the current game. How did the system handle special rules like castling rights and 3 fold repetition? How did the system determine draws?

### W5: Why does LLMs always play black in random player experiment?

### W6: Why Komodo Dragon 1? Why not use later versions? Why not use Stockfish? Maia? The max ELO included for chess engine is 750, which is super low, where moves are still very random. Although the authors said this can be easily extend to higher elo as LLMs evolve, it’s interesting to see the results now with some more reasonable ELO ranges like 1100\~1500.

### W7: Missing human-like chess engines in related works, such as the Maia series and ALLIE

### **Ethical Considerations:** No, there are no or only very minor ethics concerns

### **Dataset Code Accessibility:** Yes

### **Rating:** 2: Reject: For instance, a paper with technical flaws, weak evaluation, inadequate reproducibility and incompletely addressed ethical considerations.

### **Confidence:** 4: You are confident in your assessment, but not absolutely certain. It is unlikely, but not impossible, that you did not understand some parts of the submission or that you are unfamiliar with some pieces of related work.

### **Code Of Conduct Acknowledgement:** Yes

### **Responsible Reviewing Acknowledgement:** Yes

## Takeaways

Their main problems seem to be the formulation of the experiments (why do we design the tools we do, eschew simpler & more realistic settings).

**Idea**: We should consider having a new setting in the benchmark where we only test the real-world chess-realistic setting. This seems like the best way to isolate agentic abilities in chess (instruction-following) & reasoning. Note this will not be as expensive to run since we only need to do max attempts of 3 instead of 10 conversation per ply. We can run on o3-mini (low) and grok-3-mini (high) with the same ELO settings. Here we can just provide the current board and legal moves and do the only make\_move ablation setting.

## Response

Thank you for your valuable feedback. In general, we want to be clear that our benchmark aims to evaluate both instruction-following and reasoning in the domain of chess. Specifically, we consider an agentic setting, and tailor several key design decisions accordingly. We first summarize and justify each of these decisions. Then, we provide detailed responses to each of your concerns below:

\---

\#\#\# \`Explanation of Design Decisions\`  
We acknowledge that our benchmark includes settings that deviate from what you would find in the real-world. However, our goal was to use chess as a testbed to evaluate different aspects of LLMs including instruction-following and measuring the abilities of reasoning models beyond simple move completion settings. The main deviation was our introduction of tools, i.e., the ability to see the current board or legal moves with a tool call. While it may seem unorthodox, the results show that introducing such an agentic approach is useful in measuring instruction-following, a central goal of the benchmark: of the 44 models we tested vs a random opponent, we see instruction-following errors are responsible for 71.9% of all games ending for non-reasoning models and 24.4% for reasoning models, on average. Even more powerful models we might not expect to have such errors, e.g., Deepseek-R1 or o3-mini (low), show non-negligible problems with instruction following.

Other design choices we made beyond the agentic setting was supplying the current board and legal moves but not providing the previous moves. We justify each choice below, which we will add to the limitations section of our paper:

\*\*Board State\*\*  We assume that the model is able to see the full board at any time, differing from some models that see only the previous moves or a pgn description of the game. We chose this to be more similar to what a human player or chess engine would see.  
   
\*\*Legal Moves\*\*  We decided to provide legal moves to simplify the benchmark, as current capabilities of models are not yet enough to play consistently without providing the legal moves. See Table 6 in Appendix B, where not including legal moves causes a decrease in win/loss of \~30% for grok-3-mini-low and \~10% for o4-mini (low) compared to the baseline (note for legal moves and its comparison we use the FEN setting as without legal moves, we cannot know castling rights or en passant). Essentially, including the legal moves was a practical concern: it allows us to have more granularity between models by boosting their performance and preventing clustering at low performance due to move failures.

\*\*Previous Moves\*\* We chose not to include previous moves to increase similarity with existing AI approaches for playing chess. Chess engines like Stockfish can evaluate the best move given a board state alone without any move history. If LLMs are to reach the level of other AI systems in chess, we believe it is helpful to see them perform under these same constraints. So, we decided not including previous moves would result in a more challenging and ideal goal for LLMs. This decision not to include previous moves was made during the initial trials of the benchmark during its creation, while experimenting with different prompts across a subset of models. During these experiments, including the history bloated the prompt and made some of the models struggle more with instruction-following, so we also chose this setting as a practical concern. Moreover, in our paper, we analyzed performance of including previous moves in our ablations in Table 6\. We found that while including previous moves in the prompt did improve performance, the change was varied and altogether not drastic, suggesting that if anything, the previous moves can help reduce complexity and blunders, not increase them.

\---

**\#\#\# \`W1: Why only derive ELO estimates on a subset of models?\`**  
For LLM Chess, we created a two-phase evaluation system: (1) we test models against a random player (a player which takes a random legal move each step), then (2) we test only the best models against Dragon and compute Elo. Essentially, our two stage pipeline can be seen as primarily evaluating instruction-following in the first stage (by making the necessary reasoning as simple as possible, i.e., just the ability to close out a game against random moves as described in W2). Then, in the second stage, we focus on scaling the difficulty of reasoning, as we already know that instruction-following will not be an issue for the models that proceeded. We view the first stage as a heuristic that lets us narrow down our focus to only those models we believe would be most valuable to have an ELO score for (which is necessary given the cost of experiments).

\---

\#\#\# \`W2: The use of tools for board states and legal moves\`  
In this work, we use chess as a testbed to evaluate models for both reasoning and instruction following. Accordingly, we made several design decisions that diverge from how a human may play chess, described at the start of this response. Most importantly, we observe that even in our simplified setting, many state-of-the-art LLMs cannot reliably beat a player making random moves each turn. And even when we evaluate versus chess engines, we find top reasoning LLMs are weak against relatively low ELO opponents. As a result, we don’t believe that our setting reduces the difficulty too much to not be of use; in fact, we see in LLM Chess there is still much room for improvement. We believe there is a soft spot between the most difficult chess setting you detailed and the hypothetical where the LLM can call a tool with Stockfish evaluations that is still sufficiently challenging for LLMs but not too hard as to make results too similar. This is where we want LLM Chess.

While we agree that our evaluation is not testing what we may think of as “pure” chess performance, we made practical decisions (i.e., inclusion of legal moves) that balance evaluation with our desire to evaluate instruction-following and agentic capabilities in the context of reasoning. In the future as capabilities improve and LLMs reach higher Elos, we can consider dropping some of our assumptions to make the benchmark even harder.

\---

\#\#\# \`W3: Why do we need 10 conversations per ply and 3 attempts at making legal moves?\`

We limit the number of turns per ply to 10 to enable the LLMs to make function calls beyond make\_move (e.g., get\_current\_board or get\_legal\_moves). The 3 attempts are necessary if 1\) the LLM does not call get\_legal\_moves, or 2\) the LLM does call get\_legal\_moves but doesn’t provide a valid move to make\_move. For example, the LLM may first call get\_current\_board, then try to make\_move with an invalid move, then hallucinate an action get\_legal, then call get\_legal\_moves, then call make\_move with a correct move. By allowing 3 attempts, we enable the LLM to recover from an invalid move or action. Importantly, the legal moves are not always provided; the LLM must first decide to call the tool to obtain them. This is not guaranteed. Also, even if they do call the tool, we see in practice that sometimes LLMs aren’t able to consistently choose a legal move, so want to give them a chance.

\---

\#\#\# \`W4: Since no move history is provided – how does the system handle special rules and draws?\`

Through all of our experiments, we use python-chess to handle the underlying logic (e.g., move validation and state management) of chess games. The agentic functions (e.g., get\_legal\_moves) interact with this library. Hence, if a player cannot castle, that will be reflected in the legal moves returned by get\_legal\_moves. Similarly, draws are also determined by python-chess or result from the 100 move cap placed on the game. See our discussion at the top of this comment for why we chose not to include move history.

\---

\#\#\# \`W5: Why does LLMs always play black in random player experiment?\`

When we created the benchmark, we fixed the LLM to play as black to simplify the setup and reduce the number of experiments, thus lowering the already-high cost. As the benchmark progressed, we maintained this decision for consistency such that all models can be directly compared, though we acknowledge in an ideal world we would also play as white. Since we only play as black, we adjust the ELO calculations to account for it; see Appendix A.4 for further discussion.

\---

\#\#\# \`W6: Why Komodo Dragon 1?\`  
The main reasons we chose Komodo Dragon 1 were as follows:  
1\) its skill levels are pinned to Elos on \`chess.com\`  
2\) it supports simulating players with ELOs as low as 250\. This is particularly important in order to reliably calculate ELO: Even in their weakest settings, Stockfish and Maia achieve much higher ELOs, which would considerably increase the number of games that need to be played in order to derive confidence intervals of the same width. For instance, we estimate the ELO of the lowest level of Stockfish playing against Komodo Dragon 1 as 824, substantially higher than 250\.  
3\) it is available for free online, unlike the newer versions of Dragon.

Though 750 ELO (Dragon Level 5\) is low, we found that is where the capabilities of the models belonged given our agentic setting. In response to your concerns, we share the pct of checkmates of the top two models against Dragon Level 10 (ELO 1375):  
|LLM|Dragon Level 5 (750 ELO)|Dragon Level 10 (1375 ELO)|  
|---|---|---|  
|o3 (low) | 42.86% | 0% |  
|Grok 3 Mini (high) | 0% | 0%|

We find that even the top models cannot win any games against Level 10, suggesting that the more realistic ELO ranges are still too high for current models in LLM Chess. As models become more capable, we can incorporate additional games against higher level players.

\---

\#\#\# \`W7: Missing human-like chess engines in related work\`

We acknowledge that our related work is missing human-like chess engines like Maia and ALLIE and will extend its thoroughness in our final version. Thank you for this feedback.

\---

### \#\#\# Old stuff

*This is because we find that most models cannot reliably beat a random player (with an ELO near \-225). Meanwhile, at its lowest skill level, Dragon achieves a significantly higher ELO near 250\. The intuition is that if a weak LLM cannot adequately follow instructions and play a game in our agentic setting, we need not include them against better opponents (i.e., Dragon).*

*Still, we can extrapolate the ELOs of weaker LLMs by (1) playing a significant number of games between a random player and Dragon to derive an ELO for the random player, then (2) deriving ELOs for weak LLMs based on their games against the random player. We share some of those results below, but ultimately chose not to include the results due to the wider confidence intervals. With a larger budget for inference, we intend to run more simulations to tighten the confidence intervals.*

*| LLM                    | ELO     | ±95% CI |*

*|--------------------------|---------|---------|*

*| dragon-lvl-1             | 250.0   | \-       |*

*| Claude 4 Sonnet (thinking) | 47.0    | 118.8   |*

*| Claude 4 Sonnet          | \-10.9   | 114.7   |*

*| Gemini 2.5 Pro Preview   | \-70.7   | 105.2   |*

*| random                   | \-122.3  | 23.0    |*

*| DeepSeek-R1              | \-216.2  | 130.8   |*

*| DeepSeek V3              | \-822.8  | 342.9   |*

(regarding llms always as black)  It also allows the engine to dictate the start of the game instead of the LLM (not sure if this is good, bad, neutral).

# jQFV response

Thanks a lot for the rebuttal, it solved some of my concerns. However, I still found the setting problematic and it does not evaluate the true chess-playing capabilities of llms. In particular, the available tools to get legal moves and the retries prohibit the evaluation of actual chess-playing abilities because they provide additional error-correction beyond the original chess understanding of llms. I understand that the authors just want llms to play chess normally, but (1) If functions and tools are available, the extreme would be just to call Stockfish as a function. (2) In FIDE-rated chess tournaments, when a player makes an illegal move, there will be consequences depending on the time control and when the illegal move is discovered. While in this setting, making illegal moves (once or \< \#retry) does not have any consequences, which is a flawed setting. On the other hand, arguments made about special moves and repetitions do not hold if being "agentic" does not make sense.

If we see this work through the lens of instruction following and agentic function calling, many more functions and tools (e.g., king safety, pins, forks, and much more) can be highly useful for chess-playing. The choice of only using a few naive functions is not ideal.

I acknowledge that this work is of good quality, but the settings do not make much sense in the context of chess. I will keep my original evaluation, unfortunately.

Thank you for the response; we are glad that our rebuttal was able to solve some of your concerns. As for the setting, we want to emphasize that we are focused on evaluating instruction-following and reasoning in an agentic setting \*\*using chess as a testbed\*\*. We believe there is a fundamental misconception about the goal of our benchmark: we are not evaluating true chess-playing capabilities as one may define it in a human tournament, but rather using chess as a backdrop to evaluate instruction-following and reasoning. 

When evaluating chess engines, it is not uncommon to vary the information provided based on the capabilities of the models being evaluated. For example, Deep Blue, early versions of Stockfish, and other early chess engines used opening books and endgame databases to improve performance but were still compared to humans. It would thus be analogous in our case to include such information as tools for the LLM and there would be precedent for it to be accepted as a valid chess setting. Though we didn’t decide to use opening books or endgame databases, we did make the design decision to provide legal moves, which we found useful given the limitations of current LLMs. 

Clearly, there is a large capability gap between providing Stockfish as a tool and providing the legal moves alone; with legal moves, models still need adequate reasoning ability to perform well, as shown in our experiments. In practice, providing Stockfish as a tool would all but eliminate the ability for reasoning. In agentic settings, models are often provided with additional information, e.g., the ability to do web searches, in order to improve their performance in question answering tasks. We could argue that in such settings, the equivalent to calling Stockfish as a tool in chess would be a setting where we provide a tool that retrieves the exact website in which the answer to a given question is present. The fact that we can craft such a setup does not negate the utility of the LLM and web search setup described before; in reality, there is a large capability gap between needing to search for information over all websites versus being provided the target website exactly. The proposed Stockfish as a tool versus legal moves comparison lies in a similar paradigm to this exact website vs ability to search all websites setting, where the legal move setting still has much utility and the ability to test model capabilities, even though the ability to retrieve more information is provided compared to an LLM-only baseline.

Regarding the ability to retry moves, we again emphasize the difference between a human chess tournament setting and our testbed setting. In agentic applications, it is common to give models the ability to self-correct and recover to increase their robustness. Thus we believe it is important to include in our benchmark, else the performance would be much lower. Again, it is a matter of aligning with agentic instruction-following work versus being a perfect representation of the true chess-playing capabilities of LLMs.

As for your comment regarding the selection of tools, we agree that providing more tools may be valuable, especially to help us better understand the capabilities LLMs currently lack. However, the choice of our set of tools was meant to be as simple as possible while still allowing agentic thinking. The current board and legal moves are basic enough such that they provide information to the model but not any specific strategy. We wanted to maintain a setting for the benchmark in which the LLMs still had to think about deeper strategies, e.g., deciding to use pins and forks. If we didn’t include our set of tools, we would not have been able to evaluate instruction-following as well, which was a goal of the benchmark.

Overall, we crafted this benchmark with such design decisions as to enable testing agentic instruction-following and reasoning, while still evaluating on a reasonable chess setting. We acknowledge that other settings could be crafted that have their own benefits and may reflect better on human chess tournaments, but we believe the ability to craft such settings does not refute the assertion that our benchmark still adequately tests reasoning abilities in the chess setting and is difficult enough to be of value.

\#\#\# kyle’s

Thank you for the response; we are glad that our rebuttal was able to solve some of your concerns. We believe there is a fundamental misconception about the goal and contribution of our benchmark: \*\*Our intent is not to measure the pure chess playing abilities of LLMs, but rather to evaluate LLMs for agentic reasoning and instruction following using chess as a testbed.\*\* As such, we’ve made a number of decisions (e.g., tools, retries, etc.) that diverge from FIDE-rated chess tournaments in order to better mimic this agentic setting that is the focus of our work. Namely, our setting focuses on providing LLMs a set of actions (tools, legal moves) upon which to act, a common setting for agents. We can view reasoning as the ability to best select these actions and instruction-following as the ability to select valid actions without error. Our benchmark is constructed with these ideas in mind, with chess being a great environment to test such abilities. We respond to each of your concerns below:

\*\*If functions and tools are available, the extreme would be just to call Stockfish as a function.\*\*  
There is a large capability gap between providing Stockfish as a tool and providing a tool that lists the legal moves. In practice, providing Stockfish as a tool would all but eliminate the need for reasoning. Providing the legal moves simplifies reasoning, but as shown in our experiments, models still need strong reasoning abilities on our benchmark to perform well. Even if the legal moves are known, it is still difficult to choose the best move at each ply.

\*\*Many more functions and tools (e.g., king safety, pins, forks, and much more) can be highly useful for chess-playing.\*\*  
We evaluate all models with a fixed selection of tools. Our tool selection was intended to be as simple as possible while still enabling an agentic setting. This selection is basic enough to make games accessible to weaker LLMs but doesn’t impose an explicit game strategy (as having a tool for pins or forks might) so that we can effectively measure reasoning ability, a core focus of our benchmark. As models become more capable, we can revisit the tool selection and incorporate new, more complex tools, which we leave for future work.

\*\*Making illegal moves does not have any consequences.\*\*  
Again, we emphasize that our benchmark is not intended to measure the raw chess playing abilities of LLMs. Allowing retries mimics standard agentic workflows which enable LLMs to self-correct and recover. 

# Rebuttals \- v3Yi

#### **Official Review of Submission1125 by Reviewer v3Yi**

**Summary:**  
This paper introduces LLM CHESS, a novel and insightful evaluation framework designed to benchmark the generalisation of reasoning and instruction-following abilities in large language models (LLMs) through extended agentic interaction within the domain of chess. Its agentic, dynamic nature helps reduce overfitting compared to static benchmarks. Reasoning models did much better and made fewer errors than others. But even the best LLMs only scored around 758 Elo—well below human master level. Giving models info directly (instead of making them ask) helped performance. A leaderboard, dataset, and framework will be shared to support future research.

**Strengths Contributions:**

* Novel methodology: LLMs play chess in an agentic way via actions and tries to reason on chess rules and take decisions.  
* Comprehensive Metrics: The framework provides different levels of metris such as per-model, per-game and per-ply metrics.  
* Extensive experimental setup: over 50 open and closed-sourece models are evaluated.  
* Reproducibility: The authors commit to releasing the experimental framework, a public leaderboard, and the dataset of games.

**Limitations Weaknesses:**  
The study had limits like a 100-move cap, short conversations per move, prompt length limits, and 10-minute timeouts that could cut off reasoning. The compute setup used was also not specified.

**Ethical Considerations:** No, there are no or only very minor ethics concerns  
**Dataset Code Accessibility:** Yes  
**Dataset Code Comments:**  
The authors provided a github link with clear, documented code.

**Rating:** 5: Accept: Technically solid paper, with high impact on at least one sub-area of AI or moderate-to-high impact on more than one area of AI, with good-to-excellent evaluation, resources, reproducibility, and no unaddressed ethical considerations.  
**Confidence:** 4: You are confident in your assessment, but not absolutely certain. It is unlikely, but not impossible, that you did not understand some parts of the submission or that you are unfamiliar with some pieces of related work.  
**Code Of Conduct Acknowledgement:** Yes  
**Responsible Reviewing Acknowledgement:** Yes

## Takeaways

No additional experiments needed, nice review.

## Response

Thank you for your valuable review and comments\! We are glad you have seen the novelty, comprehensiveness, and reproducibility of our benchmark.  
\---

**\#\#\# \`W1: Limits on number of moves, conversations per move, length of prompt and timeouts\`**

\*\*Move limit\*\*: We limited each game to 100 moves, which is reasonable considering the average human game duration is \~40 moves. Furthermore, our limit was based on several observations:  
\- Games longer than 50 moves tend to drag on infinitely until a draw (insufficient material).  
\- Weak non-reasoning models often lost on technicality (e.g., violate instructions, hallucinate moves) long before 100 moves.  
\- Strong non-reasoning models often reached the limit, but made little game progress.  
\- Reasoning models (e.g., o3) could beat the random player in 20-40 moves.

\*\*Conversations per move\*\*: We limit the length of the conversation to 10\. Strong models tend to have only 3 turns per conversation (get\_board\_state, get\_legal\_moves, and make\_move), with some (i.e., o3, o4-mini) occasionally skipping get\_legal\_moves. Strong models generally recover quickly from any mistakes. Weaker models tend to either hallucinate early (e.g., making two illegal moves and ending the game) or get stuck in loops (e.g., requesting board state and legal moves infinitely). Limiting the length of the conversation contains failures and reduces costs.

\*\*Length of prompt\*\*: Because each move happens in its own context, prompt lengths stay short and rarely exceed a model's limit. 

\*\*Timeouts\*\*: We set the timeout to 10 minutes. Only OpenAI’s reasoning models (specifically, o3-mini, o3, and o4-mini) occasionally reached the timeout with high reasoning effort. We believe this was a server-side issue, as increasing the timeout to 20 or 60 minutes didn’t resolve the issue.

\---

**\#\#\# \`W2: Compute setup was not specified\`**

We detail our hardware and experimental settings in Appendix A. Table 3 indicates which models were run locally (on a RTX 4090\) and which were via API. 

\---

# Rebuttals \- Svei

#### **Official Review of Submission1125 by Reviewer Svei**

Official Reviewby Reviewer Svei16 Jul 2025, 17:06 (modified: 24 Jul 2025, 08:15)Program Chairs, Senior Area Chairs, Area Chairs, Reviewers Submitted, Authors, Reviewer Svei[Revisions](https://openreview.net/revisions?id=XtEMKWAzxy)  
**Summary:**  
The authors propose a new benchmark for evaluating reasoning/instruction-following abilities of LLMs based on their chess playing ability. Through extensive experiments, the authors find that all non-reasoning models struggle to checkmate even a random opponent (often due to a failure in instruction-following). Reasoning models still struggle somewhat but are generally able to checkmate their opponent in a majority of games. The authors then test the performance of these models against a chess engine of varying levels (and then estimate their elo). They find that even the best performing model o3 (low), has an elo of \~750, quite below the elo of adept chess players.

To analyze the impact of test-time scaling, the paper analyzes the impact of scaling deep (reasoning levels) and wide (mixture of agents) and find the former improves performance noticeably while the latter doesn't. Finally, the authors ablate various design decisions including board representation, available actions to the agents and knowing previous moves.

**Strengths Contributions:**

* The idea is promising and novel. There is some work testing the performance of LLMs at chess or training them to play chess but never at this scale and not proposing it as a benchmark.  
* As more and more benchmarks begin to saturate, the poor performance of many models and large discrepancy relative to human performance point to the benchmark being useful for evaluating progress from some time.  
* Thorough experiments on a large variety of models including various ablations.  
* The stochastic/dynamic aspect of this benchmark mentioned by the authors seems particularly valuable. Other benchmarks often face concerns of overfitting/memorization due to answers potentially ending up in the training set of the new model. Instead chess is particularly hard to memorize due to the branching factor of the game and its precise nature (in many positions, all but a handful moves are losing).  
* The code for the benchmark is well-structured.

**Limitations Weaknesses:**

* The paper could benefit from an analysis of the impact of finetuning on agent conversations in this framework (does it significantly improve performance/instruction-following)?  
* The paper could examine the performance of certain models against each other (at least between reasoning models).  
* It would be helpful to precisely describe an actual benchmark (e.g. the benchmark is the estimated elo using script compute\_elo.py from the agent playing 10 games against each of Dragon 1 level {1, 3, 5}). The repo could then have a script to run all the required games and compute the elo as well as a leaderboard of top models.  
* Have you tested variations of the prompt, in particular including examples?  
* From the ablations it seems that models perform better with the ASCII representation than the unicode one. Should this perhaps be the default (maybe the models haven't seen enough unicode chess piece data)?  
* ~~Is the chess engine at least somewhat stochastic? Otherwise, the benchmark could also suffer from the concerns of memorization.~~

If some of my questions/concerns are addressed, I would be willing to raise my score to Accept.

**Ethical Considerations:** No, there are no or only very minor ethics concerns  
**Ethics Flags:** Data privacy, copyright, and consent  
**Ethical Comments:**  
The inclusion of the Komodo weights in the GitHub (should instead include a link) is potentially problematic as their website ([https://komodochess.com/store/](https://komodochess.com/store/), cited in bibliography) includes the following disclaimer at the bottom of the page: "Komodo is protected by copyright. Komodo, even our freeware versions, can not be redistributed on other webistes." In general, there could be further discussion of licenses as the authors state that "their respective licenses and terms of use are noted in our bibliography and supplemental material."

Other than that, no ethical issues as the benchmark simply proposes testing LLMs performance at chess.

**Dataset Code Accessibility:** Yes  
**Dataset Code Comments:**  
The code appears to be well-structured and clean. There is reasonable documentation describing how to get started and how to modify the various configurations. The use/testing of models by major providers is straightforward.

However, it would be helpful to have an example demonstrating how to evaluate a custom local model (e.g. a researcher finetunes a given open source model locally and wants to test its performance on the benchmark. This should be in the main README.md. In addition, there is little description of how to use the elo computation score.

**Rating:** 4: Borderline accept: Technically solid paper where reasons to accept outweigh reasons to reject, e.g., limited evaluation. Please use sparingly.  
**Confidence:** 3: You are fairly confident in your assessment. It is possible that you did not understand some parts of the submission or that you are unfamiliar with some pieces of related work. Math/other details were not carefully checked.  
**Code Of Conduct Acknowledgement:** Yes  
**Responsible Reviewing Acknowledgement:** Yes

## Takeaways

This reviewer mostly had suggestions for the future and various ablation-type tests that are easy to run.

## Response

Thank you for all your suggestions to help us improve the paper, especially your specific comments regarding our codebase. We have addressed all of them below:

\---

**\#\#\# \`W1: Could benefit from the impact of finetuning on agent conversations in this framework\`**

While our current focus is on benchmarking LLMs off-the-shelf in our agentic chess setting, we agree that people will naturally want to improve their models’ performance in chess through finetuning, e.g., in existing work like \[1\]. We will consider this a future direction, especially given the development of large reasoning models that have yet to be sufficiently finetuned and evaluated on this task. As noted by the reviewer, we will make it easier to use local models in the framework so others can share their performance, as well as considering finetuning our own models given existing work to use on our benchmark.

\---

**\#\#\# \`W2: Could examine the performance of certain models against each other (at least between reasoning models)\`**

In response to your comment, we have conducted LLM vs. LLM experiments below with o3-mini (low) vs o4-mini (low) and o3-mini (medium) vs. o4-mini (medium), both as black and white for 33 games on each setting. Results are below:

\#\#\# Low Reasoning  
| Model | As White | As Black | Average |  
|-------|----------|----------|---------|  
| \*\*o3-mini\*\* | Win: 6.06% | Win: 3.03% | \*\*Win: 4.55%\*\* |  
| | Draw: 57.58% | Draw: 24.24% | \*\*Draw: 40.91%\*\* |  
| \*\*o4-mini\*\* | Win: 72.73% | Win: 36.36% | \*\*Win: 54.55%\*\* |  
| | Draw: 24.24% | Draw: 57.58% | \*\*Draw: 40.91%\*\* |

\#\#\# Medium Reasoning  
| Model | As White | As Black | Average |  
|-------|----------|----------|---------|  
| \*\*o3-mini\*\* | Win: 3.03% | Win: 0.00% | \*\*Win: 1.52%\*\* |  
| | Draw: 72.73% | Draw: 66.67% | \*\*Draw: 69.70%\*\* |  
| \*\*o4-mini\*\* | Win: 33.33% | Win: 24.24% | \*\*Win: 28.79%\*\* |  
| | Draw: 66.67% | Draw: 72.73% | \*\*Draw: 69.70%\*\* |

In Figure 3, we found the Elos of the above models were as follows: o4-mini (medium) was 311.11, o3-mini (medium) was 210.75, o4-mini (low) was 140.31, and o3-mini (low) was \-85.30. Our LLM vs LLM results follow a similar pattern – o3-mini (low) only has an average win rate of 4.55% compared to o4-mini (low) of 54.55%, which is expected on account of the over 200 point difference in Elo. On the other hand, o3-mini (medium) has an average win rate of 1.52% compared to o4-mini (medium) of 28.79%. This is a lower jump in performance than for the other two models, which better aligns with their only 100 point difference in Elo.

Overall, the LLM vs. LLM setting seems to align well with the scores we found through our Elo calculations. We will include these results and select others in a separate section in the final version of the paper.

\---

**\#\#\# \`W3: Lacking an actual benchmark formulation\`**

Currently, we have a general structure where we benchmark models in two stages, one against random and the other a chess engine. However, we agree that we should be more explicit about how to add models and unify the structure of the evaluation results. For this, we propose a simple system that we will follow in the future: 

Given a new LLM, first we play 30 games vs random to get a general sense of model capabilities. Then, if performance is above 50% (a heuristic to ensure we catch all models with the potential to perform well), we play against skills 1-5, each with an equal number of games. 

While this is appropriate for models with current capabilities, to future-proof the design of our benchmark we propose playing the current model against every skill in one of two brackets of skills, chosen based on performance: {1, 3, 5, 7, 9, 11} and {12, 14, 16, 18, 20, 22, 24} (differences between neighboring skills are usually negligible, so we propose to use every other skill instead). With this bracket-based design, we do not have to run a very powerful model against skills we know it can always beat, nor do we need to run a weak model against powerful skills it will always lose too, thus maintaining coverage of all skills but lowering costs.

As per your advice, we will construct a script that automatically runs the full pipeline and calculates the results, then will adjust our online leaderboard to use this and allow others to submit models using results obtained from the same script as well.

\---

**\#\#\# \`W4: Lacking testing of variations of the prompt with examples\`**

We agree that prompt sensitivity could have an non-negligible impact on performance. To address this, we define two new experimental scenarios: one with a simplistic version of the prompt (\*You are playing Black. Your reply must be ONE line and must be exactly one of: get\_current\_board · get\_legal\_moves · make\_move \<uci\>\*) and another with the original prompt but with three examples of moves being made given either the board state, legal moves, or both. We present the Win/Loss% for our ablation models on 42 games (note the baseline LLM Chess setting is with 30 games as presented in Table 6):

| Model | LLM Chess | Simple prompt | Prompt with examples |  
|-------|-----------|---------------|---------------------|  
| Grok 3 Mini (low) | 61.7 | 45.2 | 48.8 |  
| o4-mini (low) | 73.3 | 52.4 | 63.1 |

We see these prompts can have decent impacts on performance. We will explore more and add these results to our ablation section in the final version of the paper.

\---  
**\#\#\# \`W5: Models perform better with ASCII\`**

This is a good point – unicode chess pieces may have different frequencies and locations in training data relative to ASCII text. As such, it may decrease chess performance. We will further expand our ablation studies regarding board state to better analyze performance differentials with ASCII instead of unicode.

\---

**\#\#\# \`W6: \`Is the chess engine stochastic? If so, there could be concerns of memorization\`**

This is a good question. As we use it, the Dragon chess engine is stochastic: to verify this, we ran 1000 games between Dragon skill 1 vs skill 2\. We found that game metrics such as player material count and game duration variate significantly (standard deviation is 10-40% of the mean) which suggest the game engines are not deterministic and actually demonstrate a good deal of variance. Note also that we use a temperature greater than 0 when generating responses from the LLMs so the moves will be different. Taken together, we believe memorization will not be a problem for the benchmark.

\---

**\#\#\# \`License Issues and Code Improvements\`**

Thank you for pointing out the license issue regarding Komodo; we have removed the Komodo binaries from our repo and will be sure to include a further discussion of the licenses in the README in an updated version. We also will ensure to allow more direction in the code regarding how to add new models and run our full pipeline including Elo computation. We appreciate all your suggestions to improve the quality of the code.

\---

\#\#\# References  
\[1\]: Xidong Feng, Yicheng Luo, Ziyan Wang, Hongrui Tang, Mengyue Yang, Kun Shao, David Mguni, Yali Du, Jun Wang:  
ChessGPT: Bridging Policy Learning and Language Modeling. NeurIPS 2023

### \#\#\# Old todos

\+----------------------------------------------------+-------+------------------+------------------+-------------+  
|              LLM (white) vs LLM Black              | Games | White Win Rate % | Black Win Rate % | Draw Rate % |  
\+----------------------------------------------------+-------+------------------+------------------+-------------+  
|                 ~~4o\_mini\_vs\_flash\_2                 |   30  |      26.67       |      70.00       |     3.33    |~~  
~~|                4o\_mini\_vs\_haiku\_35                 |   30  |       3.33       |      60.00       |    36.67    |~~  
~~|                 flash\_2\_vs\_4o\_mini                 |   29  |      27.59       |      72.41       |     0.00    |~~  
~~|                flash\_2\_vs\_haiku\_35                 |   25  |      12.00       |      88.00       |     0.00~~    |  
|     **grok-3-mini-beta-high\_vs\_o3-2025-04-16-low     |   33  |       0.00       |      69.70       |    30.30    |**  
**| grok-3-mini-beta-high\_vs\_o4-mini-2025-04-16-medium |   19  |      15.79       |      31.58       |    52.63    |**  
**|   grok-3-mini-beta-low\_vs\_o4-mini-2025-04-16-low   |   32  |      15.62       |      12.50       |    71.88    |**  
|                ~~haiku\_35\_vs\_4-o\_mini                |   30  |      36.67       |      23.33       |    40.00    |~~  
~~|      haiku\_35\_vs\_4o\_mini\_messaed\_player\_names      |   30  |      56.67       |      43.33       |     0.00    |~~  
|             **o3-mini-low\_vs\_o4-mini-low             |   33  |       6.06       |      36.36       |    57.58    |**  
**|          o3-mini-medium\_vs\_o4-mini-medium          |   33  |       3.03       |      24.24       |    72.73    |**  
**|   ~~o4-mini-2025-04-16-low\_vs\_grok-3-mini-beta-low   |   31  |      12.90       |       9.68       |    77.42~~    |**  
**| ~~o4-mini-2025-04-16-medium\_vs\_grok-3-mini-beta-high |   19  |      10.53       |      15.79       |    73.68~~    |**  
**|             o4-mini-low\_vs\_o3-mini-low             |   33  |      72.73       |       3.03       |    24.24    |**  
**|          o4-mini-medium\_vs\_o3-mini-medium          |   33  |      33.33       |       0.00       |    66.67    |**  
**\+----------------------------------------------------+-------+------------------+------------------+-------------+**

For prompt ablations:  
Model | LLM Chess | Simple prompt | Prompt with examples  
Grok 3 Mini (low) | 61.7 | 0 wins, 4 losses, 38 draws | 3 wins, 4 losses, 35 draws  
o4-mini (low) | 73.3 | 9 wins, 7 losses, 26 draws | 11 wins, 0 losses, 31 draws

W6: **(incorporated in the answer above)** Besides we have run multiple Dragon vs. Dragon (as well as vs. Random and vs. Stockfish) simulations, the logs can be found here: [https://huggingface.co/datasets/maxim-saplin/llm\_chess/tree/main/dragon](https://huggingface.co/datasets/maxim-saplin/llm_chess/tree/main/dragon)  
Take for example a simulation of 1000 games between Dragon Level 1 vs Dragon Level 2 \- we can see that game metrics, such as player material count and game duration variate significantly (standard deviation is 10-40% of the mean) which suggest the game engines are not deterministic (as otherwise we would get 0 std. Dev. \- all game beginnings were exactly the same) and demonstrate a good deal of variance.

— 

**TODO:** Add license discussion in readme, remove komodo weights instead replacing with information on how to download. Also include more information on 1\) how to set up local models and 2\) how to calculate the Elo score.

**Maxim:** thanks for noticing. We’ve removed Komodo binaries from the Git repo and updated the instructions directing to Komodo hosted download link.

**Maxim:** the instruction now has extra on running local models via llama.cpp (e.g. through LMStudio/ollama) \- in the models must be converted to GGUF format

**Maxim:** extended README with Elo calc, uploaded input data directly to GH repo for simplicity \- just run the script and get the results printed

Evaluating a custom local model is easy, as long as it is available as OpenAI API endpoint on localhost \- .env.sample file has an example config. We tested many local models using LMStudio. Any model in GGUF format can be easily deployed locally via popular llama.cpp wrapper with OpenAI inference features, e.g. LMStudio, ollama. 

# Rebuttals \- USES

#### **Official Review of Submission1125 by Reviewer USES**

Official Reviewby Reviewer USES14 Jul 2025, 22:26 (modified: 24 Jul 2025, 08:15)Program Chairs, Senior Area Chairs, Area Chairs, Reviewers Submitted, Authors, Reviewer USES[Revisions](https://openreview.net/revisions?id=CRr63p59yG)  
**Summary:**  
This paper introduces LLM CHESS, a benchmarking framework designed to assess the chess performance of LLMs. The authors evaluate over 50 LLMs, examining various performance metrics such as win/loss rates, move legality, move quality, hallucinations, and game duration. A subset of these models is also tested against chess engines at different skill levels to derive Elo ratings.

Results indicate that only reasoning-enhanced LLMs reliably outperform random opponents, with even top models significantly underperforming when compared to chess engines, highlighting their limited generalization in chess. The authors also explore test-time scaling methods, such as increased reasoning effort and parallel model aggregation, demonstrating substantial improvements.

**Strengths Contributions:**

* The paper introduces a interactive chess benchmark that evaluates reasoning and instruction-following abilities of LLMs through the game of chess, effectively bridging traditional AI evaluation with modern LLMs.  
* The authors utilize an extensive suite of metrics at multiple granularities (per-model, per-game, per-ply), which include traditional win-loss statistics, move legality, hallucination tracking, and quantitative reasoning indicators (blunders, inaccuracies, move optimality). This depth allows detailed insights into model performance.  
* The paper conducts well-structured ablation studies exploring critical elements of the evaluation framework (e.g., agentic actions, board representation, and additional contextual information).

**Limitations Weaknesses:**

* While the authors emphasize generalization, chess reasoning is domain-specific. It’s unclear how performance on LLM CHESS translates into reasoning capabilities on broader, less structured tasks or domains, potentially limiting the utility of the findings outside chess evaluation.  
* The primary evaluation (initially) pits LLMs against a random chess player, which, from a practical standpoint, is an extremely weak baseline. This makes it less insightful in demonstrating meaningful reasoning or strategic depth beyond basic instruction-following.  
* **Many losses in non-reasoning models result simply from instruction-following failures rather than strategic mistakes**. This conflates two fundamentally different capabilities (instruction-following vs. strategic reasoning), obscuring the actual reasoning power of the models tested.  
* ~~The chess setup is highly simplified: models do not have access to prior moves, and the board state is explicitly provided at each turn without historical context. This artificially reduces complexity and is far removed from genuine chess reasoning or human-like gameplay, limiting the real-world applicability of findings.~~  
* ~~Experiments predominantly fix hyperparameters (temperature \= 0.3, Top-P \= 1.0) without sufficient exploration. It remains unclear how sensitive the results are to changes in these parameters, raising questions about robustness and stability of the results presented.~~

**Ethical Considerations:** No, there are no or only very minor ethics concerns  
**Dataset Code Accessibility:** Yes  
**Dataset Code Comments:**  
The code looks good to me.

**Rating:** 3: Borderline reject: Technically solid paper where reasons to reject, e.g., limited evaluation, outweigh reasons to accept, e.g., good evaluation. Please use sparingly.  
**Confidence:** 3: You are fairly confident in your assessment. It is possible that you did not understand some parts of the submission or that you are unfamiliar with some pieces of related work. Math/other details were not carefully checked.  
**Code Of Conduct Acknowledgement:** Yes  
**Responsible Reviewing Acknowledgement:** Yes

## Takeaways

The main concern is about instruction-following being conflated with reasoning and why a random player is necessary. We should be able to run experiments on the make\_move-only setting that let us make better statements about instruction-following and thus disentangle them.

Secondary concerns are about the simplified state and experimental settings, which are concerns shared in basically all the reviews.

## Response

Thank you for your valuable insights and feedback. We address your concerns below:

\---

\#\#\# \`W1: Utility of findings is potentially limited outside chess evaluation\`

While LLM Chess focuses on only the chess domain, we still believe our benchmark still says something about generalization. Namely, since current reasoning models gain their capabilities through training with almost exclusively math or code datasets, chess and other games are out of distribution. So, as of now, we believe we can view reasoning performance in chess through the lens of generalization.

As far as generalizing to other aspects, chess has been a common goal for AI systems throughout history to master. Though we cannot know if our results will explicitly generalize to other games, chess is frequently used as a measuring stick and a milestone for a sufficiently advanced AI system, so it may be of more use than other evaluation targets with otherwise similar properties.

Additionally, while current reasoning models reach expert levels in math and coding, we find this expert-level reasoning does not transfer to our chess benchmark; in fact, the LLMs currently perform at very low levels, only reaching a max of \~750 Elo, which corresponds to a beginner. We have a short discussion regarding the difference in performance on benchmarks versus LLM Chess in Appendix B.4, which we will further expand in the final version with these claims.

\---

\#\#\# \`W2: Playing against a random chess player is an extremely weak baseline\`

We chose to start with a random player for simplicity and as a heuristic for whether it is worth it to test the models against a chess engine. For context, we run 1000 games of random against each of Dragon skills 1-4 and find that the reported Elo for random is \-122.3 with a 95% confidence interval of 23.0, confirming that it is much weaker than any of the available Dragon skills. We agree it is a surprising result that many models fail against such a weak random player. However, we still view the results as insightful by looking at how the games ended.

Indeed, in Table 1, against a random player over all non-reasoning models that 71.9% of games end in an instruction-following error, whereas 24.6% end in a draw on average. This is compared to 24.4% and 30.2% for reasoning models on average, for instruction-following error and draws respectively. These results show that playing against a random player can be very revealing for instruction-following failures.

Moreover, we interestingly find that around a quarter of games end in a draw for both classes of models. As the rate of checkmates by the random player is quite small (up to low single digits on average across reasoning and non-reasoning models), we argue that the reasoning a model needs to do is defined mostly by its ability to end the game within the 100 move limit. Thus, we can gain insights about reasoning by looking at the percentage of draws against a random player.

In either case, while a random player is a weak baseline, it still gives us a sense of if the model can actually play a game in our setup (instruction-following), and as a secondary focus, a controlled preview of its reasoning ability measured by its ability to close out the game. We believe this is enough of a signal to help us identify powerful models that we can use when we proceed to the Elo stages, which is our main focus.

\---

\#\#\# \`W3: Instruction-following and reasoning are conflated, especially on non-reasoning models\`

While we understand the concern with instruction-following and reasoning being conflated, we argue that the construction of our benchmark draws them sufficiently apart. Essentially, our two stage pipeline can be seen as primarily evaluating instruction-following in the first stage (by making the necessary reasoning as simple as possible, i.e., just the ability to close out a game against random moves as described in W2). Then, in the second stage, we focus on scaling the difficulty of reasoning, as we already know that instruction-following will not be an issue for the models that proceeded. Looking at Table 1, we see the most powerful models o3 (medium) and o3 (low) make 0% instruction-following errors against a random player. Hence these models have essentially “passed” the instruction-following test of the benchmark and now are evaluated on more difficult opponents, shifting the focus more to reasoning, which is our main goal.

We do note that this separation is not perfect. Even though the most powerful models do not make instruction-following errors, it is still possible for the difficulty of the instruction-following setting to affect reasoning ability. To see performance when instruction-following challenges are removed, we define the \`Only make\_move\` setting in our ablations, where the board state and legal moves are always provided within the prompt and the only action offered to the LLM is \`make\_move\`. In Table 6, we found that this setting boosts Grok 3 Mini (low) performance by 10.0 points, while increasing o4-mini (low) by 23.4 points against a random player. This suggests that our default setting with agentic calls increases the difficulty of reasoning, even though the reasoning models don’t make instruction-following errors. We will include further experiments with results versus Dragon in our final version to better define this separation and understand the overlap between capabilities.

Regarding weak and non-reasoning models specifically, we agree that such models may not get to show their true reasoning abilities in LLM Chess due to instruction-following errors holding them back. However, this is by design: LLM Chess requires sufficient instruction-following ability before scaling up reasoning.

However, we agree it still is important to test the capabilities of the weaker models. To do this, we run experiments on gpt-4o-2024-11-20 and gpt-4o-mini in the \`Only make\_move\` setting with 30 games. We find gpt-4o has a win/loss of 41.7% as compared to the baseline of 48.3% and gpt-4o-mini has a win/loss of 36.7% as compared to the baseline of 30.0%. In both cases, performance is generally similar (we expect the decrease is due to having a small sample size): there are no large jumps in capabilities in the simpler \`Only make\_move\` setting. This suggests that for non-reasoning models, instruction-following isn’t having a huge impact on reasoning performance. Interestingly, this is different than for reasoning models, who generally perform better in the simpler setting. We will further expand these experiments in the final version.

\---

\#\#\# \`W4: Chess setup is highly simplified\`  
We acknowledge that our benchmark includes settings that deviate from what you would find in the real-world. However, our goal was to use chess as a testbed to evaluate different aspects of LLMs including instruction-following and measuring the abilities of reasoning models beyond simple move completion settings. The main deviation was our introduction of tools, i.e., the ability to see the current board or legal moves with a tool call. While it may seem unorthodox, the results show that introducing such an agentic approach is useful in measuring instruction-following, a central goal of the benchmark: of the 44 models we tested vs a random opponent, we see instruction-following errors are responsible for 71.9% of all games ending for non-reasoning models and 24.4% for reasoning models, on average. Even more powerful models we might not expect to have such errors, e.g., Deepseek-R1 or o3-mini (low), show non-negligible problems with instruction following.

The main design choices we made beyond the agentic setting was supplying the current board and legal moves but not providing the previous moves. We justify our other choices below, which we will add to the limitations section of our paper:

\*\*Board State\*\*  We assume that the model is able to see the full board at any time, differing from some models that see only the previous moves or a pgn description of the game. We chose this to be more similar to what a human player or chess engine would see.  
   
\*\*Legal Moves\*\*  We decided to provide legal moves to simplify the benchmark, as current capabilities of models are not yet enough to play consistently without providing the legal moves. See Table 6 in Appendix B, where not including legal moves causes a decrease in win/loss of \~30% for grok-3-mini-low and \~10% for o4-mini (low) compared to the baseline (note for legal moves and its comparison we use the FEN setting as without legal moves, we cannot know castling rights or en passant). Essentially, including the legal moves was a practical concern: it allows us to have more granularity between models by boosting their performance and preventing clustering at low performance due to move failures.

\*\*Previous Moves\*\* We chose not to include previous moves to increase similarity with existing AI approaches for playing chess. Chess engines like Stockfish can evaluate the best move given a board state alone without any move history. If LLMs are to reach the level of other AI systems in chess, we believe it is helpful to see them perform under these same constraints. So, we decided not including previous moves would result in a more challenging and ideal goal for LLMs. This decision not to include previous moves was made during the initial trials of the benchmark during its creation, while experimenting with different prompts across a subset of models. During these experiments, including the history bloated the prompt and made some of the models struggle more with instruction-following, so we also chose this setting as a practical concern. Moreover, in our paper, we analyzed performance of including previous moves in our ablations in Table 6\. We found that while including previous moves in the prompt did improve performance, the change was varied and altogether not drastic, suggesting that if anything, the previous moves can help reduce complexity and blunders, not increase them.

\---

\#\#\# \`W5: Hyperparameters are fixed without sufficient exploration\`

For simplicity, we chose default hyperparameters to use throughout the experiments. Early on, we tested a higher temperature with an initial set of 10 models, which resulted in too many game loop interruptions. The temperature of 0.3 was determined empirically as being not too high as to cause interruptions, but not too low as to induce too much determinism. As the benchmark has been running for a long time, once we chose the hyperparameters we did not change them for future tests. While we acknowledge our choice of hyperparameters may have a non-negligible effect on performance, we believe they are reasonable enough, and for continuity and consistency we persisted with the initial test design.

\---

### \#\#\# Old stuff

 To test this, we run experiments with grok-3-mini-high on the \`Only make\_move\` setting versus skills 1-5 of Komodo Dragon. We calculate its Elo as **todo**

- Dont do bc suspected difference of dragon on our cluster vs maxims computer

 As the reviewer points out, losses in non-reasoning models often result from instruction-following errors, so it is difficult to know in isolation how good they are at reasoning.  
	\- \[x\] GPT-4o (\`gpt-4o-2024-11-20\` bc that was the best one) vs. random: \`\_logs/ablations/llm\_vs\_random\_only\_make\_move/gpt-4o-2024-11-20/RANDOM\_PLAYER\_vs\_LLM\_BLACK/2025-07-29-14-34-06/\`  
		\- 0 wins, 5 losses, 25 draws. Note 1 loss due to instruction-following errors.  
			\- This is a 41.67% win/loss.  
	\- \[x\] GPT-4o-mini (\`gpt-4o-mini-2024-07-18\` bc that had instr following errors) vs. random: \`\_logs/ablations/llm\_vs\_random\_only\_make\_move/gpt-4o-mini-2024-07-18/RANDOM\_PLAYER\_vs\_LLM\_BLACK/2025-07-29-14-52-01\`  
		\- 0 wins, 8 losses, 22 draws. Note 5 losses due to instruction-following errors.  
			\- This is a 36.67% win/loss.  
	\- \[x\]  \`o3-mini\` vs random: \`\_logs/ablations/llm\_vs\_random\_only\_make\_move/o3-mini/RANDOM\_PLAYER\_vs\_LLM\_BLACK/2025-07-29-14-46-51\`  
		\- 11 wins, 0 losses, 19 draws. Note no instruction-following errors.  
			\- This is a 68.33 win/loss.

**TODO:** Run our Elo leaderboard on top 2 models in the reasoning make\_move-only setting as discussed before. Honestly we may consider running it on gpt-4o and Qwen-2.5-Max as well, as those models have 0% instruction-following errors. It makes more sense to me to see where these non-reasoning models are versus certain Elo opponents as then we can claim that a random player is either a good proxy for reasoning ability, given we have strong enough instruction following, or not.

Interestingly, we noticed that reasoning models, such as o4-mini and Grok-3-mini tend to skip the get\_legal\_moves step at higher reasoning levels OR the legacy GPT-4 almost never requested the board state making the move after getting the list of legal moves.

(i.e., Grok 3 Mini improved its Win/Loss from 61.7% to 75.0% and o4-mini improved from 73.3% to 76.7%)   
or roughly on par with affecting performance (e.g. single step make\_move experiment bumped o4-mini win/loss to 96.7%). Overall, we find models demonstrate far more sensitivity to prompt formatting and game workflow rather than omission of some of the information.

# Rebuttals \-- 9zRm (addressed)

#### **Official Review of Submission1125 by Reviewer 9zRm**

Official Reviewby Reviewer 9zRm02 Jul 2025, 09:43 (modified: 24 Jul 2025, 08:15)Program Chairs, Senior Area Chairs, Area Chairs, Reviewers Submitted, Authors, Reviewer 9zRm[Revisions](https://openreview.net/revisions?id=DiMGWZ9Hcp)  
**Summary:**  
This paper introduces LLM CHESS, a benchmark that uses an agentic framework to evaluate the reasoning and instruction-following skills of LLMs in chess. By requiring models to interact with the game via commands, the study assesses over 50 LLMs against random and engine opponents to derive Elo ratings. The core finding is that most LLMs struggle, with failures often stemming from an inability to follow instructions rather than poor strategic play. The work demonstrates that chess remains a significant challenge for the agentic capabilities of current LLMs.

**Strengths Contributions:**  
The study assesses over 50 models using a sound two-stage methodology (random opponent then a rated engine), providing a comprehensive and valuable snapshot of current LLM capabilities.

**Limitations Weaknesses:**

1. ~~models are tested without any game history, treating each move as a separate problem, which makes it impossible to evaluate long-term planning, which is a core part of chess intelligence. This limitation should be made more explicit.~~  
2. ~~some results are counter-intuitive but not explained. For example, in Figure 4a, the 5x Mixture-of-Agents setup performs worse than the 3x version, which goes against expectations. The paper doesn’t offer any hypothesis or discussion about why this might happen, which leaves an important gap in the analysis.~~  
3. ~~minor typos: line 191, 'Figure 4' should be 'Figure3'; line 65, the paper states that "o3 (low)" achieved a "753 Elo". However, in Figure 3 on page 7, the same model is listed with an Elo of 758.42±65.20.~~

**Ethical Considerations:** No, there are no or only very minor ethics concerns  
**Dataset Code Accessibility:** Yes  
**Dataset Code Comments:**  
the data/framework/leaderboard can be found in corresponding links.

**Rating:** 3: Borderline reject: Technically solid paper where reasons to reject, e.g., limited evaluation, outweigh reasons to accept, e.g., good evaluation. Please use sparingly.  
**Confidence:** 3: You are fairly confident in your assessment. It is possible that you did not understand some parts of the submission or that you are unfamiliar with some pieces of related work. Math/other details were not carefully checked.  
**Code Of Conduct Acknowledgement:** Yes  
**Responsible Reviewing Acknowledgement:** Yes

## Takeaways

Again, most of the concern is the unusual evaluation format.

## Response

Thank you for your valuable feedback; we address your comments below:  
\---

**\#\#\# \`W1: Models are tested without any game history\`**  
We chose not to include previous moves to increase similarity with existing AI approaches for playing chess. Chess engines like Stockfish can evaluate the best move given a board state alone without any move history. If LLMs are to reach the level of other AI systems in chess, we believe it is helpful to see them perform under these same constraints. So, we decided not including previous moves would result in a more challenging and ideal goal for LLMs. Even though we don’t include previous moves, we disagree that this prevents our benchmark from evaluating long-term planning. Like how chess engines need to investigate many different branches into the future, LLMs also need to think about the prospects of future moves; in fact, this is inherent to any move made in chess. Including previous moves may affect the strategies LLMs choose, but they still need to reason about long-term decisions given the complexity and branching factor of chess.

From a more practical stance, the decision not to include previous moves was made during the initial trials of the benchmark during its creation, while experimenting with different prompts across a subset of models. During these experiments, including the history bloated the prompt and made some of the models struggle more with instruction-following, so we also chose this setting as a practical concern. Moreover, in our paper, we analyzed performance of including previous moves in our ablations in Table 6\. We found that while including previous moves in the prompt did improve performance, the change was varied and altogether not drastic, suggesting that if anything, the previous moves can help reduce complexity and blunders, not increase them.

\---

**\#\#\# \`W2: Some results are counter-intuitive but not explained\`**  
We observe an increase in win rate from single agent (i.e., o4-mini low or high) to 3x MoA, but a decrease from 3x to 5x MoA. Though one may expect returns to diminish, this decrease suggests that too many proposed moves can become redundant or even confusing. Relatedly, we did find that pairing a strong reasoning model (but a weaker instruction follower) such as Gemini 2.5 Pro or DeepSeek-R1 with a strong instruction following model (e.g., GPT 4.1 Mini) improved performance significantly by reducing instruction-following errors. For example, pairing Gemini 2.5 Pro with GPT 4.1 Mini improved its Win/Loss rate against the random player from 41.9% to 78.8%.

\---

**\#\#\# \`W3: Minor typos\`**

Thank you for pointing these out; we will fix them all in the final version of our paper.

\---

\#\#\# References

\[1\] Junlin Wang, Jue Wang, Ben Athiwaratkun, Ce Zhang, James Zou: Mixture-of-Agents Enhances Large Language Model Capabilities. ICLR 2025

# Rebuttals \-- SeKK (mostly addressed)

#### **Official Review of Submission1125 by Reviewer SeKK**

#### **Official Reviewby Reviewer SeKK24 Jun 2025, 13:37 (modified: 24 Jul 2025, 08:15)Program Chairs, Senior Area Chairs, Area Chairs, Reviewers Submitted, Authors, Reviewer SeKK[Revisions](https://openreview.net/revisions?id=5dSou3Mmzk)**

#### **Summary:**

#### **This paper introduces a benchmark in which LLM agents play chess games to evaluate the instruction-following capability of LLMs. In this benchmark, the to-be-evaluated LLM plays chess with either a random player or a chess engine.**

#### **Strengths Contributions:**

#### **This paper provides an interesting setting and conducts detailed analysis on the results.**

#### **Limitations Weaknesses:**

#### **~~\[1\] The exact meaning of "instruction following" under the context of this experiment is missing. In line 101-102, it mentions "without having game-ending issues from instruction-following issues or choosing invalid moves", but no further explanation.~~**

#### **\[2\] Insufficient number of repetitions and missing error bar: While the authors take efforts in testing many different LLM models to include in Figure 2, for other results with less LLM choices (such as Table 1), the authors are encourages to perform more repetitions and apply an error bar. 30 repetitions is enough for a single setting, but when comparing different LLM models, it is not sufficient.**

#### **~~\[3\] The LLMs are not given the play history. While the authors explain on this setting, it would be better if an additional ablation study can be provided for this to examine the impact of the play history.~~**

#### **~~\[4\] Writing: the writing of this paper can be revised:~~**

#### **~~\[4.1\] It is not clear what is the relationship between "Elo" and~~** 

#### **~~Ei(R)~~**

#### **~~.~~** 

#### **~~Ei(R)~~**

####  **~~is not used in tables or figures.~~**

#### **~~\[4.2\] There are informal wordings such as "you" used in the paper. Please revise them to more professional language.~~**

#### **Ethical Considerations: No, there are no or only very minor ethics concerns**

#### **Dataset Code Accessibility: Yes**

#### **Rating: 3: Borderline reject: Technically solid paper where reasons to reject, e.g., limited evaluation, outweigh reasons to accept, e.g., good evaluation. Please use sparingly.**

#### **Confidence: 3: You are fairly confident in your assessment. It is possible that you did not understand some parts of the submission or that you are unfamiliar with some pieces of related work. Math/other details were not carefully checked.**

#### **Code Of Conduct Acknowledgement: Yes**

#### **Responsible Reviewing Acknowledgement: Yes**

#### 

## Takeaways

Only thing we really need to address is the lack of experiments vs. random.  
Other things we addressed but was not clear enough to them.

## Response

Thank you for your valuable feedback. Our clarifications and comments are below:  
\---

\#\#\# \`W1: Instruction-following in this context is not clearly defined\`

We defined losses resulting from instruction-based errors in lines 122-124 as reaching the maximum turns in a conversation or maximum number of attempts in a turn without making a valid action. This includes hallucinating different actions beyond \`get\_current\_board\`, \`get\_legal\_moves\`, and \`make\_move\`, or hallucinating an invalid chess move. Note that because we offer the ability to provide legal moves, we view an invalid chess move as an instruction-following error rather than a reasoning error because the model has the opportunity to see all moves that would work. 

We will be more explicit in tying the instruction-based error section directly to what we call instruction-following errors throughout the paper, and will be sure to edit this section in the final version.

\---

\#\#\# \`W2: Insufficient number of repetitions and missing error bar\`

While we include confidence intervals for our Elo calculations, we acknowledge that the 30 initial games versus a random opponent leads to wide confidence intervals and the inability to have more precise comparisons of performance between our models. However, in our view, the LLM vs. random stage is used more as a sanity check and heuristic than a focused benchmark. Our main focus lies in the LLMs vs. chess engine setting, as it is much more scalable and can always present challenges, regardless of which model we use.

Ideally, we can run all models against the same chess engine skills with a high number of experiments. But since runs are expensive and models vary widely in their performance, we instead find a heuristic to help us choose which models to run. E.g., we do not want to run a model that cannot regularly make valid moves in our normal chess engine setup, as those experiments will likely all result in losses for the LLMs. Indeed, in our LLM vs. random experiments we can essentially ‘weed-out’ models like Qwen2.5-72B-Instruct and DeepSeek-V3 that have almost a 0% win/loss, so would not fare well against a chess engine. We define an informal heuristic as whether the LLM can perform equal to or above 50% win/loss versus a random player in 30 games. Our ideal goal is to select only very good models, maybe ones that exceed 75% or even 85-90% vs a random player. However, choosing our cutoff to be 75% or higher would likely have us skip many reasonably strong models that didn’t perform as well due to the small sample size. So, we choose a cutoff of 50%, with the idea that we would rather keep models that are weaker than they appear than throw away potentially strong models. For our main chess engine experiments, we select the top models among those that passed this heuristic (and in the future, will formalize this and expand our leaderboard to run against all models that passed this heuristic).

We will rephrase the LLM vs random section in the final version to be more clear that this is more of a sanity-check/heuristic, and that our main focus lies on the LLM vs chess engine leaderboard.

\---

\#\#\# \`W3: LLMs are not given the play history\`  
We ran an ablation using previous moves against a random opponent in Table 6\. We find that Grok 3 Mini (low) performs 13.3 points better by including previous moves, but o4-mini (low) performs only 3.4 points better. 

We also perform another ablation by changing our agentic setting, removing all actions but make\_move and instead always placing the board state and legal moves directly in the prompt. We do this both with and without supplying the previous moves. We find that Grok 3 Mini (low) and o4-mini (low) score 66.7 and 95.0 with previous moves versus 71.7 and 96.7 without previous moves in the only make\_move setting. This means that in an ideal scenario where the model already has all the information the tools would give it, there is little difference in having previous moves or not.

So, while there is utility to having previous moves, it does not universally provide large performance boosts across all models according to our ablations.

\---

\#\#\# \`W4: Writing errors\`

Thanks for pointing out the specific writing errors – we will clean up the Elo calculation notation and any informal wordings we find in the final version of our paper.

\---