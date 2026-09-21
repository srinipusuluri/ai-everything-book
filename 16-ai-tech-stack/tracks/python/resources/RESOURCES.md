# 🔗 Resources — Python for AI Engineering

## Courses and structured learning (free unless noted)

| Resource | Who it's for | Link |
|---|---|---|
| **Official Python Tutorial** | You know another language and want the syntax in 4 hours | https://docs.python.org/3/tutorial/ |
| **Real Python** | The best written explanations of specific topics; search it before Stack Overflow | https://realpython.com/ |
| **CS50P — Introduction to Programming with Python** (Harvard, free) | A genuinely good first course if Python is your first language | https://cs50.harvard.edu/python/ |
| **Python for Data Analysis, 3rd ed.** — Wes McKinney (free online) | pandas from the person who wrote pandas | https://wesmckinney.com/book/ |
| **Scientific Python Lectures** | NumPy/SciPy/matplotlib, notebook-style, maintained | https://lectures.scientific-python.org/ |
| **NumPy "Absolute Basics" + "NumPy for MATLAB users"** | Fastest route to the array model | https://numpy.org/doc/stable/user/absolute_beginners.html |
| **Async IO in Python: A Complete Walkthrough** (Real Python) | The clearest asyncio explainer in existence | https://realpython.com/async-io-python/ |
| **Talk Python To Me** (podcast) | Keeping up with the ecosystem passively | https://talkpython.fm/ |

## The toolchain — bookmark these

| Tool | What it replaces | Link |
|---|---|---|
| **uv** | pip, venv, virtualenv, pyenv, pip-tools, poetry | https://docs.astral.sh/uv/ |
| **ruff** | flake8, isort, black, pyupgrade, pydocstyle, autoflake | https://docs.astral.sh/ruff/ |
| **ty** (Astral's type checker, early) | eventually some mypy usage — watch this space | https://github.com/astral-sh/ty |
| **mypy** | — | https://mypy.readthedocs.io/ |
| **pyright / Pylance** | — | https://microsoft.github.io/pyright/ |
| **pytest** | unittest | https://docs.pytest.org/ |
| **pre-commit** | your willpower | https://pre-commit.com/ |
| **py-spy** | guessing why prod is slow | https://github.com/benfred/py-spy |
| **memray** | guessing why prod is out of memory | https://github.com/bloomberg/memray |
| **hatch / hatchling** | setuptools | https://hatch.pypa.io/ |

## Libraries that matter for AI work

| Library | What it's for | Link |
|---|---|---|
| **pydantic** | validation, settings, JSON Schema for tool calling | https://docs.pydantic.dev/latest/ |
| **httpx** | async HTTP with a requests-shaped API | https://www.python-httpx.org/ |
| **tenacity** | retry/backoff as a decorator, if you don't want to hand-roll it | https://github.com/jd/tenacity |
| **anyio** | asyncio/trio-agnostic structured concurrency | https://anyio.readthedocs.io/ |
| **FastAPI** | the Pydantic-native web framework | https://fastapi.tiangolo.com/ |
| **polars** | the fast dataframe | https://pola.rs/ |
| **pandas** | the compatible dataframe | https://pandas.pydata.org/docs/ |
| **DuckDB** | SQL over Parquet/Arrow, in-process, spills to disk | https://duckdb.org/ |
| **NumPy** | the array | https://numpy.org/doc/stable/ |
| **numba** | `@njit` your numeric loops | https://numba.readthedocs.io/ |
| **structlog** | structured logging that's pleasant to use | https://www.structlog.org/ |
| **rich** | terminal output humans enjoy reading | https://github.com/Textualize/rich |
| **typer** | CLIs from type hints | https://typer.tiangolo.com/ |
| **syrupy** | snapshot testing for pytest | https://github.com/syrupy-project/syrupy |
| **hypothesis** | property-based testing; brutal at finding edge cases | https://hypothesis.readthedocs.io/ |
| **safetensors** | model weights without pickle's arbitrary-code problem | https://github.com/huggingface/safetensors |
| **PyO3** | if you end up writing the Rust half | https://pyo3.rs/ |

## Repositories worth reading (not just cloning)

| Repo | Read it for |
|---|---|
| https://github.com/pydantic/pydantic | How a Rust core is wrapped in an ergonomic Python API. Start with `main/pydantic/main.py`. |
| https://github.com/encode/httpx | Clean async client design: pools, timeouts, transports. The `_transports/` directory is a masterclass. |
| https://github.com/astral-sh/uv | Why it's fast. Even if you don't read Rust, the README's design notes are worth it. |
| https://github.com/anthropics/anthropic-sdk-python | A production LLM client: retries, streaming, typed responses, pagination. |
| https://github.com/tiangolo/fastapi | How type hints become an API contract and OpenAPI docs. |
| https://github.com/numpy/numpy | `numpy/_core/src/multiarray/` if you want to see what broadcasting actually does. |
| https://github.com/pola-rs/polars | The lazy query optimiser in `crates/polars-plan/`. |
| https://github.com/psf/requests | Small enough to read end to end; the API design that everything else copied. |

## Cheat sheets and references

- Python 3 standard library by example: https://pymotw.com/3/
- Ruff rule index (skim once, learn 20 real bugs): https://docs.astral.sh/ruff/rules/
- NumPy broadcasting rules: https://numpy.org/doc/stable/user/basics.broadcasting.html
- asyncio API index: https://docs.python.org/3/library/asyncio-api-index.html
- typing module reference: https://docs.python.org/3/library/typing.html
- Python version release notes (what's new in each): https://docs.python.org/3/whatsnew/
- Also see [`../../../../_shared/cheatsheets/`](../../../../_shared/cheatsheets/)

## Communities

- Python Discord (large, well moderated, genuinely helpful) — https://discord.gg/python
- r/Python — https://www.reddit.com/r/Python/
- r/learnpython (ask beginner questions here, not r/Python) — https://www.reddit.com/r/learnpython/
- Python Discourse (where PEPs are debated) — https://discuss.python.org/
- Astral Discord (uv / ruff) — https://discord.gg/astral-sh
- Pydantic GitHub Discussions — https://github.com/pydantic/pydantic/discussions

## Staying current without drowning

- **Python Weekly** — https://www.pythonweekly.com/
- **PyCoder's Weekly** — https://pycoders.com/
- **What's New in Python 3.x** — the single highest-signal page per release: https://docs.python.org/3/whatsnew/
- **Astral's blog** — the toolchain changes fastest: https://astral.sh/blog

One habit worth more than all of the above: when a library surprises you, open its source. It is Python. It
is right there in your `.venv`. Reading `pydantic/main.py` or `httpx/_client.py` for twenty minutes teaches
more than an afternoon of tutorials, and it is how you stop treating your dependencies as magic.
