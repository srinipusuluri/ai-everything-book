"""
Backpropagation from scratch — a full MLP in NumPy, with a gradient check.

Four equations are the whole algorithm:
    delta_L = dJ/da * phi'(z_L)
    delta_l = (W_{l+1}^T delta_{l+1}) * phi'(z_l)
    dJ/dW_l = delta_l a_{l-1}^T
    dJ/db_l = delta_l

    python code/backprop_from_scratch.py

Requires: numpy, scikit-learn (for the digits dataset only)
"""
from __future__ import annotations

import numpy as np

rng = np.random.default_rng(0)


# --------------------------------------------------------------------------- #
# Activations                                                                  #
# --------------------------------------------------------------------------- #
def relu(z):            return np.maximum(0.0, z)
def relu_grad(z):       return (z > 0).astype(z.dtype)
def tanh(z):            return np.tanh(z)
def tanh_grad(z):       return 1.0 - np.tanh(z) ** 2


ACT = {"relu": (relu, relu_grad), "tanh": (tanh, tanh_grad)}


def softmax(z):
    """Row-wise softmax. Subtract the max or exp() overflows for large logits."""
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


# --------------------------------------------------------------------------- #
# The network                                                                  #
# --------------------------------------------------------------------------- #
class MLP:
    """A plain multi-layer perceptron with softmax output and cross-entropy loss."""

    def __init__(self, sizes: list[int], activation: str = "relu", seed: int = 0):
        self.sizes = sizes
        self.act, self.act_grad = ACT[activation]
        r = np.random.default_rng(seed)
        # He initialisation: var = 2 / fan_in. Zero init would make every unit
        # in a layer identical forever -- symmetry must be broken.
        self.W = [r.normal(scale=np.sqrt(2.0 / a), size=(a, b))
                  for a, b in zip(sizes[:-1], sizes[1:])]
        self.b = [np.zeros(b) for b in sizes[1:]]

    # ---- forward ---------------------------------------------------------- #
    def forward(self, X):
        """Returns (probs, cache). The cache is what backprop consumes."""
        a = X
        zs, acts = [], [X]
        for i, (W, b) in enumerate(zip(self.W, self.b)):
            z = a @ W + b
            zs.append(z)
            a = softmax(z) if i == len(self.W) - 1 else self.act(z)
            acts.append(a)
        return a, (zs, acts)

    # ---- loss ------------------------------------------------------------- #
    @staticmethod
    def loss(probs, Y):
        """Categorical cross-entropy. Y is one-hot."""
        n = Y.shape[0]
        return float(-np.sum(Y * np.log(probs + 1e-12)) / n)

    # ---- backward --------------------------------------------------------- #
    def backward(self, Y, cache):
        zs, acts = cache
        n = Y.shape[0]
        gW = [None] * len(self.W)
        gb = [None] * len(self.b)

        # The famous simplification: for softmax + cross-entropy, dJ/dz = p - y.
        # Every exponential and its derivative cancels. This is why frameworks
        # fuse the two ops and why cross_entropy() takes LOGITS, not probabilities.
        delta = (acts[-1] - Y) / n

        for l in range(len(self.W) - 1, -1, -1):
            gW[l] = acts[l].T @ delta
            gb[l] = delta.sum(axis=0)
            if l > 0:
                delta = (delta @ self.W[l].T) * self.act_grad(zs[l - 1])
        return gW, gb

    # ---- training --------------------------------------------------------- #
    def fit(self, X, Y, *, epochs=60, lr=0.1, batch_size=64, l2=0.0, verbose=True,
            X_val=None, Y_val=None):
        n = X.shape[0]
        hist = []
        for ep in range(epochs):
            idx = rng.permutation(n)
            for s in range(0, n, batch_size):
                sl = idx[s:s + batch_size]
                probs, cache = self.forward(X[sl])
                gW, gb = self.backward(Y[sl], cache)
                for l in range(len(self.W)):
                    self.W[l] -= lr * (gW[l] + l2 * self.W[l])
                    self.b[l] -= lr * gb[l]
            p, _ = self.forward(X)
            tr = self.loss(p, Y)
            row = {"epoch": ep, "train_loss": tr, "train_acc": self.accuracy(X, Y)}
            if X_val is not None:
                pv, _ = self.forward(X_val)
                row["val_loss"] = self.loss(pv, Y_val)
                row["val_acc"] = self.accuracy(X_val, Y_val)
            hist.append(row)
            if verbose and (ep % 10 == 0 or ep == epochs - 1):
                extra = (f"  val_loss={row['val_loss']:.4f} val_acc={row['val_acc']:.4f}"
                         if X_val is not None else "")
                print(f"  epoch {ep:>3}  train_loss={tr:.4f} train_acc={row['train_acc']:.4f}{extra}")
        return hist

    def accuracy(self, X, Y):
        p, _ = self.forward(X)
        return float((p.argmax(1) == Y.argmax(1)).mean())


# --------------------------------------------------------------------------- #
# Gradient check — never trust a backward pass you haven't verified            #
# --------------------------------------------------------------------------- #
def gradient_check(net: MLP, X, Y, eps: float = 1e-5) -> float:
    probs, cache = net.forward(X)
    gW, gb = net.backward(Y, cache)
    worst = 0.0
    for l in range(len(net.W)):
        for _ in range(12):                       # sample a few random entries
            i = rng.integers(net.W[l].shape[0])
            j = rng.integers(net.W[l].shape[1])
            orig = net.W[l][i, j]
            net.W[l][i, j] = orig + eps
            p1, _ = net.forward(X)
            lp = net.loss(p1, Y)
            net.W[l][i, j] = orig - eps
            p2, _ = net.forward(X)
            lm = net.loss(p2, Y)
            net.W[l][i, j] = orig
            numeric = (lp - lm) / (2 * eps)
            analytic = gW[l][i, j]
            denom = max(1e-8, abs(numeric) + abs(analytic))
            worst = max(worst, abs(numeric - analytic) / denom)
    return worst


# --------------------------------------------------------------------------- #
# Demos                                                                        #
# --------------------------------------------------------------------------- #
def one_hot(y, k):
    Y = np.zeros((len(y), k))
    Y[np.arange(len(y)), y] = 1
    return Y


def demo_xor():
    print("=" * 70)
    print("1. XOR — the problem a single linear layer provably cannot solve")
    print("=" * 70)
    X = np.array([[0., 0.], [0., 1.], [1., 0.], [1., 1.]])
    y = np.array([0, 1, 1, 0])
    Y = one_hot(y, 2)

    flat = MLP([2, 2], seed=1)        # no hidden layer = logistic regression
    flat.fit(X, Y, epochs=400, lr=0.5, batch_size=4, verbose=False)
    print(f"  no hidden layer : accuracy = {flat.accuracy(X, Y):.2f}   <- stuck at chance")

    deep = MLP([2, 8, 2], activation="tanh", seed=1)
    deep.fit(X, Y, epochs=2000, lr=0.5, batch_size=4, verbose=False)
    print(f"  one hidden layer: accuracy = {deep.accuracy(X, Y):.2f}   <- the nonlinearity earns its keep")


def demo_digits():
    from sklearn.datasets import load_digits
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler

    print()
    print("=" * 70)
    print("2. DIGITS — 8x8 handwritten digits, 10 classes")
    print("=" * 70)
    d = load_digits()
    X = StandardScaler().fit_transform(d.data)
    Y = one_hot(d.target, 10)
    Xtr, Xte, Ytr, Yte = train_test_split(X, Y, test_size=0.25, random_state=0, stratify=d.target)

    net = MLP([64, 64, 32, 10], activation="relu", seed=3)
    p0, _ = net.forward(Xtr)
    print(f"  loss at step 0 = {net.loss(p0, Ytr):.4f}   (theory says ln(10) = {np.log(10):.4f})")
    net.fit(Xtr, Ytr, epochs=60, lr=0.25, batch_size=64, X_val=Xte, Y_val=Yte)
    print(f"  final test accuracy = {net.accuracy(Xte, Yte):.4f}")


def demo_gradcheck():
    print()
    print("=" * 70)
    print("3. GRADIENT CHECK")
    print("=" * 70)
    X = rng.normal(size=(12, 6))
    Y = one_hot(rng.integers(0, 4, size=12), 4)
    net = MLP([6, 10, 7, 4], activation="tanh", seed=5)   # tanh: smooth, safe for finite differences
    err = gradient_check(net, X, Y)
    print(f"  worst relative error = {err:.3e}   -> {'PASS' if err < 1e-6 else 'CHECK ME'}")
    print("  (Use tanh here: ReLU's kink at 0 makes finite differences unreliable.)")


def demo_dead_relu():
    print()
    print("=" * 70)
    print("4. WHAT A BAD LEARNING RATE LOOKS LIKE")
    print("=" * 70)
    from sklearn.datasets import load_digits
    from sklearn.preprocessing import StandardScaler
    d = load_digits()
    X = StandardScaler().fit_transform(d.data)
    Y = one_hot(d.target, 10)
    for lr in (0.001, 0.05, 0.25, 2.0, 25.0):
        net = MLP([64, 64, 10], seed=3)
        h = net.fit(X, Y, epochs=15, lr=lr, batch_size=64, verbose=False)
        final = h[-1]["train_loss"]
        verdict = ("diverged" if not np.isfinite(final) or final > 5
                   else "crawling" if final > 0.5 else "healthy")
        print(f"  lr={lr:<7} final train loss = {final:>12.5f}   {verdict}")


if __name__ == "__main__":
    demo_xor()
    demo_digits()
    demo_gradcheck()
    demo_dead_relu()
    print("\nNext: open code/pytorch_training_loop.py and find these same four")
    print("equations hiding behind loss.backward().\n")
