"""
Linear & logistic regression from scratch — NumPy only.

Why this file exists
--------------------
Every neural network in Module 02, and every LLM in Module 04, is this file plus depth.
Run it, break it, and the rest of the track stops being magic.

    python code/linear_models_from_scratch.py

Requires: numpy  (pip install numpy)
"""
from __future__ import annotations

import numpy as np

rng = np.random.default_rng(7)


# --------------------------------------------------------------------------- #
# 1. Linear regression                                                        #
# --------------------------------------------------------------------------- #
class LinearRegressionGD:
    """y_hat = Xw + b, trained by batch gradient descent on MSE."""

    def __init__(self, lr: float = 0.05, epochs: int = 500, l2: float = 0.0):
        self.lr, self.epochs, self.l2 = lr, epochs, l2
        self.w: np.ndarray | None = None
        self.b: float = 0.0
        self.history: list[float] = []

    def fit(self, X: np.ndarray, y: np.ndarray) -> "LinearRegressionGD":
        n, d = X.shape
        self.w, self.b = np.zeros(d), 0.0
        for _ in range(self.epochs):
            y_hat = X @ self.w + self.b
            err = y_hat - y                                  # (n,)
            # dJ/dw = (2/n) X^T err  (+ L2 term);  dJ/db = (2/n) sum(err)
            grad_w = (2 / n) * (X.T @ err) + 2 * self.l2 * self.w
            grad_b = (2 / n) * err.sum()
            self.w -= self.lr * grad_w
            self.b -= self.lr * grad_b
            self.history.append(float((err ** 2).mean()))
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        return X @ self.w + self.b


# --------------------------------------------------------------------------- #
# 2. Logistic regression                                                      #
# --------------------------------------------------------------------------- #
def sigmoid(z: np.ndarray) -> np.ndarray:
    """Numerically stable sigmoid. Naive 1/(1+exp(-z)) overflows for z << 0."""
    out = np.empty_like(z, dtype=float)
    pos, neg = z >= 0, z < 0
    out[pos] = 1.0 / (1.0 + np.exp(-z[pos]))
    ez = np.exp(z[neg])
    out[neg] = ez / (1.0 + ez)
    return out


class LogisticRegressionGD:
    """Binary classifier trained with cross-entropy loss.

    Note the gradient: (sigma(Xw+b) - y) X  --- identical in *form* to linear
    regression's. That is not a coincidence; it is why cross-entropy is paired
    with sigmoid/softmax instead of MSE.
    """

    def __init__(self, lr: float = 0.1, epochs: int = 800, l2: float = 0.0):
        self.lr, self.epochs, self.l2 = lr, epochs, l2
        self.w: np.ndarray | None = None
        self.b: float = 0.0
        self.history: list[float] = []

    def fit(self, X: np.ndarray, y: np.ndarray) -> "LogisticRegressionGD":
        n, d = X.shape
        self.w, self.b = np.zeros(d), 0.0
        for _ in range(self.epochs):
            p = sigmoid(X @ self.w + self.b)
            eps = 1e-12                                       # guard log(0)
            loss = -np.mean(y * np.log(p + eps) + (1 - y) * np.log(1 - p + eps))
            err = p - y
            self.w -= self.lr * ((X.T @ err) / n + 2 * self.l2 * self.w)
            self.b -= self.lr * err.mean()
            self.history.append(float(loss))
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        return sigmoid(X @ self.w + self.b)

    def predict(self, X: np.ndarray, threshold: float = 0.5) -> np.ndarray:
        return (self.predict_proba(X) >= threshold).astype(int)


# --------------------------------------------------------------------------- #
# 3. Gradient check — the habit that saves you in Module 02                    #
# --------------------------------------------------------------------------- #
def gradient_check(X: np.ndarray, y: np.ndarray, eps: float = 1e-6) -> float:
    """Compare the analytic logistic gradient to a numerical one."""
    n, d = X.shape
    w = rng.normal(size=d) * 0.1

    def loss(w_):
        p = sigmoid(X @ w_)
        return -np.mean(y * np.log(p + 1e-12) + (1 - y) * np.log(1 - p + 1e-12))

    analytic = X.T @ (sigmoid(X @ w) - y) / n
    numeric = np.zeros(d)
    for j in range(d):
        wp, wm = w.copy(), w.copy()
        wp[j] += eps
        wm[j] -= eps
        numeric[j] = (loss(wp) - loss(wm)) / (2 * eps)
    return float(np.max(np.abs(analytic - numeric)))


# --------------------------------------------------------------------------- #
# 4. Demo                                                                      #
# --------------------------------------------------------------------------- #
def demo() -> None:
    print("=" * 66)
    print("LINEAR REGRESSION  — recovering y = 3x1 - 2x2 + 5 + noise")
    print("=" * 66)
    X = rng.normal(size=(400, 2))
    y = 3 * X[:, 0] - 2 * X[:, 1] + 5 + rng.normal(scale=0.3, size=400)
    lin = LinearRegressionGD(lr=0.1, epochs=400).fit(X, y)
    print(f"  learned w = {np.round(lin.w, 3)}   b = {lin.b:.3f}   (true: [3, -2], 5)")
    print(f"  MSE  first epoch {lin.history[0]:8.4f} -> last {lin.history[-1]:8.4f}")

    print()
    print("=" * 66)
    print("LOGISTIC REGRESSION — two Gaussian blobs")
    print("=" * 66)
    n = 500
    Xa = rng.normal(loc=[-1.5, -1.5], scale=1.0, size=(n, 2))
    Xb = rng.normal(loc=[1.5, 1.5], scale=1.0, size=(n, 2))
    Xc = np.vstack([Xa, Xb])
    yc = np.hstack([np.zeros(n), np.ones(n)])
    idx = rng.permutation(2 * n)
    Xc, yc = Xc[idx], yc[idx]

    split = int(0.8 * len(yc))
    Xtr, Xte, ytr, yte = Xc[:split], Xc[split:], yc[:split], yc[split:]

    clf = LogisticRegressionGD(lr=0.5, epochs=600).fit(Xtr, ytr)
    acc = (clf.predict(Xte) == yte).mean()
    print(f"  learned w = {np.round(clf.w, 3)}   b = {clf.b:.3f}")
    print(f"  loss {clf.history[0]:.4f} -> {clf.history[-1]:.4f}")
    print(f"  test accuracy = {acc:.3f}")

    print()
    print("=" * 66)
    print("EFFECT OF LEARNING RATE  (same data, 200 epochs)")
    print("=" * 66)
    for lr in (0.001, 0.01, 0.1, 1.0, 5.0):
        h = LogisticRegressionGD(lr=lr, epochs=200).fit(Xtr, ytr).history
        verdict = "diverged" if not np.isfinite(h[-1]) else ("crawling" if h[-1] > 0.4 else "healthy")
        print(f"  lr={lr:<6} final loss={h[-1]:10.5f}   {verdict}")

    print()
    print("=" * 66)
    print("GRADIENT CHECK")
    print("=" * 66)
    diff = gradient_check(Xtr, ytr)
    print(f"  max |analytic - numeric| = {diff:.3e}   -> {'PASS' if diff < 1e-5 else 'FAIL'}")
    print("\nTry next: set l2=0.5 and watch the weights shrink. Then break the")
    print("sigmoid (use the naive formula) and feed it z = -800 to see overflow.")


if __name__ == "__main__":
    demo()
