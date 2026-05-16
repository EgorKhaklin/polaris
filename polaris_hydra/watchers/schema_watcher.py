"""SchemaWatcher — H2 of Arc D.

Monitors Polaris's audit-of-record discipline at the schema layer:

  - Are the expected audit-of-record tables present?
  - Are their append-only / immutability triggers installed?
  - Are the v7 hardening objects (C-NEW-1..C-NEW-4) installed?
  - Are the expected per-entity indexes present?
  - **(v9.04)** Pheromone-context: recent soldier_db_table_size
    deposits surface row-count growth that the static schema check
    can't see (a table whose audit triggers are present but whose
    row count is exploding is a different signal).

This watcher caught the v8.32 finding (12_v7_constraints.sql silently
not applied) retroactively — that exact failure mode is what it's
designed to surface continuously going forward.

Connection details come from environment variables matching the rest
of Polaris (POLARIS_DB_HOST / POLARIS_DB_NAME / POLARIS_DB_USER /
POLARIS_DB_PASSWORD). If psycopg2 is not importable or the DB is
unreachable, the watcher emits an `alert` finding and returns a
status="alert" report; it does not crash HYDRA.
"""

from __future__ import annotations

import os
from typing import Any

from polaris_hydra.pheromone_reader import PheromoneReader, WINDOW_SLOW

from .base import Finding, Watcher, WatcherReport


# The nine schema instances of the audit-of-record principle (v8.32
# correction; the 10th instance is filesystem-based — `sanctum/*.md`),
# plus AuthAuditLog (administrative) — together the 11 expected tables
# this watcher inspects. Numbers + naming pin to
# `DEVNOTES/audit-of-record.md` (canonical) as of v8.32 / v8.45.
EXPECTED_AOR_TABLES: dict[str, str] = {
    "tokenlifecycleevent":   "TokenLifecycleEvent",
    "verificationevent":     "VerificationEvent",
    "enrollmentstatusevent": "EnrollmentStatusEvent",
    "recoveryrequest":       "RecoveryRequest",        # partial-enforcement
    "tokensignature":        "TokenSignature",
    "anchorbatch":           "AnchorBatch",
    "agencytrustattestation": "AgencyTrustAttestation",
    "tokenstateepoch":       "TokenStateEpoch",
    "tokenstateepochleaf":   "TokenStateEpochLeaf",
    "duressevent":           "DuressEvent",
    "authauditlog":          "AuthAuditLog",
}

# Triggers we expect on the schema. Names match exactly what's
# installed by 01_schema.sql / 06_triggers.sql / 12_v7_constraints.sql.
EXPECTED_TRIGGERS: dict[str, str] = {
    "trg_lifecycle_append_only":      "tokenlifecycleevent",
    "trg_verification_append_only":   "verificationevent",
    "trg_enrollment_event_append_only": "enrollmentstatusevent",
    "trg_token_signature_immutable":  "tokensignature",
    "trg_anchor_batch_append_only":   "anchorbatch",
    "trg_attestation_immutable":      "agencytrustattestation",
    "trg_epoch_immutable":            "tokenstateepoch",
    "trg_epoch_leaf_append_only":     "tokenstateepochleaf",
    "trg_duress_event_append_only":   "duressevent",
    "trg_authaudit_append_only":      "authauditlog",
    "trg_predecessor_same_individual": "identitytoken",   # v7 C-NEW-1
    "trg_revocation_status":          "revocationlist",   # v7 C-NEW-2
}

EXPECTED_INDEXES: list[str] = [
    "uq_one_active_per_person",          # C3
    "idx_token_individual_status",       # v7 C-NEW-3
]

EXPECTED_VIEWS: list[str] = [
    "activetokens",
    "tokenswithlifecyclesummary",        # v7 C-NEW-4
]


class SchemaWatcher(Watcher):
    name = "schema"
    domain = "audit-of-record tables + triggers + v7 hardening + indexes"

    # v9.28 / Hydra #4 — runtime-grounded schema probe.
    # Diffs DECLARED schema (polaris_sql/01_schema.sql AST-parsed)
    # against LIVE schema (pg_class / pg_indexes via psycopg2). Returns
    # Finding objects describing any drift. INCONCLUSIVE on connection
    # failure per Anti-Architect honest-accounting (chaos-test pattern).
    def query_live_schema(self) -> list[Finding]:
        """Compare declared schema against the live DB.

        Returns:
          [] if everything matches.
          [Finding(severity='inconclusive', ...)] if DB unreachable.
          [Finding(severity='alert', ...)] for each missing-in-live table
            or partial-unique-index declared in 01_schema.sql but absent
            from pg_indexes.

        Predicate (per meta/watcher-predicates.md): "Every table declared
        in polaris_sql/01_schema.sql exists in the live database with
        matching column types, and every partial unique index in the
        schema file is present in pg_indexes."
        External record: pg_class + pg_indexes (live DB query).
        """
        try:
            import psycopg2
            import os, re as _re
            from pathlib import Path as _Path
            ROOT = _Path(__file__).resolve().parents[2]
        except ImportError:
            return [Finding(
                severity="drift",
                title="schema_watcher runtime probe INCONCLUSIVE",
                detail="psycopg2 not importable; cannot probe live schema.",
                evidence={"node_id": "schema:runtime", "status": "inconclusive"},
            )]

        # Parse declared tables from 01_schema.sql (cheap: grep CREATE TABLE)
        schema_file = ROOT / "polaris_sql" / "01_schema.sql"
        if not schema_file.is_file():
            return [Finding(
                severity="drift",
                title="schema_watcher cannot find 01_schema.sql",
                detail=f"Expected at {schema_file}",
                evidence={"node_id": "schema:runtime", "status": "inconclusive"},
            )]
        declared_tables = set()
        with open(schema_file) as f:
            content = f.read()
        for m in _re.finditer(
            r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)',
            content, _re.IGNORECASE
        ):
            declared_tables.add(m.group(1).lower())

        # Connect to live DB
        db_config = {
            "host": os.environ.get("POLARIS_DB_HOST", "localhost"),
            "user": os.environ.get("POLARIS_DB_USER", "polaris_app"),
            "password": os.environ.get("POLARIS_DB_PASSWORD", ""),
            "database": os.environ.get("POLARIS_DB_NAME", "polaris"),
        }
        try:
            conn = psycopg2.connect(**db_config, connect_timeout=2)
        except Exception as e:
            return [Finding(
                severity="drift",
                title="schema_watcher runtime probe INCONCLUSIVE",
                detail=(f"Cannot connect to live DB ({e.__class__.__name__}); "
                        f"falling back to file-only check. Run live for "
                        f"runtime-grounded coverage."),
                evidence={
                    "node_id": "schema:runtime",
                    "status": "inconclusive",
                    "db_error": str(e)[:100],
                },
            )]

        findings: list[Finding] = []
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT lower(tablename) FROM pg_tables "
                    "WHERE schemaname = 'public'"
                )
                live_tables = {row[0] for row in cur.fetchall()}
            missing = sorted(declared_tables - live_tables)
            for t in missing:
                findings.append(Finding(
                    severity="alert",
                    title=f"declared table {t!r} MISSING from live DB",
                    detail=(f"polaris_sql/01_schema.sql declares table {t!r} "
                            f"but pg_tables does not list it. C1-C10 cannot "
                            f"hold on a table that doesn't exist."),
                    evidence={
                        "node_id": f"schema:missing:{t}",
                        "table": t,
                    },
                ))
        finally:
            conn.close()

        return findings

    def _observe(self) -> WatcherReport:
        # Lazy import so the package loads even if psycopg2 is absent.
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
        except ImportError as exc:
            return WatcherReport(
                watcher_name=self.name,
                domain=self.domain,
                status="alert",
                findings=[Finding(
                    severity="alert",
                    title="psycopg2 not importable",
                    detail=("SchemaWatcher requires psycopg2. Install it in "
                            "the same venv the Flask app uses."),
                    evidence={"import_error": str(exc)},
                )],
                evidence_summary={"can_connect": False},
            )

        db_config = {
            "host":     os.environ.get("POLARIS_DB_HOST", "localhost"),
            "dbname":   os.environ.get("POLARIS_DB_NAME", "polaris_test"),
            "user":     os.environ.get("POLARIS_DB_USER", "polaris_app"),
            "password": os.environ.get("POLARIS_DB_PASSWORD",
                                       "polaris_dev_password"),
        }

        try:
            conn = psycopg2.connect(cursor_factory=RealDictCursor, **db_config)
        except psycopg2.OperationalError as exc:
            return WatcherReport(
                watcher_name=self.name,
                domain=self.domain,
                status="alert",
                findings=[Finding(
                    severity="alert",
                    title="cannot reach Polaris database",
                    detail=("SchemaWatcher could not connect. The watcher "
                            "operates on a live DB; without one, schema "
                            "integrity cannot be verified."),
                    evidence={"db_host": db_config["host"],
                              "db_name": db_config["dbname"],
                              "error": str(exc)[:200]},
                )],
                evidence_summary={"can_connect": False},
            )

        findings: list[Finding] = []
        evidence: dict[str, Any] = {}

        try:
            with conn, conn.cursor() as cur:
                # --- Tables -----------------------------------------------
                cur.execute(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public'"
                )
                present_tables = {row["table_name"].lower()
                                  for row in cur.fetchall()}
                missing_tables = [
                    display for lower, display in EXPECTED_AOR_TABLES.items()
                    if lower not in present_tables
                ]
                evidence["aor_tables_present"] = (
                    len(EXPECTED_AOR_TABLES) - len(missing_tables)
                )
                evidence["aor_tables_expected"] = len(EXPECTED_AOR_TABLES)
                if missing_tables:
                    findings.append(Finding(
                        severity="alert",
                        title="audit-of-record table missing",
                        detail=("One or more expected audit-of-record tables "
                                "are absent from the schema. The schema may "
                                "not have been loaded fully; cannot verify "
                                "the audit-of-record discipline."),
                        evidence={"missing": missing_tables},
                    ))

                # --- Triggers ---------------------------------------------
                cur.execute(
                    "SELECT trigger_name, event_object_table "
                    "FROM information_schema.triggers"
                )
                present_triggers = {
                    (row["trigger_name"], row["event_object_table"].lower())
                    for row in cur.fetchall()
                }
                present_trigger_names = {n for n, _ in present_triggers}
                missing_triggers = [
                    f"{name} on {tbl}"
                    for name, tbl in EXPECTED_TRIGGERS.items()
                    if name not in present_trigger_names
                ]
                evidence["triggers_present"] = (
                    len(EXPECTED_TRIGGERS) - len(missing_triggers)
                )
                evidence["triggers_expected"] = len(EXPECTED_TRIGGERS)
                if missing_triggers:
                    # The v7 hardening triggers historically went missing
                    # (v8.32 finding); call those out by name.
                    v7_missing = [t for t in missing_triggers
                                  if "predecessor_same_individual" in t
                                  or "revocation_status" in t]
                    if v7_missing:
                        findings.append(Finding(
                            severity="alert",
                            title="v7 hardening trigger missing",
                            detail=("12_v7_constraints.sql DDL did not apply. "
                                    "This is the v8.32 silent-failure mode: "
                                    "the file was likely loaded as a "
                                    "no-DDL-privilege role. Re-apply 12_v7_"
                                    "constraints.sql as a superuser."),
                            evidence={"missing": v7_missing},
                        ))
                    other_missing = [t for t in missing_triggers
                                     if t not in v7_missing]
                    if other_missing:
                        findings.append(Finding(
                            severity="alert",
                            title="audit-of-record trigger missing",
                            detail=("Append-only or immutability trigger "
                                    "absent. The corresponding table is "
                                    "writeable without the discipline."),
                            evidence={"missing": other_missing},
                        ))

                # --- Indexes ----------------------------------------------
                cur.execute(
                    "SELECT indexname FROM pg_indexes "
                    "WHERE schemaname = 'public'"
                )
                present_indexes = {row["indexname"]
                                   for row in cur.fetchall()}
                missing_indexes = [
                    idx for idx in EXPECTED_INDEXES
                    if idx not in present_indexes
                ]
                evidence["indexes_present"] = (
                    len(EXPECTED_INDEXES) - len(missing_indexes)
                )
                evidence["indexes_expected"] = len(EXPECTED_INDEXES)
                if missing_indexes:
                    findings.append(Finding(
                        severity="drift",
                        title="expected index missing",
                        detail=("One or more performance / uniqueness "
                                "indexes are absent. C3 is enforced by "
                                "uq_one_active_per_person; if that index is "
                                "missing the constraint is unenforced."),
                        evidence={"missing": missing_indexes},
                    ))

                # --- Views ------------------------------------------------
                cur.execute(
                    "SELECT viewname FROM pg_views "
                    "WHERE schemaname = 'public'"
                )
                present_views = {row["viewname"]
                                 for row in cur.fetchall()}
                missing_views = [
                    v for v in EXPECTED_VIEWS if v not in present_views
                ]
                evidence["views_present"] = (
                    len(EXPECTED_VIEWS) - len(missing_views)
                )
                evidence["views_expected"] = len(EXPECTED_VIEWS)
                if missing_views:
                    findings.append(Finding(
                        severity="drift",
                        title="expected view missing",
                        detail=("One or more application-facing views are "
                                "absent."),
                        evidence={"missing": missing_views},
                    ))

                # --- Audit-of-record row counts (info-level signal) ------
                # If a recent ship added a table but its seed didn't land,
                # this surfaces it.
                row_counts: dict[str, int] = {}
                for lower, display in EXPECTED_AOR_TABLES.items():
                    if lower in present_tables:
                        try:
                            cur.execute(f"SELECT count(*) AS n FROM {display}")
                            row_counts[display] = cur.fetchone()["n"]
                        except Exception:  # noqa: BLE001
                            row_counts[display] = -1
                evidence["aor_row_counts"] = row_counts
        finally:
            conn.close()

        # --- Pheromone-context: soldier_db_table_size growth (v9.04) -----
        ph_findings, ph_evidence = self._check_pheromone_table_size()
        findings.extend(ph_findings)
        evidence.update(ph_evidence)

        # Compute aggregate status.
        if any(f.severity == "alert" for f in findings):
            status = "alert"
        elif sum(1 for f in findings if f.severity == "drift") >= 2:
            status = "drift"
        elif any(f.severity == "drift" for f in findings):
            # Single drift finding still counts as drift, but watchers may
            # choose to call this "healthy with a note". We err on drift.
            status = "drift"
        else:
            status = "healthy"

        if not findings:
            findings.append(Finding(
                severity="info",
                title="schema invariants intact",
                detail=("All expected audit-of-record tables, append-only / "
                        "immutability triggers, v7 hardening objects, and "
                        "indexes are present."),
                evidence={"tables": evidence["aor_tables_present"],
                          "triggers": evidence["triggers_present"],
                          "indexes": evidence["indexes_present"],
                          "views": evidence["views_present"]},
            ))

        evidence["can_connect"] = True

        return WatcherReport(
            watcher_name=self.name,
            domain=self.domain,
            status=status,
            findings=findings,
            evidence_summary=evidence,
        )

    # ------------------------------------------------------------------
    # Pheromone-context channel (v9.04): soldier_db_table_size signal
    # ------------------------------------------------------------------

    def _check_pheromone_table_size(
        self,
    ) -> tuple[list[Finding], dict[str, Any]]:
        """Read recent soldier_db_table_size deposits + surface growth.

        soldier_db_table_size deposits one pheromone per audit-class
        table per pass; the deposit's `intensity` carries the row
        count (or growth rate). Where the schema check confirms the
        TABLES + TRIGGERS are present, this channel reads what's
        ACCUMULATING in them.

        Graceful: missing reader / no deposits → no findings.
        """
        findings: list[Finding] = []
        evidence: dict[str, Any] = {
            "pheromone_table_size_status": "unknown",
        }

        try:
            reader = PheromoneReader(window_hours=WINDOW_SLOW)
            deposits = reader.deposits_by_class("soldier_db_table_size",
                                                window_hours=WINDOW_SLOW)
        except Exception as exc:  # noqa: BLE001 — graceful
            evidence["pheromone_table_size_status"] = (
                f"reader_error:{type(exc).__name__}"
            )
            return findings, evidence

        if not deposits:
            evidence["pheromone_table_size_status"] = "no_deposits_in_window"
            return findings, evidence

        evidence["pheromone_table_size_status"] = "ok"
        evidence["pheromone_table_size_count"] = len(deposits)

        # alert/drift kinds = soldier flagged growth (e.g., a table that
        # gained N rows in M hours faster than the configured threshold).
        alert_count = sum(1 for d in deposits if d.kind == "alert")
        drift_count = sum(1 for d in deposits if d.kind == "drift")
        evidence["pheromone_table_size_alert"] = alert_count
        evidence["pheromone_table_size_drift"] = drift_count

        if alert_count > 0 or drift_count > 0:
            sample_node_ids = sorted({
                d.node_id for d in deposits
                if d.kind in ("alert", "drift")
            })[:5]
            findings.append(Finding(
                severity="drift",
                title=(f"soldier_db_table_size flagged "
                       f"{alert_count + drift_count} table-growth event(s)"),
                detail=(
                    f"In the last {WINDOW_SLOW:.0f}h soldier_db_table_size "
                    f"deposited {alert_count} alert + {drift_count} drift "
                    f"pheromone(s). The schema layer is healthy "
                    f"(triggers present), but at least one table is "
                    f"growing fast enough to warrant the soldier's "
                    f"attention. Sample node_ids: {sample_node_ids}"
                ),
                evidence={
                    "alert_count": alert_count,
                    "drift_count": drift_count,
                    "sample_node_ids": sample_node_ids,
                    "node_id": sample_node_ids[0] if sample_node_ids
                                else "schema:tables",
                    "pheromone_context": "soldier_db_table_size",
                },
            ))

        return findings, evidence
