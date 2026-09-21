"""
Sampling trade-offs: DDPM vs. DDIM step counts, and the classifier-free-guidance
scale/diversity trade-off -- both measured numerically on the toy 2D diffusion
model from diffusion_from_scratch.py.

This script answers two questions you will face with every real diffusion model:

  Q1. "How many sampler steps do I actually need?"
      DDPM's stochastic reverse process wants close to the full schedule. DDIM's
      deterministic reverse process gets comparable quality in a fraction of the
      steps. We measure this with the same precision/recall proxy from script 1,
      instead of eyeballing pictures.

  Q2. "What does turning up the guidance scale actually cost me?"
      Higher guidance = more literally on-prompt, but samples for a given class
      collapse toward a narrower region of the data manifold. We measure both
      sides of that trade with a fidelity proxy and a diversity proxy.

    python code/guidance_and_sampling.py

Requires: numpy (and diffusion_from_scratch.py in the same folder)
"""
from __future__ import annotations

import time

import numpy as np

from diffusion_from_scratch import (DiffusionSchedule, make_moons, standardize,
                                     train_denoiser, predict_noise, nn_distance,
                                     precision_recall_proxy, ascii_scatter, rng)


# =========================================================================== #
# DDIM sampling -- deterministic, and can skip steps (see notes 01, section 2.3)
# =========================================================================== #
def ddim_sample(net, schedule: DiffusionSchedule, n_samples: int, *, dim: int = 2,
                 steps: int = 50, cond: np.ndarray | None = None,
                 guidance_scale: float | None = None, null_cond: np.ndarray | None = None,
                 seed: int = 0) -> np.ndarray:
    """Deterministic (eta=0) DDIM: predict x0, then re-noise it to the next selected
    timestep. Same trained network as DDPM -- only the sampling procedure differs."""
    r = np.random.default_rng(seed)
    x = r.normal(size=(n_samples, dim))
    # A strictly decreasing subsequence of the full [0, T) schedule.
    ts = sorted(set(np.linspace(schedule.T - 1, 0, steps).round().astype(int)), reverse=True)

    for i, t in enumerate(ts):
        t_arr = np.full(n_samples, t)
        if cond is not None and guidance_scale is not None:
            eps_c = predict_noise(net, x, t_arr, schedule.T, cond)
            null = np.tile(null_cond, (n_samples, 1))
            eps_u = predict_noise(net, x, t_arr, schedule.T, null)
            eps_hat = eps_u + guidance_scale * (eps_c - eps_u)
        else:
            eps_hat = predict_noise(net, x, t_arr, schedule.T, cond)

        abar_t = schedule.alpha_bars[t]
        x0_hat = (x - np.sqrt(1 - abar_t) * eps_hat) / np.sqrt(abar_t)     # predicted clean sample
        abar_prev = schedule.alpha_bars[ts[i + 1]] if i + 1 < len(ts) else 1.0
        x = np.sqrt(abar_prev) * x0_hat + np.sqrt(1 - abar_prev) * eps_hat  # deterministic re-noise
    return x


def ddpm_sample_full(net, schedule: DiffusionSchedule, n_samples: int, dim: int = 2, seed: int = 0):
    """The stochastic DDPM reverse process, unabridged. (Re-implemented compactly here so this
    file is a self-contained comparison; see diffusion_from_scratch.ddpm_sample for the
    conditional/guided version used elsewhere.)"""
    r = np.random.default_rng(seed)
    x = r.normal(size=(n_samples, dim))
    for t in reversed(range(schedule.T)):
        eps_hat = predict_noise(net, x, np.full(n_samples, t), schedule.T)
        alpha_t, abar_t, beta_t = schedule.alphas[t], schedule.alpha_bars[t], schedule.betas[t]
        mean = (x - (beta_t / np.sqrt(1 - abar_t)) * eps_hat) / np.sqrt(alpha_t)
        x = mean + np.sqrt(beta_t) * r.normal(size=x.shape) if t > 0 else mean
    return x


def mean_pairwise_distance(points: np.ndarray) -> float:
    d2 = ((points[:, None, :] - points[None, :, :]) ** 2).sum(-1)
    iu = np.triu_indices(len(points), k=1)
    return float(np.sqrt(d2[iu]).mean())


def section(title: str) -> None:
    print("\n" + "=" * 74 + f"\n{title}\n" + "=" * 74)


def demo():
    # ------------------------------------------------------------------- #
    # Rebuild the same dataset and train the same two models as script 1  #
    # (kept self-contained so this file runs standalone).                 #
    # ------------------------------------------------------------------- #
    N = 1200
    X_raw, y = make_moons(N, noise=0.08, r=rng)
    X, _, _ = standardize(X_raw)
    schedule = DiffusionSchedule(T=200, beta_start=1e-4, beta_end=0.05)

    section("SETUP -- training the unconditional and conditional denoisers")
    print("  (same architecture and data as diffusion_from_scratch.py; ~5-10s)")
    uncond_net, _ = train_denoiser(X, schedule, iters=3000, batch_size=256, lr=2e-3, seed=1)

    cond = np.zeros((len(X), 2))
    cond[y == 0, 0], cond[y == 1, 1] = 1.0, 1.0
    null_cond = np.zeros(2)
    cond_net, _ = train_denoiser(X, schedule, cond=cond, null_cond=null_cond, p_uncond=0.15,
                                  iters=3000, batch_size=256, lr=2e-3, seed=2)
    print("  done training.")

    # ------------------------------------------------------------------- #
    # Q1: DDPM (full steps) vs. DDIM at decreasing step counts            #
    # ------------------------------------------------------------------- #
    section("Q1. STEPS VS. QUALITY -- DDPM (full schedule) vs. DDIM (fewer steps)")
    n_gen = 500
    print(f"  {'sampler':<18} {'steps':>6} {'net evals':>10} {'wall time (s)':>14} "
          f"{'precision':>10} {'recall':>8}")

    t0 = time.perf_counter()
    ddpm_full = ddpm_sample_full(uncond_net, schedule, n_gen, seed=7)
    dt = time.perf_counter() - t0
    p, rcl = precision_recall_proxy(ddpm_full, X)
    print(f"  {'DDPM (full)':<18} {schedule.T:>6} {schedule.T:>10} {dt:>14.3f} {p:>10.4f} {rcl:>8.4f}")

    for steps in (100, 50, 20, 10, 5):
        t0 = time.perf_counter()
        gen = ddim_sample(uncond_net, schedule, n_gen, steps=steps, seed=7)
        dt = time.perf_counter() - t0
        p, rcl = precision_recall_proxy(gen, X)
        print(f"  {'DDIM':<18} {steps:>6} {steps:>10} {dt:>14.3f} {p:>10.4f} {rcl:>8.4f}")

    print("\n  Read this as: DDIM at 20-50 steps should land within shouting distance of DDPM's")
    print("  200-step precision/recall, using 4-10x fewer network evaluations. Below ~10 steps,")
    print("  quality visibly degrades -- there just isn't enough resolution left in the schedule")
    print("  to refine detail. This is the exact trade-off a product makes when it offers a")
    print("  'fast' vs. 'quality' generation mode.")
    print("\n  DDIM @ 10 steps, ASCII check (compare to script 1's DDPM output):")
    gen10 = ddim_sample(uncond_net, schedule, n_gen, steps=10, seed=7)
    print(ascii_scatter(gen10, width=48, height=14))

    # ------------------------------------------------------------------- #
    # Q2: classifier-free guidance scale sweep                           #
    # ------------------------------------------------------------------- #
    section("Q2. GUIDANCE SCALE -- fidelity up, diversity down, then artifacts")
    centroid0, centroid1 = X[y == 0].mean(0), X[y == 1].mean(0)

    def classify_by_centroid(points):
        d0 = np.linalg.norm(points - centroid0, axis=1)
        d1 = np.linalg.norm(points - centroid1, axis=1)
        return (d1 < d0).astype(int)

    real_diversity = mean_pairwise_distance(X[y == 0])
    print(f"  reference: mean pairwise distance WITHIN real class-0 data = {real_diversity:.4f}")
    print(f"\n  {'guidance w':>10} {'class fidelity':>15} {'diversity (mean pair dist)':>28} {'note':>18}")

    n_per_class = 200
    prev_div = None
    for w in (0.0, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0):
        c = np.tile(np.array([1.0, 0.0]), (n_per_class, 1))    # always request class 0
        gen = ddim_sample(cond_net, schedule, n_per_class, steps=50, cond=c,
                           guidance_scale=w, null_cond=null_cond, seed=99)
        pred = classify_by_centroid(gen)
        fidelity = float((pred == 0).mean())
        diversity = mean_pairwise_distance(gen)
        if w == 0.0:
            note = "no conditioning"
        elif prev_div is not None and diversity < prev_div * 0.6:
            note = "collapsing"
        elif fidelity > 0.97 and diversity < real_diversity * 0.5:
            note = "over-guided"
        else:
            note = ""
        print(f"  {w:>10.1f} {fidelity:>15.0%} {diversity:>28.4f} {note:>18}")
        prev_div = diversity

    print("\n  Read this as: w=0 ignores the class condition (fidelity near chance, diversity")
    print("  matches the unconditional spread). Fidelity climbs fast and saturates near 100% by")
    print("  w~4-8. Push further and fidelity has nowhere left to go, but diversity keeps")
    print("  shrinking -- the model is squeezing samples toward an ever-narrower region of the")
    print("  class-0 manifold. That squeeze is the numeric signature of the 'oversaturated,")
    print("  over-cooked' look you get from cranking guidance scale on a real text-to-image model.")


if __name__ == "__main__":
    demo()
