"""ant_principle_invariant — Praetorian-class observation of the four principles.

Arc G / G1 — Legio Praetorian. Sister to `ant_mission_drift`.
Where mission_drift watches the document, principle_invariant
watches the *implementation* of the four cognitive-substrate
principles named in v8.30:

  1. **Sanctum protocol** — `sanctum/` directory exists; contains
     ≥10 sessions; `meta/sanctum-index.md` exists.
  2. **Audit-of-record** — `CHANGELOG.md` exists; `DEVNOTES/audit-of-record.md`
     exists; ≥3 of the documented AoR instances are present.
  3. **Risk classes** — `meta/autonomy-architecture.md` exists
     and names LOW / MEDIUM / HIGH.
  4. **CM (meta-constraint)** — `scripts/ai-meta.sh` exists and
     executes the six checks.

Local rule: any principle whose implementation is missing or
broken = `alert` pheromone at intensity 8.0. The Praetorian
considers all four principles equally load-bearing; the
mythology says CM is immortal (uncuttable) but the *implementation*
of any of the four going missing is a constitutional emergency.

G21 (Praetorian observability): constitutional artifacts only.

Determinism: pure filesystem + content scan.

Authorized by `sanctum/2026-05-13-arc-g-roman-empire-opening.md`.
"""

from __future__ import annotations

from polaris_swarm.base import Ant, AntFinding, KIND_ALERT


class AntPrincipleInvariant(Ant):
    NAME = "ant_principle_invariant"
    DESCRIPTION = "Praetorian: ALERT if any of the four cognitive-substrate principles' implementation is missing."

    def scan(self) -> list[AntFinding]:
        findings: list[AntFinding] = []
        principles = (
            ("sanctum", self._check_sanctum),
            ("audit_of_record", self._check_aor),
            ("risk_classes", self._check_risk_classes),
            ("cm", self._check_cm),
        )
        for name, check in principles:
            result = check()
            if result is not None:
                msg, details = result
                findings.append(AntFinding(
                    node_id=f"principle:{name}",
                    intensity=8.0,
                    kind=KIND_ALERT,
                    evidence={
                        "message": f"principle '{name}' violated: {msg}",
                        "principle": name,
                        "details": details,
                        "fix_hint": (
                            "restore the principle's implementation; "
                            "if removal was intentional, Sanctum-amend "
                            "MISSION.md to retire it explicitly"
                        ),
                    },
                    half_life_hours=12.0,
                ))
        return findings

    def _check_sanctum(self):
        sd = self.root / "sanctum"
        if not sd.is_dir():
            return "sanctum/ directory missing", {"dir": "sanctum"}
        sessions = list(sd.glob("2026-*.md"))
        if len(sessions) < 10:
            return (
                f"only {len(sessions)} sanctum session(s); expected ≥10",
                {"count": len(sessions)},
            )
        index = self.root / "meta" / "sanctum-index.md"
        if not index.is_file():
            return "meta/sanctum-index.md missing", {"file": "meta/sanctum-index.md"}
        return None

    def _check_aor(self):
        if not (self.root / "CHANGELOG.md").is_file():
            return "CHANGELOG.md missing (audit-of-record primary)", {}
        if not (self.root / "DEVNOTES" / "audit-of-record.md").is_file():
            return (
                "DEVNOTES/audit-of-record.md missing (AoR principle doc)",
                {"file": "DEVNOTES/audit-of-record.md"},
            )
        # AoR instances: at least Pheromone table + treasury roll + census roll
        sql = self._read("polaris_sql", "01_schema.sql") or ""
        if "CREATE TABLE Pheromone" not in sql:
            return "Pheromone table (AoR instance) missing from schema", {}
        if not (
            self.root / "polaris_swarm" / "civitas" / "treasury-roll.json"
        ).is_file():
            return "treasury-roll.json (FS-AoR) missing", {}
        return None

    def _check_risk_classes(self):
        aa = self.root / "meta" / "autonomy-architecture.md"
        if not aa.is_file():
            return "meta/autonomy-architecture.md missing", {}
        text = aa.read_text(errors="replace")
        for label in ("LOW", "MEDIUM", "HIGH"):
            if label not in text:
                return (
                    f"risk-class label {label!r} missing from "
                    f"meta/autonomy-architecture.md",
                    {"missing_label": label},
                )
        return None

    def _check_cm(self):
        sh = self.root / "scripts" / "ai-meta.sh"
        if not sh.is_file():
            return "scripts/ai-meta.sh missing (CM enforcement)", {}
        return None
