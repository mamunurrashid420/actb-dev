"""Tests for evaluation result storage."""

import tempfile
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from evals.framework.experiment import RunResult
from evals.framework.prompt import ResolvedPrompt
from evals.framework.provenance import Provenance
from evals.framework.store import LocalStore


class TestLocalStore:
    """Tests for LocalStore."""

    def test_init_creates_directory(self):
        """Store should create .eval directory on init."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir) / ".eval"
            LocalStore(base_dir=base_dir)

            assert base_dir.exists()
            assert (base_dir / "experiments.db").exists()
            assert (base_dir / "results").exists()

    def test_save_and_load_result(self):
        """Store should save and load results."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir) / ".eval"
            store = LocalStore(base_dir=base_dir)

            prompt = ResolvedPrompt(
                content="test prompt",
                source="inline",
                ref=None,
                version=None,
                hash="abc123def456",
            )
            provenance = Provenance(
                prompt=prompt,
                git_commit="abc123",
                git_branch="main",
                git_dirty=False,
                dataset_name="test",
                dataset_hash="def456",
                case_count=5,
            )
            result = RunResult(
                id=uuid4(),
                name="test_run",
                provenance=provenance,
                model="google:gemini-flash",
                agent_type="TestAgent",
                metrics={},
                summary={"success_rate": 0.8},
                total_cases=5,
                failed_cases=1,
                duration_seconds=10.5,
                created_at=datetime.now(),
                tags=["test"],
            )

            # Save
            store.save(result)

            # Load
            loaded = store.load(result.id)
            assert loaded is not None
            assert loaded.name == "test_run"
            assert loaded.success_rate == 0.8
            assert loaded.provenance.prompt.hash == "abc123def456"

    def test_list_experiments_empty(self):
        """Store should return empty list initially."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir) / ".eval"
            store = LocalStore(base_dir=base_dir)

            results = store.list_experiments()
            assert results == []

    def test_list_experiments_returns_saved(self):
        """Store should list saved experiments."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir) / ".eval"
            store = LocalStore(base_dir=base_dir)

            prompt = ResolvedPrompt(
                content="test",
                source="inline",
                ref=None,
                version=None,
                hash="abc123",
            )
            provenance = Provenance(
                prompt=prompt,
                git_commit="abc",
                git_branch="main",
                git_dirty=False,
                dataset_name="test",
                dataset_hash="def",
                case_count=1,
            )
            result = RunResult(
                id=uuid4(),
                name="test_experiment",
                provenance=provenance,
                model="test-model",
                agent_type="TestAgent",
                metrics={},
                summary={},
                total_cases=1,
                failed_cases=0,
                duration_seconds=1.0,
                created_at=datetime.now(),
                tags=[],
            )

            store.save(result)
            experiments = store.list_experiments()

            assert len(experiments) == 1
