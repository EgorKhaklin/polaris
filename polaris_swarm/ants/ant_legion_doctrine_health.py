"""ant_legion_doctrine_health — verifies each legion's tactic still validates.

Consciousness ant. Slice: every `polaris_swarm/legions/legio_*.py`
source file. Each declares a `TacticConfig` (`Tactic.TESTUDO`,
`TRIPLEX_ACIES`, `CUNEUS`, etc.) and provides an `ANTS` cohort.

G11 contract: ants do NOT import from `polaris_swarm.legions`. To
honor this AND still surface doctrine-validation drift, the ant
reads legion source files as **text** and runs the same checks
that `TacticConfig.validate()` performs:

  - **TRIPLEX_ACIES** must declare `tiers=[...]` with ≥2 tiers
    whose flattened union exactly matches `ANTS`.
  - **CUNEUS** must declare a `lead=` ant that appears in `ANTS`.
  - Every legion must declare a `TACTIC` and an `ANTS` list.

Local rule: any structural violation = `alert` pheromone
(intensity 7.0). This is the second ALERT-capable ant in the
cohort (after `ant_self_model_accuracy`).

G18 (consciousness): reads swarm self-state via filesystem
introspection; never imports legion behavior.

G11 (ants don't import legions): preserved verbatim. This ant
parses legion DECLARATIONS as text — it never imports them.

Determinism: pure file-system + regex scan; no time, no
randomness.

Authorized by `sanctum/2026-05-13-arc-e-acceleration-consciousness-cohort-e10.md`.
"""

from __future__ import annotations

import re

from polaris_swarm.base import Ant, AntFinding, KIND_ALERT


# Match the `class LegioFoo(Legion):` header so we can scope each
# legion's TACTIC/ANTS block within the same file (one file = one
# legion in current architecture).
_LEGION_HEADER_RE = re.compile(
    r"^class\s+(Legio\w+)\s*\(\s*Legion\s*\)\s*:",
    re.MULTILINE,
)
# ANTS = [ ... ] block — handles both `[X, Y]` single-line and
# `[\n   X,\n   Y,\n]` multi-line forms. The closing `]` is matched
# as the FIRST `]` since ANTS lists contain only identifiers
# (no nested brackets).
_ANTS_BLOCK_RE = re.compile(
    r"^\s*ANTS\s*=\s*\[(.*?)\]",
    re.MULTILINE | re.DOTALL,
)
# TACTIC = TacticConfig( ... ) block — handles both single-line
# `TacticConfig(tactic=Tactic.TESTUDO)` and multi-line forms.
# The closing `)` is matched at minimal nesting; we use a
# non-greedy match plus a check for `^\s*)` to find the outer
# paren when there are nested calls (e.g., Tactic.X.value).
_TACTIC_BLOCK_RE = re.compile(
    r"^\s*TACTIC\s*=\s*TacticConfig\s*\((.*?)^\s*\)",
    re.MULTILINE | re.DOTALL,
)
# Fallback for single-line `TACTIC = TacticConfig(tactic=Tactic.X)`.
_TACTIC_INLINE_RE = re.compile(
    r"^\s*TACTIC\s*=\s*TacticConfig\s*\((.*?)\)\s*$",
    re.MULTILINE,
)
_TACTIC_NAME_RE = re.compile(r"tactic\s*=\s*Tactic\.(\w+)")
_LEAD_NAME_RE   = re.compile(r"lead\s*=\s*(\w+)")
# Tiers are nested lists inside the outer `tiers=[...]` list. Regex
# alone cannot reliably match balanced brackets when tiers span
# multiple lines (the v8.69 attempt used `(?:^\s+\])` which stopped
# at the closing bracket of T2's multi-line list, miscounting
# 3 tiers as 1 — caught as a false ALERT in v8.76 and fixed here).
# The helper `_extract_tiers_body` does explicit bracket counting,
# which is robust to any nesting depth.
_TIERS_HEAD_RE = re.compile(r"tiers\s*=\s*\[")
# Identifiers — class names referenced in ANTS/tiers/lead.
_IDENT_RE = re.compile(r"\b(Ant\w+)\b")


def _extract_tiers_body(tactic_body: str) -> str | None:
    """Return the body inside the OUTER brackets of `tiers=[ ... ]`,
    handling arbitrary nesting via explicit bracket counting.
    Returns None if `tiers=` is absent or brackets are unbalanced.

    Strings + comments inside the source could in principle contain
    bracket characters that throw off naive counting. In legion
    files the tiers= block is canonical Python list-of-lists with
    only identifiers + commas + newlines + comments inside, so the
    naive count is safe. If a future legion uses string literals
    inside tiers= (which would be a separate problem), this helper
    would need a tokenizer.
    """
    m = _TIERS_HEAD_RE.search(tactic_body)
    if not m:
        return None
    start = m.end()  # position right after the outer `[`
    depth = 1
    i = start
    while i < len(tactic_body) and depth > 0:
        ch = tactic_body[i]
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
        i += 1
    if depth != 0:
        return None  # unbalanced; caller will treat as missing
    return tactic_body[start:i - 1]


def _strip_comments(text: str) -> str:
    """Remove `# ...` end-of-line comments for clean identifier
    parsing."""
    return re.sub(r"#.*", "", text)


def _identifiers_in(block: str) -> list[str]:
    """Return CamelCase identifiers starting with `Ant` from a
    code block."""
    block = _strip_comments(block)
    return _IDENT_RE.findall(block)


class AntLegionDoctrineHealth(Ant):
    NAME = "ant_legion_doctrine_health"
    DESCRIPTION = "Pheromones (ALERT) when a legion's TacticConfig fails to validate."

    def scan(self) -> list[AntFinding]:
        findings: list[AntFinding] = []
        legions_dir = self.root / "polaris_swarm" / "legions"
        if not legions_dir.is_dir():
            return findings
        for path in sorted(legions_dir.glob("legio_*.py")):
            try:
                body = path.read_text(errors="replace")
            except OSError:
                continue
            header = _LEGION_HEADER_RE.search(body)
            if not header:
                continue
            legion_class_name = header.group(1)
            # Pull the ANTS list
            ants_m = _ANTS_BLOCK_RE.search(body)
            if not ants_m:
                findings.append(self._alert(
                    legion_class_name,
                    "no ANTS = [...] block found",
                    "declare ANTS list on the legion class",
                ))
                continue
            ant_names = _identifiers_in(ants_m.group(1))
            cohort_set = set(ant_names)
            # Pull the TACTIC block (multi-line OR single-line)
            tactic_m = _TACTIC_BLOCK_RE.search(body) \
                or _TACTIC_INLINE_RE.search(body)
            if not tactic_m:
                findings.append(self._alert(
                    legion_class_name,
                    "no TACTIC = TacticConfig(...) block found",
                    "declare TACTIC on the legion class",
                ))
                continue
            tactic_body = tactic_m.group(1)
            tactic_name_m = _TACTIC_NAME_RE.search(tactic_body)
            if not tactic_name_m:
                findings.append(self._alert(
                    legion_class_name,
                    "TacticConfig has no tactic= keyword",
                    "set tactic=Tactic.<NAME> in TacticConfig",
                ))
                continue
            tactic_name = tactic_name_m.group(1)
            # Mirror TacticConfig.validate() rules
            if tactic_name == "TRIPLEX_ACIES":
                tiers_body = _extract_tiers_body(tactic_body)
                if tiers_body is None:
                    findings.append(self._alert(
                        legion_class_name,
                        "TRIPLEX_ACIES requires tiers=[...] declaration",
                        "add tiers=[[...], [...]] to TacticConfig",
                        tactic_name,
                    ))
                    continue
                # Parse out each tier's identifiers
                tier_idents: list[list[str]] = []
                # Match `[ ... ]` groups inside the outer block
                for tier_m in re.finditer(
                    r"\[(.*?)\]", tiers_body, re.DOTALL,
                ):
                    tier_idents.append(_identifiers_in(tier_m.group(1)))
                flat = [a for tier in tier_idents for a in tier]
                if len(tier_idents) < 2:
                    findings.append(self._alert(
                        legion_class_name,
                        f"TRIPLEX_ACIES requires ≥2 tiers; got "
                        f"{len(tier_idents)}",
                        "split the cohort into 2+ tiers",
                        tactic_name,
                    ))
                elif set(flat) != cohort_set:
                    missing = cohort_set - set(flat)
                    extra = set(flat) - cohort_set
                    findings.append(self._alert(
                        legion_class_name,
                        (
                            f"TRIPLEX_ACIES tiers do not partition the "
                            f"cohort; missing={sorted(missing)}, "
                            f"extra={sorted(extra)}"
                        ),
                        "ensure every ANTS member appears in exactly one tier",
                        tactic_name,
                    ))
            elif tactic_name == "CUNEUS":
                lead_m = _LEAD_NAME_RE.search(tactic_body)
                if not lead_m:
                    findings.append(self._alert(
                        legion_class_name,
                        "CUNEUS requires lead= declaration",
                        "set lead=<AntCls> in TacticConfig",
                        tactic_name,
                    ))
                    continue
                lead_name = lead_m.group(1)
                if lead_name not in cohort_set:
                    findings.append(self._alert(
                        legion_class_name,
                        (
                            f"CUNEUS lead {lead_name!r} is not in "
                            f"the cohort {sorted(cohort_set)}"
                        ),
                        "either add the lead to ANTS or pick a different lead",
                        tactic_name,
                    ))
        return findings

    def _alert(
        self,
        legion_name: str,
        message: str,
        fix_hint: str,
        tactic_name: str | None = None,
    ) -> AntFinding:
        evidence: dict = {
            "message": f"{legion_name}: {message}",
            "legion": legion_name,
            "fix_hint": fix_hint,
        }
        if tactic_name is not None:
            evidence["tactic"] = tactic_name
        return AntFinding(
            node_id=f"legion:{legion_name}",
            intensity=7.0,
            kind=KIND_ALERT,
            evidence=evidence,
            half_life_hours=12.0,
        )
