# v0.2.38 — Choose your local Qwen model

The installer offers independent **Lightweight (1.5B)** and **Higher quality (7B)**
Qwen 2.5 Coder choices. Select either or both. Each includes Ollama as a dependency.
Descriptions show approximate download sizes and the memory/speed tradeoff.

Only selected, missing or incomplete models are pulled. Existing setups retain
their lightweight default. OpenCode knows both models, and the workspace
`--model` option chooses which installed model to use. A 7B-only selection works
with the ordinary `deckctl ai-workspace open` command.

Owned-server cleanup and `OLLAMA_KEEP_ALIVE=0` are unchanged. Tests cover both
downloads, repeat-install skipping, partial readiness, default and explicit
launch choices, config migration and legacy defaults. Real model inference
performance has not been benchmarked.

See [AI workspace instructions](../modules/ai-workspace/README.md).

![Independent local model choices](screenshots/setup-qwen-models.png)
