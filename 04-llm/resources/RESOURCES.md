# 🔗 Resources — Large Language Models

## Courses & lectures (free)
| Resource | Why | Link |
|---|---|---|
| **Karpathy — Neural Networks: Zero to Hero** | Build GPT from scratch; the "Let's build GPT" and "Tokenizers" lectures are the core of this module | https://karpathy.ai/zero-to-hero.html |
| **Karpathy — Intro to Large Language Models** | 1-hour overview of the pretrain -> finetune pipeline | https://karpathy.ai/ |
| **Stanford CS336 — Language Modeling from Scratch** | The rigorous version: data, systems, scaling, alignment | https://stanford-cs336.github.io/ |
| **Hugging Face LLM Course** | Transformers, tokenizers, fine-tuning, with runnable notebooks | https://huggingface.co/learn/llm-course |
| **Hugging Face RLHF book (blog chapters)** | The clearest free RLHF/DPO walkthrough | https://huggingface.co/blog/rlhf |
| **Jay Alammar — The Illustrated Transformer** | The diagrams everyone borrows | https://jalammar.github.io/illustrated-transformer/ |

## Repositories worth cloning
| Repo | What's inside |
|---|---|
| https://github.com/karpathy/nanoGPT | A readable GPT training pipeline in ~300 lines |
| https://github.com/karpathy/llm.c | The same idea in pure C/CUDA, for seeing the metal |
| https://github.com/vllm-project/vllm | The serving engine the industry converged on; read the PagedAttention docs |
| https://github.com/ggerganov/llama.cpp | Quantized local inference; the GGUF/q4 formats in the notes live here |
| https://github.com/huggingface/trl | Post-training reference implementations: SFT, DPO, RLHF |
| https://github.com/huggingface/peft | LoRA/QLoRA/adapters as an API |
| https://github.com/EleutherAI/lm-evaluation-harness | The open eval harness; pairs with Module 15 |
| https://github.com/Lightning-AI/litgpt | Pretraining/fine-tuning recipes with reproducible configs |

## Where to watch the landscape (not read, watch)
| Source | What it gives you |
|---|---|
| https://huggingface.co/open-llm-leaderboard | Open-model quality comparison; read the methodology caveats |
| https://artificialanalysis.ai/ | Price/latency/quality curves across providers — the Module 11 selection data |
| https://github.com/rasbt/LLMs-from-scratch | Raschka's book repo; the patient from-scratch build |

## Cheat sheets
- OpenAI API reference — sampling parameters and their real semantics: https://platform.openai.com/docs/api-reference/chat
- Hugging Face chat templating (`apply_chat_template`): https://huggingface.co/docs/transformers/main/en/chat_templating
- vLLM docs (quantization, batching, speculative decoding): https://docs.vllm.ai/
- Also see [../../\_shared/cheatsheets/](../../_shared/cheatsheets/)

## Communities
- r/LocalLLaMA — the self-hosting crowd; best place to learn what actually fits on which GPU
- Hugging Face forums — https://discuss.huggingface.co/
- EleutherAI Discord — the open-research community behind GPT-NeoX and the eval harness
