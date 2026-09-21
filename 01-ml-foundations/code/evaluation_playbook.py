"""
The honest-evaluation playbook — metrics, leakage, imbalance, calibration.

Demonstrates, on synthetic data you can reason about:
  1. Why accuracy lies under class imbalance
  2. Why ROC-AUC flatters rare-positive problems and PR-AUC doesn't
  3. What data leakage does to your validation score
  4. Why you scale INSIDE the cross-validation fold
  5. What a calibration curve tells you

    python code/evaluation_playbook.py

Requires: numpy, scikit-learn
"""
from __future__ import annotations

import numpy as np
from sklearn.calibration import calibration_curve
from sklearn.datasets import make_classification
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, average_precision_score,
                             confusion_matrix, f1_score, precision_score,
                             recall_score, roc_auc_score)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

RANDOM_STATE = 42
rng = np.random.default_rng(RANDOM_STATE)
rule = lambda t: print("\n" + "=" * 70 + f"\n{t}\n" + "=" * 70)


def imbalance_demo() -> None:
    rule("1. ACCURACY IS A TRAP  (1% positive class)")
    X, y = make_classification(n_samples=20_000, n_features=20, n_informative=6,
                               weights=[0.99], flip_y=0.01, random_state=RANDOM_STATE)
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.3, stratify=y,
                                          random_state=RANDOM_STATE)
    print(f"  positives in test: {yte.mean():.2%}")

    always_no = np.zeros_like(yte)
    print(f"\n  'always predict negative'  accuracy = {accuracy_score(yte, always_no):.4f}  "
          f"recall = {recall_score(yte, always_no, zero_division=0):.4f}   <- useless model, great accuracy")

    model = Pipeline([("scale", StandardScaler()),
                      ("clf", LogisticRegression(max_iter=1000))]).fit(Xtr, ytr)
    p = model.predict_proba(Xte)[:, 1]
    yhat = (p >= 0.5).astype(int)
    tn, fp, fn, tp = confusion_matrix(yte, yhat).ravel()
    print(f"\n  logistic regression @0.5")
    print(f"    TP={tp:<5} FP={fp:<5} FN={fn:<5} TN={tn}")
    print(f"    accuracy  = {accuracy_score(yte, yhat):.4f}")
    print(f"    precision = {precision_score(yte, yhat, zero_division=0):.4f}")
    print(f"    recall    = {recall_score(yte, yhat, zero_division=0):.4f}")
    print(f"    f1        = {f1_score(yte, yhat, zero_division=0):.4f}")
    print(f"    ROC-AUC   = {roc_auc_score(yte, p):.4f}   <- looks wonderful")
    print(f"    PR-AUC    = {average_precision_score(yte, p):.4f}   <- the honest number")
    print(f"    baseline PR-AUC (random) = {yte.mean():.4f}")

    rule("1b. THRESHOLD IS A PRODUCT DECISION, NOT A DEFAULT")
    print(f"  {'thresh':>8} {'precision':>10} {'recall':>8} {'alerts':>8}")
    for t in (0.05, 0.1, 0.2, 0.3, 0.5, 0.7):
        yh = (p >= t).astype(int)
        print(f"  {t:>8.2f} {precision_score(yte, yh, zero_division=0):>10.3f} "
              f"{recall_score(yte, yh, zero_division=0):>8.3f} {yh.sum():>8}")
    print("  Pick the row your ops team can actually staff.")


def leakage_demo() -> None:
    rule("2. DATA LEAKAGE  (a feature that quietly contains the answer)")
    X, y = make_classification(n_samples=5_000, n_features=12, n_informative=5,
                               random_state=RANDOM_STATE)
    clean = cross_val_score(
        Pipeline([("s", StandardScaler()), ("m", RandomForestClassifier(
            n_estimators=120, random_state=RANDOM_STATE))]),
        X, y, cv=5, scoring="roc_auc")

    leaky_feature = y + rng.normal(scale=0.35, size=len(y))     # "post-outcome" column
    X_leak = np.column_stack([X, leaky_feature])
    leaked = cross_val_score(
        Pipeline([("s", StandardScaler()), ("m", RandomForestClassifier(
            n_estimators=120, random_state=RANDOM_STATE))]),
        X_leak, y, cv=5, scoring="roc_auc")

    print(f"  honest  CV ROC-AUC = {clean.mean():.4f} (+/- {clean.std():.4f})")
    print(f"  leaked  CV ROC-AUC = {leaked.mean():.4f} (+/- {leaked.std():.4f})  <- 'wow, 0.99!'")
    print("  Heuristic: a single feature with overwhelming importance and a score")
    print("  that jumps overnight is leakage until proven otherwise.")


def preprocessing_leak_demo() -> None:
    rule("3. SCALE INSIDE THE FOLD, NOT BEFORE IT")
    X, y = make_classification(n_samples=800, n_features=60, n_informative=4,
                               random_state=RANDOM_STATE)
    cv = StratifiedKFold(5, shuffle=True, random_state=RANDOM_STATE)

    X_pre = StandardScaler().fit_transform(X)                   # <- fit on ALL data: wrong
    wrong = cross_val_score(LogisticRegression(max_iter=2000), X_pre, y, cv=cv, scoring="roc_auc")
    right = cross_val_score(
        Pipeline([("s", StandardScaler()), ("m", LogisticRegression(max_iter=2000))]),
        X, y, cv=cv, scoring="roc_auc")
    print(f"  scaler fit on full dataset (WRONG) = {wrong.mean():.4f}")
    print(f"  scaler inside Pipeline   (RIGHT)   = {right.mean():.4f}")
    print("  The gap is small here and enormous with target/mean encoding.")
    print("  Rule: every transform that learns a statistic belongs in the Pipeline.")


def calibration_demo() -> None:
    rule("4. CALIBRATION — does '0.8' mean 80%?")
    X, y = make_classification(n_samples=12_000, n_features=20, n_informative=8,
                               random_state=RANDOM_STATE)
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.3, random_state=RANDOM_STATE)

    for name, m in [("logistic  ", LogisticRegression(max_iter=2000)),
                    ("rand.forest", RandomForestClassifier(n_estimators=200,
                                                           random_state=RANDOM_STATE))]:
        m.fit(Xtr, ytr)
        p = m.predict_proba(Xte)[:, 1]
        true_freq, pred_mean = calibration_curve(yte, p, n_bins=8, strategy="quantile")
        ece = float(np.mean(np.abs(true_freq - pred_mean)))
        bars = "  ".join(f"{pm:.2f}->{tf:.2f}" for pm, tf in zip(pred_mean, true_freq))
        print(f"\n  {name}  ECE~{ece:.4f}")
        print(f"    predicted->actual: {bars}")
    print("\n  Perfect calibration is the identity map. Tree ensembles are usually")
    print("  over-confident at the extremes; fix with Platt scaling or isotonic regression.")
    print("  This same question returns in Module 15 for LLM confidence scores.")


if __name__ == "__main__":
    imbalance_demo()
    leakage_demo()
    preprocessing_leak_demo()
    calibration_demo()
    print("\nDone. Now go re-read notes/01-core-concepts.md section 6.\n")
