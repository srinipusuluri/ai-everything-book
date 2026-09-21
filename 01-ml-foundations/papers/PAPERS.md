# 📄 Papers & Primary Sources — ML Foundations

Run `bash ../_tools/fetch_papers.sh 01-ml-foundations` from the repo root to download the open-access PDFs
into this folder. Items without a direct PDF link are noted.

## Read these two first

| # | Paper | Why it matters | Link |
|---|-------|----------------|------|
| 1 | **A Few Useful Things to Know About Machine Learning** — Pedro Domingos (2012) | The single best 9-page summary of ML practice ever written. "More data beats a cleverer algorithm." Read it twice. | [PDF](https://homes.cs.washington.edu/~pedrod/papers/cacm12.pdf) |
| 2 | **Hidden Technical Debt in Machine Learning Systems** — Sculley et al., NeurIPS 2015 | Why the model is 5% of a real ML system. Introduces CACE: *Changing Anything Changes Everything*. Foundational for Module 10 and 16. | [PDF](https://proceedings.neurips.cc/paper_files/paper/2015/file/86df7dcfd896fcaf2674f757a2463eba-Paper.pdf) |

## Core theory & method

| Paper | Year | One-line takeaway | Link |
|---|---|---|---|
| Random Forests — Breiman | 2001 | Bagging + random feature subsets kills variance | [PDF](https://www.stat.berkeley.edu/~breiman/randomforest2001.pdf) |
| Greedy Function Approximation: A Gradient Boosting Machine — Friedman | 2001 | The original gradient boosting derivation | [PDF](https://jerryfriedman.su.domains/ftp/trebst.pdf) |
| XGBoost: A Scalable Tree Boosting System | 2016 | The engineering that made boosting the tabular default | [arXiv:1603.02754](https://arxiv.org/abs/1603.02754) |
| Statistical Modeling: The Two Cultures — Breiman | 2001 | Prediction vs. inference; the intellectual split that still shapes the field | [PDF](https://projecteuclid.org/journals/statistical-science/volume-16/issue-3/Statistical-Modeling--The-Two-Cultures-with-comments-and-a/10.1214/ss/1009213726.full) |
| Reconciling Modern Machine Learning and the Bias-Variance Trade-off — Belkin et al. | 2018 | Double descent; the textbook U-curve is incomplete | [arXiv:1812.11118](https://arxiv.org/abs/1812.11118) |
| Do we need hundreds of classifiers? — Fernández-Delgado et al. | 2014 | 179 classifiers, 121 datasets: random forests win | [PDF](https://jmlr.org/papers/volume15/delgado14a/delgado14a.pdf) |
| Why do tree-based models still outperform deep learning on tabular data? — Grinsztajn et al. | 2022 | Empirical answer, still cited in 2026 | [arXiv:2207.08815](https://arxiv.org/abs/2207.08815) |
| A Unified Approach to Interpreting Model Predictions (SHAP) — Lundberg & Lee | 2017 | The explainability tool you will be asked for in Module 12 | [arXiv:1705.07874](https://arxiv.org/abs/1705.07874) |
| Data Cascades in High-Stakes AI — Sambasivan et al. | 2021 | Data-quality failures compound downstream; the empirical case for "data first" | [PDF](https://storage.googleapis.com/gweb-research2023-media/pubtools/5906.pdf) |

## Free books (legally downloadable, full text)

| Book | Author | Link |
|---|---|---|
| **An Introduction to Statistical Learning** (ISLP, Python ed.) | James, Witten, Hastie, Tibshirani, Taylor | https://www.statlearning.com/ |
| **The Elements of Statistical Learning** | Hastie, Tibshirani, Friedman | https://hastie.su.domains/ElemStatLearn/ |
| **Pattern Recognition and Machine Learning** | Bishop (free since 2023) | https://www.microsoft.com/en-us/research/publication/pattern-recognition-machine-learning/ |
| **Probabilistic Machine Learning: An Introduction** | Kevin Murphy | https://probml.github.io/pml-book/book1.html |
| **Mathematics for Machine Learning** | Deisenroth, Faisal, Ong | https://mml-book.github.io/ |
| **Understanding Machine Learning: From Theory to Algorithms** | Shalev-Shwartz & Ben-David | https://www.cs.huji.ac.il/~shais/UnderstandingMachineLearning/ |

## How to read an ML paper (30 minutes, 3 passes)

1. **Pass 1 (5 min):** title, abstract, figures, conclusion. Ask: what problem, what's the claim?
2. **Pass 2 (15 min):** method section and experimental setup. Ask: what's the baseline, and is the comparison fair?
3. **Pass 3 (10 min):** limitations, ablations, and what you'd need to reproduce it. Ask: what would make this fail?

Keep a one-paragraph note per paper. In six months the note is worth more than the PDF.
