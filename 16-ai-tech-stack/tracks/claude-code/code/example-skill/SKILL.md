---
name: leakage-check
description: Audits a diff or a named file for data-leakage and reproducibility bugs in ML feature or training code. Use when the user asks to review ML changes, mentions feature engineering, train/test splits, seeds, or asks "is this leaking?".
when_to_use: Invoke before merging anything under a feature-engineering, dataset, or training directory. Trigger phrases: "review my features", "check for leakage", "is this split honest", "audit this training script".
argument-hint: [file-or-directory]
allowed-tools: Read, Grep, Glob
disallowed-tools: Write, Edit
---

## Changes under review

!`git diff HEAD --stat`

## Scope

Audit `$ARGUMENTS` if given; otherwise audit the changed files shown above. Read only — do not edit anything.

## Checks

Work through these in order. For each finding, report `file:line`, the mechanism, and the concrete fix.

1. **Temporal leakage.** Any feature computed from a row whose timestamp is >= the prediction timestamp.
   Look for joins, rolling windows, groupby aggregations and `shift()` calls with no time bound.
2. **Fit-before-split.** Scalers, imputers, encoders or vocabularies fitted on the full dataset rather than
   inside the training fold. Grep for `fit(` / `fit_transform(` outside a `Pipeline` or a CV loop.
3. **Target-derived features.** Any column computed from, or only knowable after, the label.
   Names containing `_reason`, `_outcome`, `closed_`, `final_` deserve a second look.
4. **Split integrity.** Random splits on time-ordered data; rows sharing an entity (user, patient, session)
   landing on both sides; duplicate rows spanning the split.
5. **Non-determinism.** Seeds not set, or set per-library rather than through one helper; `set()` or `dict`
   iteration order feeding into data order; `num_workers > 0` without a worker seed.
6. **Test-set contamination.** The test set read more than once, or used for early stopping or threshold tuning.

## Output

- If clean: one line saying so, plus the highest-risk area you would watch next.
- Otherwise: a markdown table `severity | file:line | mechanism | fix`, ordered high to low severity.
- End with one sentence: what would have to be true for this code to be safe.

Never modify files. Report only.
