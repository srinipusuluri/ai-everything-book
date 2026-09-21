# 🔗 Resources — ML Foundations

## Courses (free)
| Course | Who it's for | Link |
|---|---|---|
| **Andrew Ng — Machine Learning Specialization** (Coursera, audit free) | The canonical first course | https://www.coursera.org/specializations/machine-learning-introduction |
| **fast.ai — Practical Deep Learning** (Lesson 1–3 cover tabular ML) | Top-down, code-first | https://course.fast.ai/ |
| **Google — Machine Learning Crash Course** | Fastest path to working vocabulary | https://developers.google.com/machine-learning/crash-course |
| **CS229 Stanford — Machine Learning** (notes + lectures) | The mathematical treatment | https://cs229.stanford.edu/ |
| **Kaggle Learn — Intro to ML / Intermediate ML** | 4 hours to a working model | https://www.kaggle.com/learn |
| **StatQuest (Josh Starmer)** | When an equation refuses to click | https://www.youtube.com/@statquest |
| **MIT 6.036 / 6.390 Intro to ML** | Rigorous, free courseware | https://openlearninglibrary.mit.edu/ |

## Repositories worth cloning
| Repo | What's inside |
|---|---|
| https://github.com/scikit-learn/scikit-learn | Read `sklearn/linear_model/_logistic.py` — production-grade versions of what you wrote |
| https://github.com/ageron/handson-ml3 | Notebooks for *Hands-On ML with Scikit-Learn, Keras & TensorFlow* (3rd ed.) |
| https://github.com/rasbt/machine-learning-book | Raschka's *Machine Learning with PyTorch and Scikit-Learn* |
| https://github.com/microsoft/ML-For-Beginners | 12-week structured curriculum from Microsoft |
| https://github.com/dmlc/xgboost | The library and its excellent docs/tutorials |
| https://github.com/eriklindernoren/ML-From-Scratch | Clean NumPy implementations of ~30 algorithms |
| https://github.com/probml/pyprobml | Code for Murphy's *Probabilistic Machine Learning* |
| https://github.com/shap/shap | Explainability you'll need in Module 12 |
| https://github.com/evidentlyai/evidently | Drift & data-quality monitoring — pairs with §11 of the deep dive |

Clone the starter set with: `bash ../_tools/clone_repos.sh 01-ml-foundations`

## Datasets to practise on
| Dataset | Why | Where |
|---|---|---|
| California Housing | clean regression, no leakage traps | `sklearn.datasets.fetch_california_housing()` |
| Adult / Census Income | categorical encoding + fairness discussion | `fetch_openml("adult", version=2)` |
| Titanic | the classic; great for feature engineering | https://www.kaggle.com/c/titanic |
| Credit Card Fraud | severe imbalance — use with §6 of the notes | https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud |
| UCI ML Repository | 600+ datasets | https://archive.ics.uci.edu/ |
| Hugging Face Datasets | 200k+ datasets, one-line loading | https://huggingface.co/datasets |

## Cheat sheets
- scikit-learn algorithm chooser: https://scikit-learn.org/stable/machine_learning_map.html
- scikit-learn model evaluation guide: https://scikit-learn.org/stable/modules/model_evaluation.html
- Also see [../../\_shared/cheatsheets/](../../_shared/cheatsheets/)

## Communities
- r/MachineLearning — https://www.reddit.com/r/MachineLearning/
- Papers with Code — https://paperswithcode.com/
- Hugging Face forums — https://discuss.huggingface.co/
