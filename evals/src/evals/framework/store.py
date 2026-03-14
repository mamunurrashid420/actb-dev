"""Local storage for experiment results (SQLite + Parquet)."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from evals.framework.experiment import MultiRunResult, RunResult

# Default storage directory (relative to agents package)
DEFAULT_EVAL_DIR = Path(__file__).parent.parent.parent.parent.parent / ".eval"


class LocalStore:
    """Local storage for experiment results using SQLite + Parquet."""

    def __init__(self, base_dir: Path | None = None):
        """Initialize store with base directory.

        Args:
            base_dir: Base directory for .eval storage. Defaults to data/agents/.eval/
        """
        self.base_dir = Path(base_dir) if base_dir else DEFAULT_EVAL_DIR
        self.db_path = self.base_dir / "experiments.db"
        self.results_dir = self.base_dir / "results"

        # Ensure directories exist
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self._init_db()

    def _init_db(self) -> None:
        """Initialize SQLite database with schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS experiments (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    agent_type TEXT NOT NULL,
                    model TEXT NOT NULL,
                    prompt_source TEXT NOT NULL,
                    prompt_ref TEXT,
                    prompt_hash TEXT NOT NULL,
                    prompt_content TEXT NOT NULL,
                    git_commit TEXT,
                    git_branch TEXT,
                    git_dirty INTEGER,
                    dataset_name TEXT,
                    dataset_hash TEXT NOT NULL,
                    case_count INTEGER NOT NULL,
                    success_rate REAL,
                    summary TEXT,
                    metrics TEXT,
                    total_cases INTEGER,
                    failed_cases INTEGER,
                    duration_seconds REAL,
                    tags TEXT,
                    created_at TEXT NOT NULL,
                    results_path TEXT
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_experiments_agent_type ON experiments(agent_type)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_experiments_created_at ON experiments(created_at DESC)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_experiments_prompt_hash ON experiments(prompt_hash)"
            )
            conn.commit()

    def save_assertion_result(
        self, result: "RunResult", case_results: list["MultiRunResult"]
    ) -> str:
        """Save assertion-based experiment result to storage.

        Args:
            result: RunResult to save
            case_results: List of MultiRunResult from assertion runner

        Returns:
            Path to saved Parquet file
        """
        # Save detailed case results to Parquet
        results_path = self._save_assertion_parquet(result.id, case_results)
        result.results_path = results_path

        # Save metadata to SQLite (reuse existing save logic)
        return self._save_metadata(result)

    def save(self, result: "RunResult", report=None) -> str:
        """Save experiment result to storage.

        Args:
            result: RunResult to save
            report: Optional EvaluationReport for detailed case results

        Returns:
            Path to saved Parquet file (if report provided)
        """
        # Save detailed case results to Parquet if report provided
        results_path = None
        if report is not None:
            results_path = self._save_parquet(result.id, report)
            result.results_path = results_path

        # Save metadata to SQLite
        return self._save_metadata(result)

    def _save_metadata(self, result: "RunResult") -> str:
        """Save result metadata to SQLite."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO experiments (
                    id, name, agent_type, model,
                    prompt_source, prompt_ref, prompt_hash, prompt_content,
                    git_commit, git_branch, git_dirty,
                    dataset_name, dataset_hash, case_count,
                    success_rate, summary, metrics,
                    total_cases, failed_cases, duration_seconds,
                    tags, created_at, results_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    str(result.id),
                    result.name,
                    result.agent_type,
                    result.model,
                    result.provenance.prompt.source,
                    result.provenance.prompt.ref,
                    result.provenance.prompt.hash,
                    result.provenance.prompt.content,
                    result.provenance.git_commit,
                    result.provenance.git_branch,
                    1 if result.provenance.git_dirty else 0,
                    result.provenance.dataset_name,
                    result.provenance.dataset_hash,
                    result.provenance.case_count,
                    result.success_rate,
                    json.dumps(result.summary),
                    json.dumps(result.metrics),
                    result.total_cases,
                    result.failed_cases,
                    result.duration_seconds,
                    json.dumps(result.tags),
                    result.created_at.isoformat(),
                    result.results_path,
                ),
            )
            conn.commit()

        return result.results_path or ""

    def _save_assertion_parquet(
        self, experiment_id: UUID, case_results: list["MultiRunResult"]
    ) -> str:
        """Save assertion-based case results to Parquet."""
        try:
            import polars as pl
        except ImportError:
            return self._save_assertion_json_fallback(experiment_id, case_results)

        rows = []
        for mr in case_results:
            for run in mr.runs:
                row = {
                    "case_name": mr.case_name,
                    "run_index": run.run_index,
                    "passed": run.passed,
                    "duration_ms": run.duration_seconds * 1000,
                    "output": json.dumps(
                        run.output.model_dump()
                        if run.output and hasattr(run.output, "model_dump")
                        else str(run.output)
                    ),
                    "assertion_count": len(run.assertions),
                    "assertions_passed": sum(1 for a in run.assertions if a.passed),
                }

                # Add assertion details as JSON
                assertion_details = []
                for ar in run.assertions:
                    assertion_details.append({
                        "type": ar.assertion.type,
                        "field": ar.assertion.field,
                        "passed": ar.passed,
                        "expected": ar.assertion.value,
                        "actual": ar.actual_value,
                        "message": ar.message,
                    })
                row["assertions"] = json.dumps(assertion_details)

                rows.append(row)

        df = pl.DataFrame(rows)
        parquet_path = self.results_dir / f"{experiment_id}.parquet"
        df.write_parquet(parquet_path)

        return str(parquet_path)

    def _save_assertion_json_fallback(
        self, experiment_id: UUID, case_results: list["MultiRunResult"]
    ) -> str:
        """Fallback to JSON if Polars not available."""
        rows = []
        for mr in case_results:
            for run in mr.runs:
                row = {
                    "case_name": mr.case_name,
                    "run_index": run.run_index,
                    "passed": run.passed,
                }
                rows.append(row)

        json_path = self.results_dir / f"{experiment_id}.json"
        with open(json_path, "w") as f:
            json.dump(rows, f, indent=2)

        return str(json_path)

    def _save_parquet(self, experiment_id: UUID, report) -> str:
        """Save detailed case results to Parquet."""
        try:
            import polars as pl
        except ImportError:
            # Fallback to JSON if polars not available
            return self._save_json_fallback(experiment_id, report)

        rows = []
        for case_result in report.cases:
            row = {
                "case_name": case_result.name,
                "input": json.dumps(
                    case_result.inputs.model_dump()
                    if hasattr(case_result.inputs, "model_dump")
                    else str(case_result.inputs)
                ),
                "output": json.dumps(
                    case_result.output.model_dump()
                    if case_result.output and hasattr(case_result.output, "model_dump")
                    else str(case_result.output)
                ),
                "expected": json.dumps(
                    case_result.expected_output.model_dump()
                    if case_result.expected_output
                    and hasattr(case_result.expected_output, "model_dump")
                    else str(case_result.expected_output)
                ),
                "success": case_result.name not in {f.name for f in report.failures},
                "duration_ms": case_result.duration.total_seconds() * 1000
                if case_result.duration
                else None,
                "error": str(case_result.error)
                if hasattr(case_result, "error") and case_result.error
                else None,
            }

            # Add labels as columns
            if case_result.labels:
                for key, value in case_result.labels.items():
                    row[key] = value

            rows.append(row)

        df = pl.DataFrame(rows)
        parquet_path = self.results_dir / f"{experiment_id}.parquet"
        df.write_parquet(parquet_path)

        return str(parquet_path)

    def _save_json_fallback(self, experiment_id: UUID, report) -> str:
        """Fallback to JSON if Polars not available."""
        rows = []
        for case_result in report.cases:
            row = {
                "case_name": case_result.name,
                "success": case_result.name not in {f.name for f in report.failures},
            }
            rows.append(row)

        json_path = self.results_dir / f"{experiment_id}.json"
        with open(json_path, "w") as f:
            json.dump(rows, f, indent=2)

        return str(json_path)

    def load(self, experiment_id: str | UUID) -> "RunResult | None":
        """Load experiment result by ID."""
        from evals.framework.experiment import RunResult
        from evals.framework.prompt import ResolvedPrompt
        from evals.framework.provenance import Provenance

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM experiments WHERE id = ?", (str(experiment_id),)
            ).fetchone()

            if row is None:
                return None

            # Reconstruct prompt
            prompt = ResolvedPrompt(
                content=row["prompt_content"],
                source=row["prompt_source"],
                ref=row["prompt_ref"],
                version=None,
                hash=row["prompt_hash"],
            )

            # Reconstruct provenance
            provenance = Provenance(
                prompt=prompt,
                git_commit=row["git_commit"],
                git_branch=row["git_branch"],
                git_dirty=bool(row["git_dirty"]),
                dataset_name=row["dataset_name"],
                dataset_hash=row["dataset_hash"],
                case_count=row["case_count"],
                created_at=datetime.fromisoformat(row["created_at"]),
            )

            return RunResult(
                id=UUID(row["id"]),
                name=row["name"],
                provenance=provenance,
                model=row["model"],
                agent_type=row["agent_type"],
                metrics=json.loads(row["metrics"]) if row["metrics"] else {},
                summary=json.loads(row["summary"]) if row["summary"] else {},
                total_cases=row["total_cases"],
                failed_cases=row["failed_cases"],
                duration_seconds=row["duration_seconds"],
                created_at=datetime.fromisoformat(row["created_at"]),
                results_path=row["results_path"],
                tags=json.loads(row["tags"]) if row["tags"] else [],
            )

    def list_experiments(
        self,
        agent_type: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list["RunResult"]:
        """List experiments with optional filtering."""
        query = "SELECT id FROM experiments"
        params: list = []

        if agent_type:
            query += " WHERE agent_type = ?"
            params.append(agent_type)

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(query, params).fetchall()

        results = []
        for (exp_id,) in rows:
            result = self.load(exp_id)
            if result:
                results.append(result)

        return results

    def find_by_prompt_hash(self, prompt_hash: str) -> list["RunResult"]:
        """Find experiments with matching prompt hash."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT id FROM experiments WHERE prompt_hash = ? ORDER BY created_at DESC",
                (prompt_hash,),
            ).fetchall()

        return [r for r in (self.load(row[0]) for row in rows) if r is not None]

    def delete(self, experiment_id: str | UUID) -> bool:
        """Delete an experiment and its results."""
        result = self.load(experiment_id)
        if result is None:
            return False

        # Delete Parquet file if exists
        if result.results_path:
            parquet_path = Path(result.results_path)
            if parquet_path.exists():
                parquet_path.unlink()

        # Delete from database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM experiments WHERE id = ?", (str(experiment_id),))
            conn.commit()

        return True
