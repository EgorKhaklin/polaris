# docs/paper/ — academic write-up

The formal academic write-up of Polaris, in LaTeX + rendered PDF.
Submitted as the SCS-230 capstone project; intended-readership is
academic + technical reviewers.

---

## What's here

| File | Purpose |
|---|---|
| [`polaris_project_report.tex`](polaris_project_report.tex) | LaTeX source — edit this; render with `pdflatex` |
| `polaris_project_report.pdf` | Rendered output — NOT edited by hand |

---

## Building

```bash
cd docs/paper
pdflatex polaris_project_report.tex
# Run twice if cross-references change.
```

---

## What this directory is NOT

- Not the operator runbook (that's in [`../operator/`](../operator/))
- Not the technical reference (that's in [`../reference/`](../reference/))
- Not the narrative (that's in [`../story/`](../story/))
- Not informal developer notes (that's in [`../../DEVNOTES/`](../../DEVNOTES/))

`docs/paper/` is **the artifact submitted for academic review** —
self-contained, citation-ready, no external dependencies for
reading.
