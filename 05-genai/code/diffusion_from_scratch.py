"""
A minimal DDPM you can read start to finish — NumPy only, no GPU, no display.

Every real diffusion model (Stable Diffusion, Imagen, Sora) is this file plus scale: a bigger
denoiser (a U-Net or DiT instead of a 2-hidden-layer MLP), bigger data (pixels instead of 2D
points), and a much bigger T. The math is identical. If you understand this file, you understand
the mechanism inside every image/video/audio generator in Module 05's notes.

What this script does, in order:
  1. Builds a 2D "two moons" dataset — a shape a linear model cannot fit, small enough to reason about.
  2. Runs the closed-form FORWARD (noising) process and prints statistics showing x_t -> N(0, I).
  3. Trains a tiny MLP denoiser epsilon_theta(x_t, t) by plain MSE regression (predict the noise).
  4. Runs DDPM sampling: start from pure noise, iteratively denoise, and land back on the moons.
  5. Extends to a 2-CLASS CONDITIONAL model with classifier-free-guidance-style condition dropout,
     and samples each class under guidance to show conditioning actually steering the output.

No matplotlib: since there's no display in this environment, "visual" here means (a) printed
distribution statistics that let you verify the theory numerically, and (b) a coarse ASCII
scatter-plot renderer — a text-mode substitute for "look at the picture."

    python code/diffusion_from_scratch.py

Requires: numpy
"""
from __future__ import annotations

import numpy as np

rng = np.random.default_rng(0)


# =========================================================================== #
# 1. Data: two moons (and a 2-class labelled version for conditioning)        #
# =========================================================================== #
def make_moons(n: int, noise: float, r: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    """Two interleaving half-circles. Class 0 is the upper moon, class 1 the lower one."""
    n0, n1 = n // 2, n - n // 2
    theta0 = r.uniform(0, np.pi, n0)
    x0 = np.stack([np.cos(theta0), np.sin(theta0)], axis=1)
    theta1 = r.uniform(0, np.pi, n1)
    x1 = np.stack([1 - np.cos(theta1), 1 - np.sin(theta1) - 0.5], axis=1)
    X = np.vstack([x0, x1]) + r.normal(scale=noise, size=(n, 2))
    y = np.concatenate([np.zeros(n0, dtype=int), np.ones(n1, dtype=int)])
    idx = r.permutation(n)
    return X[idx], y[idx]


def standardize(X: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mu, sigma = X.mean(0), X.std(0)
    return (X - mu) / sigma, mu, sigma


def ascii_scatter(points: np.ndarray, labels: np.ndarray | None = None,
                   width: int = 56, height: int = 20,
                   xlim=(-2.6, 2.6), ylim=(-2.2, 2.2)) -> str:
    """A coarse text-mode scatter plot. '.' = class 0, 'o' = class 1, '*' = unlabelled."""
    grid = [[" "] * width for _ in range(height)]
    for i, (x, y) in enumerate(points):
        xi = int((x - xlim[0]) / (xlim[1] - xlim[0]) * width)
        yi = int((y - ylim[0]) / (ylim[1] - ylim[0]) * height)
        if 0 <= xi < width and 0 <= yi < height:
            ch = "*" if labels is None else ("." if labels[i] == 0 else "o")
            grid[height - 1 - yi][xi] = ch
    border = "+" + "-" * width + "+"
    return border + "\n" + "\n".join("|" + "".join(row) + "|" for row in grid) + "\n" + border


# =========================================================================== #
# 2. The diffusion schedule and the closed-form forward process               #
# =========================================================================== #
class DiffusionSchedule:
    """Linear beta schedule. beta_end is set high enough that x_T is ~indistinguishable
    from N(0, I) by the last step -- verify this yourself in section 3's printout."""

    def __init__(self, T: int = 200, beta_start: float = 1e-4, beta_end: float = 0.05):
        self.T = T
        self.betas = np.linspace(beta_start, beta_end, T)
        self.alphas = 1.0 - self.betas
        self.alpha_bars = np.cumprod(self.alphas)          # abar_t = prod_{s<=t} alpha_s

    def q_sample(self, x0: np.ndarray, t: np.ndarray, eps: np.ndarray) -> np.ndarray:
        """Closed-form q(x_t | x_0):  x_t = sqrt(abar_t) x0 + sqrt(1 - abar_t) eps.
        This is THE equation that makes training tractable -- no simulation loop needed."""
        ab = self.alpha_bars[t][:, None]
        return np.sqrt(ab) * x0 + np.sqrt(1.0 - ab) * eps


def time_embedding(t: np.ndarray, T: int, dim: int = 8) -> np.ndarray:
    """Fixed (non-learned) sinusoidal embedding of the timestep -- same trick as a
    transformer's positional encoding (Module 03), just encoding 'how noisy' instead of 'where'."""
    frac = (t.astype(float) / T)[:, None]
    freqs = (2.0 ** np.arange(dim // 2))[None, :]
    ang = frac * freqs * np.pi
    return np.concatenate([np.sin(ang), np.cos(ang)], axis=1)


# =========================================================================== #
# 3. The denoiser: a tiny MLP, manual forward/backward, Adam                  #
#    (same four backprop equations as Module 02's backprop_from_scratch.py,   #
#     with a linear output layer and MSE loss instead of softmax + CE)        #
# =========================================================================== #
def tanh(z):        return np.tanh(z)
def tanh_grad(z):   return 1.0 - np.tanh(z) ** 2


class DenoiserMLP:
    """Predicts the noise epsilon that was added, given (x_t, time embedding[, condition])."""

    def __init__(self, in_dim: int, hidden: int = 64, out_dim: int = 2, seed: int = 0):
        r = np.random.default_rng(seed)
        sizes = [in_dim, hidden, hidden, out_dim]
        self.W = [r.normal(scale=np.sqrt(2.0 / a), size=(a, b)) for a, b in zip(sizes[:-1], sizes[1:])]
        self.b = [np.zeros(b) for b in sizes[1:]]
        # Adam moment buffers
        self.mW = [np.zeros_like(w) for w in self.W]
        self.vW = [np.zeros_like(w) for w in self.W]
        self.mb = [np.zeros_like(b) for b in self.b]
        self.vb = [np.zeros_like(b) for b in self.b]
        self.step_count = 0

    def forward(self, X: np.ndarray):
        a = X
        zs, acts = [], [X]
        for i, (W, b) in enumerate(zip(self.W, self.b)):
            z = a @ W + b
            zs.append(z)
            a = z if i == len(self.W) - 1 else tanh(z)     # linear output layer -- this is regression
            acts.append(a)
        return a, (zs, acts)

    def backward(self, target: np.ndarray, cache):
        zs, acts = cache
        pred = acts[-1]
        # dL/dpred for MSE = mean((pred-target)^2): dL/dpred = 2*(pred-target)/pred.size
        delta = 2.0 * (pred - target) / pred.size
        gW, gb = [None] * len(self.W), [None] * len(self.b)
        for l in range(len(self.W) - 1, -1, -1):
            gW[l] = acts[l].T @ delta
            gb[l] = delta.sum(axis=0)
            if l > 0:
                delta = (delta @ self.W[l].T) * tanh_grad(zs[l - 1])
        return gW, gb

    def adam_step(self, gW, gb, lr=2e-3, b1=0.9, b2=0.999, eps=1e-8):
        self.step_count += 1
        t = self.step_count
        for l in range(len(self.W)):
            self.mW[l] = b1 * self.mW[l] + (1 - b1) * gW[l]
            self.vW[l] = b2 * self.vW[l] + (1 - b2) * gW[l] ** 2
            mhat, vhat = self.mW[l] / (1 - b1 ** t), self.vW[l] / (1 - b2 ** t)
            self.W[l] -= lr * mhat / (np.sqrt(vhat) + eps)

            self.mb[l] = b1 * self.mb[l] + (1 - b1) * gb[l]
            self.vb[l] = b2 * self.vb[l] + (1 - b2) * gb[l] ** 2
            mhatb, vhatb = self.mb[l] / (1 - b1 ** t), self.vb[l] / (1 - b2 ** t)
            self.b[l] -= lr * mhatb / (np.sqrt(vhatb) + eps)


def predict_noise(net: DenoiserMLP, x_t: np.ndarray, t: np.ndarray, T: int,
                   cond: np.ndarray | None = None) -> np.ndarray:
    temb = time_embedding(t, T)
    feat = np.concatenate([x_t, temb] if cond is None else [x_t, temb, cond], axis=1)
    pred, _ = net.forward(feat)
    return pred


# =========================================================================== #
# 4. Training loop -- plain regression, no adversary, no ELBO to fuss over    #
# =========================================================================== #
def train_denoiser(X0: np.ndarray, schedule: DiffusionSchedule, *, cond: np.ndarray | None = None,
                    null_cond: np.ndarray | None = None, p_uncond: float = 0.0,
                    hidden: int = 64, iters: int = 4000, batch_size: int = 256,
                    lr: float = 2e-3, seed: int = 1, log_every: int | None = None):
    n, d = X0.shape
    cond_dim = cond.shape[1] if cond is not None else 0
    net = DenoiserMLP(in_dim=d + 8 + cond_dim, hidden=hidden, out_dim=d, seed=seed)
    r = np.random.default_rng(seed + 1)
    log_every = log_every or max(1, iters // 8)
    losses = []
    for it in range(iters):
        idx = r.integers(0, n, size=batch_size)
        x0 = X0[idx]
        t = r.integers(0, schedule.T, size=batch_size)
        eps = r.normal(size=x0.shape)
        x_t = schedule.q_sample(x0, t, eps)
        c = None
        if cond is not None:
            c = cond[idx].copy()
            if p_uncond > 0:                                 # classifier-free-guidance dropout
                drop = r.random(batch_size) < p_uncond
                c[drop] = null_cond
        temb = time_embedding(t, schedule.T)
        feat = np.concatenate([x_t, temb] if c is None else [x_t, temb, c], axis=1)
        pred, cache = net.forward(feat)
        loss = float(np.mean((pred - eps) ** 2))
        gW, gb = net.backward(eps, cache)
        net.adam_step(gW, gb, lr=lr)
        losses.append(loss)
        if it % log_every == 0 or it == iters - 1:
            print(f"  iter {it:5d}   MSE(predicted noise, true noise) = {loss:.4f}")
    return net, losses


# =========================================================================== #
# 5. DDPM sampling -- run the reverse process, one small step at a time       #
# =========================================================================== #
def ddpm_sample(net: DenoiserMLP, schedule: DiffusionSchedule, n_samples: int, dim: int = 2,
                 cond: np.ndarray | None = None, guidance_scale: float | None = None,
                 null_cond: np.ndarray | None = None, seed: int = 0, verbose: bool = False):
    r = np.random.default_rng(seed)
    x = r.normal(size=(n_samples, dim))                       # x_T ~ N(0, I)
    checkpoints = []
    for t in reversed(range(schedule.T)):
        t_arr = np.full(n_samples, t)
        if cond is not None and guidance_scale is not None:
            eps_c = predict_noise(net, x, t_arr, schedule.T, cond)
            null = np.tile(null_cond, (n_samples, 1))
            eps_u = predict_noise(net, x, t_arr, schedule.T, null)
            eps_hat = eps_u + guidance_scale * (eps_c - eps_u)     # classifier-free guidance
        else:
            eps_hat = predict_noise(net, x, t_arr, schedule.T, cond)

        alpha_t, abar_t, beta_t = schedule.alphas[t], schedule.alpha_bars[t], schedule.betas[t]
        mean = (x - (beta_t / np.sqrt(1 - abar_t)) * eps_hat) / np.sqrt(alpha_t)
        if t > 0:
            x = mean + np.sqrt(beta_t) * r.normal(size=x.shape)   # DDPM re-injects noise: stochastic
        else:
            x = mean
        if verbose and (t % max(1, schedule.T // 5) == 0 or t == 0):
            checkpoints.append((t, x.mean(0).copy(), x.std(0).copy()))
    return x, checkpoints


# =========================================================================== #
# 6. Quality proxies (a cheap precision/recall for 2D generative samples)     #
# =========================================================================== #
def nn_distance(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    """For each row in A, the Euclidean distance to its nearest neighbour in B."""
    d2 = ((A[:, None, :] - B[None, :, :]) ** 2).sum(-1)
    return np.sqrt(d2.min(axis=1))


def precision_recall_proxy(generated: np.ndarray, real: np.ndarray) -> tuple[float, float]:
    """precision: how close generated points sit to the real manifold (realism).
    recall: how close real points sit to the nearest generated point (coverage/diversity --
    a collapsed generator scores badly here even if precision looks great)."""
    precision = float(nn_distance(generated, real).mean())
    recall = float(nn_distance(real, generated).mean())
    return precision, recall


# =========================================================================== #
# 7. Demo                                                                     #
# =========================================================================== #
def section(title: str) -> None:
    print("\n" + "=" * 74 + f"\n{title}\n" + "=" * 74)


def demo():
    N = 1200
    X_raw, y = make_moons(N, noise=0.08, r=rng)
    X, mu, sigma = standardize(X_raw)

    section("1. THE TARGET DISTRIBUTION -- two moons, standardized")
    print(f"  {N} points, 2 classes.  mean={X.mean(0).round(3)}  std={X.std(0).round(3)}")
    print(ascii_scatter(X, y))

    # ----------------------------------------------------------------- #
    section("2. FORWARD PROCESS -- watch x_t march toward N(0, I)")
    schedule = DiffusionSchedule(T=200, beta_start=1e-4, beta_end=0.05)
    print(f"  T={schedule.T} steps. Theory: x_t = sqrt(abar_t) x0 + sqrt(1-abar_t) eps")
    print(f"  {'t':>5} {'abar_t':>9} {'signal frac sqrt(abar_t)':>26} {'x_t std (theory)':>18} {'x_t std (measured)':>20}")
    for t in [0, 10, 40, 80, 120, 160, schedule.T - 1]:
        ab = schedule.alpha_bars[t]
        eps = rng.normal(size=X.shape)
        x_t = schedule.q_sample(X, np.full(len(X), t), eps)
        print(f"  {t:>5} {ab:>9.4f} {np.sqrt(ab):>26.4f} {np.sqrt(1 - ab):>18.4f} {x_t.std(0).mean():>20.4f}")
    print("\n  By the last row, signal fraction ~0 and x_t's measured std matches the noise-only")
    print("  prediction -- the original moons shape has been destroyed on schedule. ASCII check:")
    for t in [0, 40, 120, schedule.T - 1]:
        eps = rng.normal(size=X.shape)
        x_t = schedule.q_sample(X, np.full(len(X), t), eps)
        print(f"\n  x_t at t={t}:")
        print(ascii_scatter(x_t, width=40, height=12, xlim=(-3, 3), ylim=(-3, 3)))

    # ----------------------------------------------------------------- #
    section("3. TRAINING THE DENOISER  epsilon_theta(x_t, t)  -- plain MSE regression")
    net, losses = train_denoiser(X, schedule, iters=4000, batch_size=256, lr=2e-3, seed=1)
    print(f"\n  loss: iter 0 ~ {losses[0]:.4f}  ->  final ~ {np.mean(losses[-100:]):.4f}")
    print("  (Theory floor: predicting standard-normal noise from a fully-noised input caps out")
    print("   near MSE=1.0 for large t; the average above is pulled down by the easy, low-t steps.)")

    # ----------------------------------------------------------------- #
    section("4. DDPM SAMPLING -- start from pure noise, denoise back to the moons")
    gen, checkpoints = ddpm_sample(net, schedule, n_samples=400, seed=42, verbose=True)
    print(f"  {'t':>5} {'mean':>18} {'std':>18}")
    for t, m, s in checkpoints:
        print(f"  {t:>5} {np.round(m, 3)!s:>18} {np.round(s, 3)!s:>18}")
    prec, rec = precision_recall_proxy(gen, X)
    print(f"\n  generated samples: mean={gen.mean(0).round(3)}  std={gen.std(0).round(3)}")
    print(f"  precision proxy (gen -> nearest real, lower=more realistic)   = {prec:.4f}")
    print(f"  recall proxy    (real -> nearest gen,  lower=better coverage) = {rec:.4f}")
    print("\n  Generated samples (should trace the two moons again):")
    print(ascii_scatter(gen))

    # ----------------------------------------------------------------- #
    section("5. CONDITIONAL MODEL -- 2-class one-hot condition + CFG-style dropout")
    cond = np.zeros((len(X), 2))
    cond[y == 0, 0] = 1.0
    cond[y == 1, 1] = 1.0
    null_cond = np.zeros(2)                                   # the 'no condition' vector
    print("  Training with p_uncond=0.15 (15% of steps see the null condition) -- this is exactly")
    print("  what makes classifier-free guidance possible at sampling time (see notes 01, section 2.4).")
    cnet, closses = train_denoiser(X, schedule, cond=cond, null_cond=null_cond, p_uncond=0.15,
                                    iters=4000, batch_size=256, lr=2e-3, seed=2)
    print(f"\n  final loss ~ {np.mean(closses[-100:]):.4f}")

    centroid0, centroid1 = X[y == 0].mean(0), X[y == 1].mean(0)

    def classify_by_centroid(points):
        d0 = np.linalg.norm(points - centroid0, axis=1)
        d1 = np.linalg.norm(points - centroid1, axis=1)
        return (d1 < d0).astype(int)                          # 0 if closer to centroid0

    w = 4.0
    print(f"\n  Sampling 200 points per class, guidance_scale={w}:")
    for cls in (0, 1):
        c = np.tile(np.eye(2)[cls], (200, 1))
        gen_c, _ = ddpm_sample(cnet, schedule, n_samples=200, cond=c, guidance_scale=w,
                                null_cond=null_cond, seed=100 + cls)
        pred_cls = classify_by_centroid(gen_c)
        acc = float((pred_cls == cls).mean())
        print(f"\n  requested class {cls}:  {acc:.0%} of generated points land nearer the class-{cls} centroid")
        print(ascii_scatter(gen_c, labels=pred_cls, width=40, height=10))

    print("\n  Takeaway: the SAME network produces either moon depending only on which one-hot")
    print("  condition (and how strongly it's guided) you feed it at sampling time. This is the")
    print("  conceptual core of text conditioning in Stable Diffusion -- swap 'class one-hot' for")
    print("  'CLIP text embedding' and you have classifier-free-guided text-to-image generation.")
    print("\nNext: run code/guidance_and_sampling.py for the DDPM-vs-DDIM and guidance-scale sweeps.")


if __name__ == "__main__":
    demo()
