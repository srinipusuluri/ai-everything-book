"""
PyTorch in one file — the training loop you will write a thousand times.

Covers: Dataset/DataLoader, nn.Module, the loop, validation, LR scheduling,
early stopping, checkpointing, gradient clipping, and the "overfit 10 examples"
smoke test. Runs on CPU in well under a minute; no download required.

    python code/pytorch_training_loop.py

Requires: torch  (pip install torch)
If torch is missing the script explains what it would have done and exits 0.
"""
from __future__ import annotations

import math
import sys
import tempfile
from pathlib import Path

try:
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader, Dataset, random_split
except ModuleNotFoundError:
    print(__doc__)
    print("!! torch is not installed. `pip install torch`, then re-run.")
    print("   Read the file anyway — it is annotated as a reference.")
    sys.exit(0)

SEED = 1234
torch.manual_seed(SEED)
DEVICE = ("cuda" if torch.cuda.is_available()
          else "mps" if torch.backends.mps.is_available() else "cpu")


# --------------------------------------------------------------------------- #
# 1. Data — a Dataset is just __len__ and __getitem__                          #
# --------------------------------------------------------------------------- #
class SpiralDataset(Dataset):
    """Three interleaved spirals: not linearly separable, easy to visualise mentally."""

    def __init__(self, points_per_class: int = 600, classes: int = 3, noise: float = 0.18):
        g = torch.Generator().manual_seed(SEED)
        xs, ys = [], []
        for c in range(classes):
            r = torch.linspace(0.0, 1.0, points_per_class)
            t = (torch.linspace(c * 4, (c + 1) * 4, points_per_class)
                 + torch.randn(points_per_class, generator=g) * noise)
            xs.append(torch.stack([r * torch.sin(t), r * torch.cos(t)], dim=1))
            ys.append(torch.full((points_per_class,), c, dtype=torch.long))
        self.x = torch.cat(xs).float()
        self.y = torch.cat(ys)

    def __len__(self) -> int:
        return len(self.y)

    def __getitem__(self, i: int):
        return self.x[i], self.y[i]


# --------------------------------------------------------------------------- #
# 2. Model — nn.Module: define layers in __init__, wire them in forward        #
# --------------------------------------------------------------------------- #
class MLP(nn.Module):
    def __init__(self, in_dim=2, hidden=64, out_dim=3, depth=3, p_drop=0.1):
        super().__init__()
        layers: list[nn.Module] = []
        d = in_dim
        for _ in range(depth):
            layers += [
                nn.Linear(d, hidden),
                nn.LayerNorm(hidden),   # LayerNorm, not BatchNorm: batch-size independent
                nn.GELU(),              # what transformers use
                nn.Dropout(p_drop),     # active in .train(), disabled in .eval()
            ]
            d = hidden
        layers.append(nn.Linear(d, out_dim))   # raw LOGITS: no softmax here
        self.net = nn.Sequential(*layers)

    def forward(self, x):
        return self.net(x)


# --------------------------------------------------------------------------- #
# 3. The smoke test that saves you days                                        #
# --------------------------------------------------------------------------- #
def overfit_smoke_test(model_fn, x, y, steps: int = 300) -> bool:
    """If a model cannot drive 10 examples to ~zero loss, the bug is in the CODE."""
    m = model_fn().to(DEVICE)
    m.train()
    opt = torch.optim.AdamW(m.parameters(), lr=1e-2)
    crit = nn.CrossEntropyLoss()
    xb, yb = x[:10].to(DEVICE), y[:10].to(DEVICE)
    loss = math.inf
    for _ in range(steps):
        opt.zero_grad(set_to_none=True)
        loss_t = crit(m(xb), yb)
        loss_t.backward()
        opt.step()
        loss = loss_t.item()
    print(f"  overfit-10 final loss = {loss:.6f}  ->  {'PASS' if loss < 0.01 else 'FAIL — debug the code, not the LR'}")
    return loss < 0.01


# --------------------------------------------------------------------------- #
# 4. Train / evaluate                                                          #
# --------------------------------------------------------------------------- #
@torch.no_grad()                 # no autograd graph at eval: faster, less memory
def evaluate(model, loader, crit):
    model.eval()                 # <- disables dropout, freezes norm statistics
    total_loss, correct, n = 0.0, 0, 0
    for xb, yb in loader:
        xb, yb = xb.to(DEVICE), yb.to(DEVICE)
        out = model(xb)
        total_loss += crit(out, yb).item() * len(yb)
        correct += (out.argmax(1) == yb).sum().item()
        n += len(yb)
    return total_loss / n, correct / n


def train(model, train_loader, val_loader, *, epochs=40, lr=3e-3,
          weight_decay=0.01, patience=8, clip=1.0):
    model = model.to(DEVICE)
    crit = nn.CrossEntropyLoss(label_smoothing=0.05)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)

    # Warmup + cosine decay: the canonical schedule, borrowed straight from LLM training.
    steps_per_epoch = len(train_loader)
    total_steps = epochs * steps_per_epoch
    warmup = max(1, int(0.05 * total_steps))

    def lr_lambda(step):
        if step < warmup:
            return step / warmup
        prog = (step - warmup) / max(1, total_steps - warmup)
        return 0.1 + 0.9 * 0.5 * (1 + math.cos(math.pi * prog))

    sched = torch.optim.lr_scheduler.LambdaLR(opt, lr_lambda)

    ckpt = Path(tempfile.gettempdir()) / "dl_module02_best.pt"
    best_val, bad_epochs, history = math.inf, 0, []

    for ep in range(epochs):
        model.train()                       # <- dropout ON
        run_loss, seen, gnorm = 0.0, 0, 0.0
        for xb, yb in train_loader:
            xb, yb = xb.to(DEVICE), yb.to(DEVICE)
            opt.zero_grad(set_to_none=True) # 1. clear stale gradients
            out = model(xb)                 # 2. forward
            loss = crit(out, yb)            # 3. loss
            loss.backward()                 # 4. backward
            gnorm = nn.utils.clip_grad_norm_(model.parameters(), clip).item()  # 5. clip
            opt.step()                      # 6. update
            sched.step()                    # 7. LR schedule
            run_loss += loss.item() * len(yb)
            seen += len(yb)

        tr_loss = run_loss / seen
        val_loss, val_acc = evaluate(model, val_loader, crit)
        history.append((tr_loss, val_loss, val_acc))

        if ep % 5 == 0 or ep == epochs - 1:
            print(f"  epoch {ep:>3}  train={tr_loss:.4f}  val={val_loss:.4f}  "
                  f"acc={val_acc:.4f}  lr={sched.get_last_lr()[0]:.2e}  |g|={gnorm:.2f}")

        # Checkpoint the BEST model, not the last one.
        if val_loss < best_val - 1e-4:
            best_val, bad_epochs = val_loss, 0
            torch.save({"model": model.state_dict(), "optimizer": opt.state_dict(),
                        "scheduler": sched.state_dict(), "epoch": ep,
                        "val_loss": val_loss}, ckpt)
        else:
            bad_epochs += 1
            if bad_epochs >= patience:
                print(f"  early stop at epoch {ep} (no improvement for {patience} epochs)")
                break

    model.load_state_dict(torch.load(ckpt, map_location=DEVICE)["model"])
    print(f"  restored best checkpoint (val loss {best_val:.4f}) from {ckpt}")
    return model, history


# --------------------------------------------------------------------------- #
# 5. Ablations — see the concepts, don't just read them                        #
# --------------------------------------------------------------------------- #
def ablation(train_loader, val_loader, label, **kw):
    torch.manual_seed(SEED)
    model = MLP(**{k: v for k, v in kw.items() if k in {"hidden", "depth", "p_drop"}})
    crit = nn.CrossEntropyLoss()
    opt = torch.optim.AdamW(model.parameters(), lr=kw.get("lr", 3e-3))
    model.to(DEVICE)
    for _ in range(kw.get("epochs", 25)):
        model.train()
        for xb, yb in train_loader:
            xb, yb = xb.to(DEVICE), yb.to(DEVICE)
            opt.zero_grad(set_to_none=True)
            loss = crit(model(xb), yb)
            loss.backward()
            opt.step()
    vl, va = evaluate(model, val_loader, crit)
    flag = "" if math.isfinite(vl) else "  <- diverged"
    print(f"  {label:<34} val_loss={vl:8.4f}  val_acc={va:.4f}{flag}")


def main() -> None:
    print(f"device = {DEVICE}\n")
    ds = SpiralDataset()
    n_val = int(0.2 * len(ds))
    tr, va = random_split(ds, [len(ds) - n_val, n_val],
                          generator=torch.Generator().manual_seed(SEED))
    train_loader = DataLoader(tr, batch_size=64, shuffle=True, drop_last=False)
    val_loader = DataLoader(va, batch_size=256, shuffle=False)

    print("=" * 70)
    print("STEP 0 — SMOKE TEST (always do this first)")
    print("=" * 70)
    overfit_smoke_test(lambda: MLP(p_drop=0.0), ds.x, ds.y)
    logits0 = MLP()(ds.x[:512])
    l0 = nn.CrossEntropyLoss()(logits0, ds.y[:512]).item()
    print(f"  loss at init = {l0:.4f}   (theory: ln(3) = {math.log(3):.4f})  "
          f"-> {'sane' if abs(l0 - math.log(3)) < 0.25 else 'SUSPICIOUS: check your output layer'}")

    print()
    print("=" * 70)
    print("STEP 1 — TRAIN")
    print("=" * 70)
    model, hist = train(MLP(), train_loader, val_loader)
    crit = nn.CrossEntropyLoss()
    vl, vacc = evaluate(model, val_loader, crit)
    print(f"  final: val_loss={vl:.4f}  val_acc={vacc:.4f}")

    print()
    print("=" * 70)
    print("STEP 2 — ABLATIONS (25 epochs each, same seed)")
    print("=" * 70)
    ablation(train_loader, val_loader, "depth=1 hidden=8 (underfit)", depth=1, hidden=8)
    ablation(train_loader, val_loader, "depth=3 hidden=64 (baseline)", depth=3, hidden=64)
    ablation(train_loader, val_loader, "depth=3 hidden=64 dropout=0.5", depth=3, hidden=64, p_drop=0.5)
    ablation(train_loader, val_loader, "lr=1e-5 (too small)", lr=1e-5)
    ablation(train_loader, val_loader, "lr=3.0  (too large)", lr=3.0)

    print()
    print("=" * 70)
    print("STEP 3 — WHAT model.eval() ACTUALLY CHANGES")
    print("=" * 70)
    x = ds.x[:8].to(DEVICE)
    model.train()
    a, b = model(x), model(x)
    print(f"  train mode: two forward passes identical? {torch.allclose(a, b)}   (dropout is stochastic)")
    model.eval()
    with torch.no_grad():
        c, d = model(x), model(x)
    print(f"  eval  mode: two forward passes identical? {torch.allclose(c, d)}   (this is why you call .eval())")
    print("\nForgetting model.eval() during validation is the single most common")
    print("PyTorch bug. Your metrics become noise and you chase the wrong problem.\n")


if __name__ == "__main__":
    main()
