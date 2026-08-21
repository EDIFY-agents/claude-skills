# Benchmarks

**Same model. Same repo. Same task.**

---

> ### Status: in progress
>
> **Methodology and results will be public, including the runs where EDIFY loses.**
>
> The table below is the shape of the answer, not the answer. It is published
> empty on purpose: a benchmark table filled in before the benchmark ran is the
> single fastest way to lose a technical audience, and we would rather ship this
> page honest than ship it impressive.

| metric | agent alone | Spec Kit | EDIFY |
|---|---|---|---|
| tasks passed | — | — | — |
| human interventions | — | — | — |
| retries | — | — | — |
| tokens / cost | — | — | — |
| total time | — | — | — |

## What the comparison has to be

The comparison that matters is **not** against a strawman. It is against a
modern, well-configured agent with a good prompt, and against a free alternative
that people actually use.

- **Agent alone** — the same model, in auto mode, with a good prompt and no
  harness. This is the baseline that matters, because it is what the reader is
  doing today.
- **[Spec Kit](https://github.com/github/spec-kit)** — the closest free
  alternative in the same shape.
- **EDIFY** — `/spec → /plan → /tasks → /build → /verify` with the graph.

If EDIFY does not beat the agent alone, the product does not have a reason to
exist, and the benchmark should say so.

## The minimum credible package

1. **2–3 non-trivial OSS repositories.** Real history, real mess, more than one
   language.
2. **10–20 varied tasks.** Feature work, a refactor, a bug with a wrong first
   hypothesis, a change that touches migrations.
3. **The same model version, the same opening prompt, comparable limits** across
   all three arms.
4. **Clear baselines**: agent alone, Spec Kit, EDIFY.
5. **Measured**: task success, tests passing, human interventions, retries,
   tokens and cost, wall-clock time.
6. **Scripts, prompts, and raw results published** in this repository.
7. **A short video of a visible failure case** — the runs that go wrong are the
   ones that make the rest believable.

## Reproducing it

When the runs land, everything needed to re-run them will be in `benchmarks/`:
task definitions, the exact prompts, the harness scripts, and the raw
transcripts.

**Got a different result?** That is a defect in our claim and we want it filed:
[benchmark reproduction template](../.github/ISSUE_TEMPLATE/benchmark_reproduction.yml).

## Known limitations, before you ask

Stated here rather than discovered later:

- The graph parses Python exactly and **scans** everything else unless Universal
  Ctags is installed. Precision beyond Python is good, not exact.
- A language the extractor does not cover has **no nodes at all** — visible in
  `edify graph stat`, never silently guessed.
- EDIFY is **not for a solo developer on a small project.** A frontier model in
  auto mode is already excellent there. The value starts where the codebase stops
  fitting in the context window, and a benchmark on a toy repo will show exactly
  that.
- Nothing here makes a weak model competent. It makes a competent model
  efficient, and the difference is the whole product.

## Help us build it

Benchmark methodology is the best thing to argue about in
[Discussions](https://github.com/EDIFY-agents/edify_public/discussions) right now — before the runs, while the argument
can still change the design.
