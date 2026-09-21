# 📄 Primary Sources — Python for AI Engineering

Python's "papers" are mostly **PEPs** (Python Enhancement Proposals) and official docs. That is a feature:
the design rationale for every language decision is written down, public, and usually readable. When you want
to know *why* something works the way it does, the PEP will tell you in the "Rationale" and "Rejected Ideas"
sections — which are frequently the most educational part.

## Read these three first

| # | Source | Why it matters | Link |
|---|--------|----------------|------|
| 1 | **Array programming with NumPy** — Harris et al., *Nature* 583 (2020) | The design paper for the array model that PyTorch, JAX, polars and every vector DB inherited. Explains broadcasting, strides and views as deliberate choices, not accidents. | [Nature](https://www.nature.com/articles/s41586-020-2649-2) |
| 2 | **PEP 703 — Making the GIL Optional in CPython** — Sam Gross (2023) | The single best explanation of what the GIL actually protects, what breaks without it, and what the performance trade is. Accepted; free-threaded builds followed in 3.13/3.14. | [peps.python.org/pep-0703](https://peps.python.org/pep-0703/) |
| 3 | **Exponential Backoff and Jitter** — Marc Brooker, AWS Architecture Blog (2015) | Measures the retry strategies against each other and shows why the jitter — not the exponent — is what prevents congestion collapse. Nine minutes; changes how you write every client. | [aws.amazon.com](https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/) |

## PEPs that shaped the Python you write today

| PEP | Title | Why you care |
|---|---|---|
| [8](https://peps.python.org/pep-0008/) | Style Guide for Python Code | Ruff enforces most of it. Read it once so you know what you're being told. |
| [20](https://peps.python.org/pep-0020/) | The Zen of Python | 19 aphorisms. "Explicit is better than implicit" is the one you'll cite in review. |
| [484](https://peps.python.org/pep-0484/) | Type Hints | The original. Note §"Non-goals": hints are **not** enforced at runtime, by design. |
| [544](https://peps.python.org/pep-0544/) | Protocols: Structural Subtyping | How you type "an LLM client" without inheriting from a vendor's base class. |
| [557](https://peps.python.org/pep-0557/) | Data Classes | Why `@dataclass` exists and where it deliberately stops (hint: validation). |
| [589](https://peps.python.org/pep-0589/) | TypedDict | Type a JSON payload with zero runtime cost. |
| [492](https://peps.python.org/pep-0492/) | Coroutines with async and await | The syntax's rationale. Read the "why not just generators" section. |
| [654](https://peps.python.org/pep-0654/) | Exception Groups and `except*` | The machinery under `asyncio.TaskGroup`. |
| [517](https://peps.python.org/pep-0517/) / [518](https://peps.python.org/pep-0518/) | Build backends / build requirements | Why `pyproject.toml` exists and `setup.py` doesn't need to. |
| [621](https://peps.python.org/pep-0621/) | Project metadata in pyproject.toml | The `[project]` table you now write in every repo. |
| [649](https://peps.python.org/pep-0649/) | Deferred evaluation of annotations | Adopted in 3.14; changes what `from __future__ import annotations` was for. |
| [659](https://peps.python.org/pep-0659/) | Specializing Adaptive Interpreter | The core of the 3.11+ speedups. Explains why "Python is slow" is a moving target. |
| [703](https://peps.python.org/pep-0703/) | Making the GIL optional | See above. The most consequential PEP of the decade. |
| [744](https://peps.python.org/pep-0744/) | JIT Compilation | CPython's copy-and-patch JIT. Where the runtime is heading. |

Full index: https://peps.python.org/

## Official documentation worth reading rather than searching

| Topic | Link | Read specifically |
|---|---|---|
| Broadcasting | https://numpy.org/doc/stable/user/basics.broadcasting.html | the rules table; then the "general broadcasting rules" examples |
| NumPy copies vs views | https://numpy.org/doc/stable/user/basics.copies.html | when a slice shares memory — and silently mutates your source |
| asyncio | https://docs.python.org/3/library/asyncio.html | `gather`, `TaskGroup`, `timeout`, `to_thread`, and the "Developing with asyncio" page |
| Floating point | https://docs.python.org/3/tutorial/floatingpoint.html | 15 minutes; explains every "why is this 0.30000000000000004" you'll ever hit |
| `pickle` | https://docs.python.org/3/library/pickle.html | the security warning at the top. It means what it says. |
| `functools` | https://docs.python.org/3/library/functools.html | `cache`, `lru_cache`, `partial`, `singledispatch` |
| `itertools` | https://docs.python.org/3/library/itertools.html | the recipes section at the bottom is the real content |
| Packaging | https://packaging.python.org/ | "Packaging Python Projects" tutorial, then the src-layout discussion |
| uv | https://docs.astral.sh/uv/ | "Projects" and "Locking and syncing" |
| ruff | https://docs.astral.sh/ruff/ | the rules index — skim it once and you learn Python bugs you didn't know existed |
| Pydantic v2 | https://docs.pydantic.dev/latest/ | "Models", "Validators", "JSON Schema", and the v1→v2 migration guide |
| mypy | https://mypy.readthedocs.io/ | "Existing code" — how to add types to a codebase without stopping work |
| pyright | https://microsoft.github.io/pyright/ | the configuration reference; strictness levels |
| pytest | https://docs.pytest.org/ | fixtures, parametrize, markers. In that order. |
| httpx | https://www.python-httpx.org/ | "Async Support" and "Timeouts" |
| polars | https://docs.pola.rs/ | the lazy API and "Coming from pandas" |
| free-threading | https://py-free-threading.github.io/ | current status, compatibility tracking for the libraries you use |
| safetensors | https://huggingface.co/docs/safetensors/index | the format that exists because pickle is unsafe |

## Essays and talks worth an hour

| Source | Takeaway |
|---|---|
| **What Every Computer Scientist Should Know About Floating-Point Arithmetic** — Goldberg (1991) — [Oracle mirror](https://docs.oracle.com/cd/E19957-01/806-3568/ncg_goldberg.html) | Dense, canonical. Read §1 and the "rounding error" section; skim the rest. Explains why your embedding similarities differ across machines. |
| **SciPy 1.0: fundamental algorithms for scientific computing in Python** — Virtanen et al., *Nature Methods* (2020) — [Nature](https://www.nature.com/articles/s41592-019-0686-2) | How the scientific Python stack was actually built and governed. Useful context for why the ecosystem has the shape it does. |
| **Apache Arrow** — [arrow.apache.org](https://arrow.apache.org/) | The columnar memory format underneath polars, DuckDB, and modern pandas. Zero-copy interchange is why you can mix them freely. |
| **Fluent Python, 2nd ed.** — Luciano Ramalho — [fluentpython.com](https://www.fluentpython.com/) | Not free, but the book that turns a competent programmer into a Python programmer. Chapters on data model, iterators and concurrency are the relevant ones here. |
| **Hidden Technical Debt in Machine Learning Systems** — Sculley et al., NeurIPS 2015 — [PDF](https://proceedings.neurips.cc/paper_files/paper/2015/file/86df7dcfd896fcaf2674f757a2463eba-Paper.pdf) | Not a Python paper, but the reason this track exists: the model is 5% of the system. The other 95% is the code you are learning to write well. |

## How to read a PEP in 15 minutes

1. **Abstract + Motivation (3 min).** What problem, and who had it?
2. **Rationale and Rejected Ideas (7 min).** This is the valuable part. The alternatives explain the
   constraints, and the constraints explain the design.
3. **Backwards Compatibility (3 min).** What breaks. In a language this old, this section is why half the
   design decisions look odd.
4. **Skip the reference implementation** unless you're contributing.

Keep a one-line note per PEP. "PEP 544: Protocols = structural typing, no inheritance needed" is worth more
in six months than the tab you left open.
