# 🧠 Module 02 — Deep Learning

> **Where you are:** Stop 2 of 16. **Time:** ~25–30 hours · **Prereq:** [Module 01](../01-ml-foundations/).

One neuron is logistic regression. Stack them, learn the intermediate representations instead of
hand-crafting them, and you get deep learning. This module is where you stop *choosing* features and start
*learning* them — the shift that makes everything from Module 03 onward possible.

---

## Learning objectives

1. Implement a multi-layer perceptron and **backpropagation** from scratch, and verify it with a gradient check.
2. Explain vanishing/exploding gradients and the three inventions that fixed them (ReLU, normalization, residuals).
3. Build and train networks in PyTorch: `Dataset` → `DataLoader` → `Module` → training loop → checkpoint.
4. Choose between MLP / CNN / RNN by the *structure of the data*, not by fashion.
5. Diagnose a failing training run in under 15 minutes using a fixed checklist.
6. Apply transfer learning and fine-tuning — the workflow you'll reuse for LLMs in Module 04.

## Suggested path

| # | Do this | File | Time |
|---|---------|------|------|
| 1 | Core concepts | [notes/01-neural-networks.md](notes/01-neural-networks.md) | 4h |
| 2 | Training craft | [notes/02-training-deep-networks.md](notes/02-training-deep-networks.md) | 4h |
| 3 | Backprop, by hand | [code/backprop_from_scratch.py](code/backprop_from_scratch.py) | 3h |
| 4 | PyTorch in one file | [code/pytorch_training_loop.py](code/pytorch_training_loop.py) | 3h |
| 5 | Slides | [slides/](slides/) | 1h |
| 6 | Lab | [lab/EXERCISES.md](lab/EXERCISES.md) | 8h |
| 7 | Papers | [papers/PAPERS.md](papers/PAPERS.md) | 5h |

## The 12 terms you must own

`neuron` · `activation` · `backpropagation` · `computational graph` · `vanishing gradient` ·
`batch normalization` · `residual connection` · `dropout` · `embedding` · `convolution` ·
`transfer learning` · `mixed precision`

## Exit check ✅

You can train a network on a new dataset, hit a target metric, explain every line of your training loop,
and debug it when the loss goes to NaN — without copying a notebook.
