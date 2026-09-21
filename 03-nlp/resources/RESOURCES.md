# 🔗 Resources — NLP & Transformers

## Start here
| Resource | Why | Link |
|---|---|---|
| **Karpathy — Let's build GPT from scratch** | 2 hours, builds a working transformer live. The best single artifact in this module. | https://www.youtube.com/watch?v=kCc8FmEb1nY |
| **The Illustrated Transformer** — Jay Alammar | The diagrams everyone else copies | https://jalammar.github.io/illustrated-transformer/ |
| **The Annotated Transformer** — Harvard NLP | The paper with runnable code beside each paragraph | https://nlp.seas.harvard.edu/annotated-transformer/ |
| **Hugging Face NLP Course** (free) | Practical, current, hands-on | https://huggingface.co/learn/nlp-course |
| **Stanford CS224N — NLP with Deep Learning** | The university treatment; lectures on YouTube | https://web.stanford.edu/class/cs224n/ |
| **Speech and Language Processing** — Jurafsky & Martin (free draft) | The field's textbook, updated yearly | https://web.stanford.edu/~jurafsky/slp3/ |
| **3Blue1Brown — Transformers & attention** | Visual intuition for the matrix operations | https://www.3blue1brown.com/topics/neural-networks |

## Repositories
| Repo | What's inside |
|---|---|
| https://github.com/karpathy/nanoGPT | ~300 lines of readable GPT. Train one on your laptop. |
| https://github.com/karpathy/minGPT | The even smaller pedagogical version |
| https://github.com/karpathy/minbpe | BPE in a few hundred clean lines — compare with your own |
| https://github.com/huggingface/transformers | The library; read `modeling_llama.py` once, properly |
| https://github.com/huggingface/tokenizers | Fast Rust tokenizers with a Python API |
| https://github.com/openai/tiktoken | OpenAI's BPE tokenizer |
| https://github.com/google/sentencepiece | The tokenizer behind T5, Llama and many others |
| https://github.com/Dao-AILab/flash-attention | The reference implementation |
| https://github.com/UKPLab/sentence-transformers | Sentence embeddings — the on-ramp to Module 08 |
| https://github.com/explosion/spaCy | Industrial classical NLP: NER, parsing, pipelines |
| https://github.com/bentrevett/pytorch-seq2seq | Clear tutorials from RNN seq2seq up to transformers |

Clone the starter set with: `bash ../_tools/clone_repos.sh 03-nlp`

## Interactive / visual tools
- **Transformer Explainer** (interactive GPT-2 in your browser) — https://poloclub.github.io/transformer-explainer/
- **BertViz** (attention visualisation) — https://github.com/jessevig/bertviz
- **Tiktokenizer** (see tokens live) — https://tiktokenizer.vercel.app/
- **Hugging Face tokenizer playground** — https://huggingface.co/spaces/Xenova/the-tokenizer-playground
- **Transformer Circuits** (mechanistic interpretability) — https://transformer-circuits.pub/

## Datasets & leaderboards
- Hugging Face Datasets — https://huggingface.co/datasets
- GLUE / SuperGLUE — https://gluebenchmark.com/ · https://super.gluebenchmark.com/
- MTEB (embedding leaderboard — read this before choosing an embedding model) — https://huggingface.co/spaces/mteb/leaderboard
- Papers with Code — NLP — https://paperswithcode.com/area/natural-language-processing
