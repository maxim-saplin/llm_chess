Tried running gpt-oss-20b using OpenAI endpoint provided by LM Stidio and Ollama (logs included, 2025.08.12):
- LM Studio server has broken API server failingh to properly isolate Harmony special tokens spoling the contents of the response: https://github.com/lmstudio-ai/lmstudio-bug-tracker/issues/851 
- Ollama server seemed better yet the model failed to adhere to the protocol issuing tool calls and failing to recover after bot asked to replond with text.

In both cases cases the model failed to stay in ther game long enough, breaking the gamer loop after a few moves.