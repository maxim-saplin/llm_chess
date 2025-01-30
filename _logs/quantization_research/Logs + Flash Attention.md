All logs collected with LM Studio 0.3.6, runtime: CUDA llama.cpp (Windows) v1.7.1, RTX 4090 OC.

29.01.2025 logs (990 run for LLama and Gemma) obtained via LM Studio 0.3.8 and llama.cpp 1.9.2

## Flash Attention and Performance

LLama 3.1 8B, context length 8192, Evaluation Batch Size 512:
- meta-llama-3.1-8b-instruct@q4_k_m
    - FA: 7.1GB VRAM
        - 132.03 tok/sec, 471 tokens, 0.29s to first token
        - 121.74 tok/sec, 474 tokens, 0.28s to first token
        - 121.30 tok/sec, 660 tokens, 0.20s to first token
        - 119.34 tok/sec, 506 tokens, 0.26s to first token
    - No FA: 7.3GB VRAM
        - 130.48 tok/sec, 386 tokens, 0.25s to first token
        - 111.48 tok/sec, 315 tokens, 0.27s to first token
        - 115.61 tok/sec, 480 tokens, 0.27s to first token
        - 118.37 tok/sec, 539 tokens, 0.25s to first token
- meta-llama-3.1-8b-instruct@q8_0
    - FA: 10.2GB VRAM
        - 92.52 tok/sec, 618 tokens, 0.31s to first token
        - 85.85 tok/sec, 507 tokens, 0.26s to first token
        - 87.74 tok/sec, 708 tokens, 0.26s to first token
        - 83.81 tok/sec, 367 tokens, 0.33s to first token
    - No FA: 10.5GB VRAM
        - 92.18 tok/sec, 453 tokens, 0.33s to first token
        - 85.71 tok/sec, 542 tokens, 0.33s to first token
        - 82.65 tok/sec, 351 tokens, 0.34s to first token
        - 88.28 tok/sec, 544 tokens, 0.20s to first token
- sanctumai/meta-llama-3.1-8b-instruct@f16
    - FA: 16.7GB VRAM
        - 58.82 tok/sec, 434 tokens, 0.23s to first token
        - 55.06 tok/sec, 378 tokens, 0.33s to first token
        - 55.34 tok/sec, 338 tokens, 0.23s to first token
        - 54.25 tok/sec, 301 tokens, 0.34s to first token
    - No FA: 17.0GB VRAM
        - 58.18 tok/sec, 343 tokens, 0.23s to first token
        - 51.15 tok/sec, 168 tokens, 0.28s to first token
        - 54.62 tok/sec, 423 tokens, 0.38s to first token
        - 55.02 tok/sec, 292 tokens, 0.26s to first token

Gemma 2 9B, context length 8192, Evaluation Batch Size 512:
- gemma-2-9b-it@q4_k_m
    - FA: 10.0GB VRAM
        - 94.05 tok/sec, 334 tokens, 0.31s to first token
        - 80.46 tok/sec, 262 tokens, 0.27s to first token
        - 84.15 tok/sec, 276 tokens, 0.19s to first token
        - 82.06 tok/sec, 311 tokens, 0.23s to first token
    - No FA: 10.0GB VRAM
        - 93.88 tok/sec, 243 tokens, 0.31s to first token
        - 81.64 tok/sec, 282 tokens, 0.23s to first token
        - 80.51 tok/sec, 250 tokens, 0.32s to first token
        - 87.48 tok/sec, 384 tokens, 0.18s to first token
- gemma-2-9b-it@q8_0
    - FA: 13.8GB
        - 68.75 tok/sec, 247 tokens, 0.27s to first token
        - 62.07 tok/sec, 271 tokens, 0.27s to first token
        - 64.31 tok/sec, 370 tokens, 0.33s to first token
        - 64.39 tok/sec, 268 tokens, 0.19s to first token
    - No FA: 13.8GB
        - 69.11 tok/sec, 279 tokens, 0.34s to first token
        - 62.05 tok/sec, 243 tokens, 0.24s to first token
        - 62.41 tok/sec, 275 tokens, 0.26s to first token
        - 64.36 tok/sec, 272 tokens, 0.19s to first token
