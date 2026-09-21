---
marp: true
theme: default
paginate: true
style: |
  section h1 { color: #4F46E5; }
  section { font-size: 24px; }
---

# Machine Learning Foundations

### The 20% of ML that explains 80% of modern AI

**Module 01** · AI End-to-End Learning Track

---

## Why this module exists

- Transformers, agents and RAG are ML wearing a bigger coat
- Three ideas carry the whole track: a loss, a gradient, a validation split
- If you skip this, later modules feel like magic instead of engineering
- Target: explain bias/variance and leakage to a colleague, unaided

<!-- speaker note: Set expectations: this module is the vocabulary for everything downstream. -->

---

## Classical programming vs. machine learning

- Classical: rules + data -> answers
- ML: data + answers -> rules (a model)
- A model is f_theta(x) -> y_hat plus a procedure to choose theta
- 'Training' = minimise a loss over data
- Don't use ML when the rule is known, labels are unobtainable, or errors are unacceptable

<!-- speaker note: The 'when not to use ML' list is the most useful slide for business stakeholders. -->

---

## The three-and-a-half paradigms

| Paradigm | You have | You learn | Example |
|---|---|---|---|
| Supervised | (x, y) pairs | mapping x -> y | fraud, churn, pricing |
| Unsupervised | x only | structure | clustering, anomalies |
| Reinforcement | env + reward | policy | robotics, RLHF |
| Self-supervised | x, labels invented | representations | BERT, GPT pretraining |


<!-- speaker note: Self-supervised is the half - and the reason LLMs scaled. Next-token prediction is supervised learning with free labels. -->

---

## Empirical risk minimisation

- J(theta) = (1/n) * sum L(f(x_i), y_i)  +  lambda * R(theta)
- Left term: fit the data. Right term: don't get carried away
- We minimise empirical risk but we care about TRUE risk
- The entire field of generalization lives in that gap

<!-- speaker note: Write the equation on a whiteboard. Everything else is commentary. -->

---

## Losses you must recognise on sight

| Task | Loss | Note |
|---|---|---|
| Regression | MSE | punishes outliers, assumes Gaussian noise |
| Regression | MAE / Huber | robust alternatives |
| Binary | Binary cross-entropy | needs calibrated probabilities |
| Multi-class | Categorical cross-entropy | this is the LLM training loss |
| Ranking | Pairwise hinge / InfoNCE | returns in RAG rerankers |


<!-- speaker note: Highlight row 4 - it links directly to Module 04. -->

---

## Model families that still matter

- Linear / logistic regression - interpretable, fast, and literally one neuron
- k-NN - no training; this IS vector search (Module 08)
- Decision trees -> Random Forest (cuts variance) -> Gradient boosting (cuts bias)
- Gradient-boosted trees still beat deep nets on medium tabular data
- Know also: SVM, Naive Bayes, PCA, k-Means

<!-- speaker note: Push back on 'use deep learning for everything'. Tabular is boosting's home turf. -->

---

## Features win projects; models rarely do

- Scale numerics for distance- and gradient-based models; trees don't care
- Categoricals: one-hot -> target encoding (inside CV folds!) -> embeddings
- Never build a feature from information that post-dates the prediction
- Missingness is a signal - add an is_missing flag
- Model choice is ~10% of the outcome

<!-- speaker note: Ask the room for their worst feature-engineering war story. -->

---

## Data leakage

> **Any information in training that will not exist at prediction time.**

- Symptom: suspiciously high validation score, one dominant feature
- Scaling/encoding before the split
- Random splits on time series
- IDs, timestamps, downstream artefacts, duplicate rows

<!-- speaker note: This is the career-defining bug. Everyone ships it once. -->

---

## Pick the metric that matches the cost of being wrong

| Metric | Question it answers | Use when |
|---|---|---|
| Precision | of my alarms, how many were real? | false positives cost money |
| Recall | of the real cases, how many did I catch? | misses cost lives |
| ROC-AUC | ranking quality | balanced classes |
| PR-AUC | ranking quality for rare positives | imbalanced - the honest choice |
| Calibration | does 0.8 mean 80%? | a human/system consumes the number |


<!-- speaker note: In a 99.9% negative dataset, 'always say no' scores 99.9% accuracy. -->

---

## Optimization: gradient descent

- theta <- theta - eta * grad J(theta)
- Learning rate eta is the single most important hyperparameter
- Too small: crawls. Too large: diverges to NaN
- Mini-batch (32-8192) won: GPU-friendly with useful noise
- Adam -> AdamW (decoupled weight decay) trains modern LLMs

<!-- speaker note: AdamW + linear warmup + cosine decay is the canonical LLM recipe. -->

---

## Reading a loss curve

| Symptom | Cause | Fix |
|---|---|---|
| Loss -> NaN | LR too high, exploding grads | lower LR, clip, check log(0) |
| Flat from step 0 | LR too low or broken labels | raise LR, overfit 10 examples |
| Train down, val up | overfitting | regularise, more data, early stop |
| Both high | underfitting | bigger model, train longer |
| Spiky val | small batch / small val set | bigger batch, LR decay |


<!-- speaker note: Smoke test: can the model overfit 10 examples to ~0 loss? If not, it's a bug, not a hyperparameter. -->

---

## Bias-variance

- E[(y - f)^2] = Bias^2 + Variance + irreducible noise
- High bias = underfit: wrong on train and test, consistently
- High variance = overfit: great on train, swings with the sample
- Irreducible noise = your label-quality ceiling
- Double descent: past the interpolation threshold, test error can fall AGAIN

<!-- speaker note: Double descent is the permission slip for trillion-parameter models. -->

---

## The anti-variance toolkit

| Technique | Mechanism | Where it reappears |
|---|---|---|
| L2 / Ridge | penalise sum(theta^2) | weight decay in LLM training |
| L1 / Lasso | drives weights to zero | feature selection |
| Early stopping | halt on val plateau | universal, free |
| Dropout | randomly zero activations | Module 02 |
| Augmentation | enlarge the dataset | synthetic data for LLMs |
| Ensembling | average errors away | LLM self-consistency |


---

## Validation strategy

- Stratified k-fold is the classification default
- Group k-fold when rows share an entity (patient, customer, session)
- Time-series split: train on the past, validate on the future. Never shuffle time
- Nested CV is the only unbiased way to report a tuned model's score
- The test set is sacred - touch it once

<!-- speaker note: Twenty peeks at the test set and your number is fiction. -->

---

## The test set is sacred

> **Benchmark contamination in LLMs is this exact bug, committed by an entire field at once.**

- Thousands of papers tuned against MMLU
- MMLU stopped measuring what it claimed to
- See Module 15 - AI Evaluation

<!-- speaker note: Great transition slide if you are teaching the whole track. -->

---

## The workflow to internalise

- Frame -> Baseline -> Split -> Explore -> Features
- Model -> Tune -> Interpret -> Test once -> Ship & watch
- Seniority shows in Frame, Explore, and Ship & watch
- Everyone rushes to Model
- Error analysis: read the 100 worst predictions, tag causes, fix the top one

<!-- speaker note: Error analysis becomes 'failure taxonomy' in Module 15. -->

---

## Your exit check

- A notebook with: baseline, tuned model, leakage-free CV, calibration curve
- One paragraph on when the model should NOT be trusted
- Run code/linear_models_from_scratch.py and code/evaluation_playbook.py
- Then: Module 02 - Deep Learning

---

## Now go build

`code/` run it · `lab/EXERCISES.md` break it · `papers/` go deeper
