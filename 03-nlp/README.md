# 🗣️ Module 03 — Natural Language Processing

> **Where you are:** Stop 3 of 16. **Time:** ~25 hours · **Prereq:** [Module 02](../02-deep-learning/).

This is the hinge of the whole track. NLP is where representation learning met sequences and produced the
transformer — the architecture that every model in Modules 04–11 is built from. Do not skim this module to
get to LLMs faster. **This module *is* how LLMs work**; Module 04 is what happens when you scale it.

---

## Learning objectives

1. Explain the full text pipeline: raw text → tokens → embeddings → contextual representations → task output.
2. Implement **BPE tokenization** and explain why tokenization causes half of the weird LLM behaviours you'll see.
3. Derive scaled dot-product attention and implement multi-head self-attention from scratch.
4. Draw a transformer block from memory, including the position of every LayerNorm and residual.
5. Distinguish encoder-only (BERT), decoder-only (GPT), and encoder–decoder (T5) models and pick correctly.
6. Explain positional encoding — sinusoidal, learned, and **RoPE** — and why it determines context length.

## Suggested path

| # | Do this | File | Time |
|---|---|---|---|
| 1 | The pipeline and its history | [notes/01-text-to-vectors.md](notes/01-text-to-vectors.md) | 4h |
| 2 | The transformer, in full | [notes/02-transformers.md](notes/02-transformers.md) | 5h |
| 3 | Build a BPE tokenizer | [code/bpe_tokenizer.py](code/bpe_tokenizer.py) | 3h |
| 4 | Build attention | [code/attention_from_scratch.py](code/attention_from_scratch.py) | 4h |
| 5 | Slides | [slides/](slides/) | 1h |
| 6 | Lab | [lab/EXERCISES.md](lab/EXERCISES.md) | 6h |
| 7 | Papers (read #1 twice) | [papers/PAPERS.md](papers/PAPERS.md) | 5h |

## The 14 terms you must own

`token` · `BPE` · `vocabulary` · `embedding` · `positional encoding` · `RoPE` · `self-attention` ·
`query/key/value` · `multi-head` · `causal mask` · `KV cache` · `encoder-only` · `decoder-only` · `perplexity`

## Exit check ✅

You can implement a working single-head and multi-head attention, apply a causal mask correctly, explain
why `strawberry` has three r's but the model can't count them, and sketch a transformer block on a napkin.
