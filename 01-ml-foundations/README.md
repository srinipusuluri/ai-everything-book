# 🧮 Module 01 — Machine Learning Foundations

> **Where you are:** Stop 1 of 16 on the end-to-end AI track.
> **Time:** ~20–25 hours · **Prereq:** Python, high-school algebra, willingness to meet calculus again.

Everything later in this track — transformers, agents, RAG, evals — is machine learning wearing a bigger coat.
If you can explain *bias/variance*, *gradient descent*, and *why your validation split lied to you*, the rest of
the track reads like engineering. If you can't, it reads like magic.

---

## Learning objectives

By the end of this module you can:

1. Frame a business problem as a supervised, unsupervised, or reinforcement learning task — and say when **not** to use ML.
2. Derive and implement linear & logistic regression with gradient descent from scratch (NumPy only).
3. Explain the bias–variance decomposition and diagnose under/overfitting from learning curves.
4. Build an honest evaluation setup: train/val/test, cross-validation, leakage hunting, and the right metric for the cost of being wrong.
5. Use tree ensembles (Random Forest, gradient boosting) and explain why they still beat deep learning on tabular data.
6. Read a model card / experiment report critically.

## Suggested path

| # | Do this | File | Time |
|---|---------|------|------|
| 1 | Read the core concepts | [notes/01-core-concepts.md](notes/01-core-concepts.md) | 3h |
| 2 | Work the math of learning | [notes/02-optimization-and-generalization.md](notes/02-optimization-and-generalization.md) | 3h |
| 3 | Run the from-scratch trainer | [code/linear_models_from_scratch.py](code/linear_models_from_scratch.py) | 2h |
| 4 | Run the honest-evaluation lab | [code/evaluation_playbook.py](code/evaluation_playbook.py) | 2h |
| 5 | Present it back | [slides/](slides/) (`ml-foundations.pptx`) | 1h |
| 6 | Do the exercises | [lab/EXERCISES.md](lab/EXERCISES.md) | 6h |
| 7 | Read 2 papers | [papers/PAPERS.md](papers/PAPERS.md) | 4h |

## The 12 terms you must own

`feature` · `label` · `loss function` · `gradient descent` · `learning rate` · `overfitting` ·
`regularization` · `bias–variance` · `cross-validation` · `data leakage` · `class imbalance` · `ensemble`

## Exit check ✅

You can hand a colleague a notebook that loads a tabular dataset, produces a baseline, a tuned model,
a leakage-free CV score, a calibration curve, and one paragraph on when the model should *not* be trusted.
