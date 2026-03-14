"""Provenance tracking for reproducibility."""

import hashlib
import json
import subprocess
from dataclasses import dataclass, field
from datetime import datetime

from evals.framework.prompt import ResolvedPrompt


@dataclass
class GitState:
    """Current git repository state."""

    commit: str
    branch: str
    dirty: bool

    @staticmethod
    def capture() -> "GitState":
        """Capture current git state."""
        try:
            commit = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()

            branch = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()

            # Check if working directory is dirty
            status = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
            dirty = len(status) > 0

            return GitState(commit=commit, branch=branch, dirty=dirty)
        except (subprocess.CalledProcessError, FileNotFoundError):
            return GitState(commit="unknown", branch="unknown", dirty=True)


def hash_dataset(cases: list) -> str:
    """Compute hash of dataset for reproducibility tracking.

    Hashes the inputs and expected outputs of all cases.
    """
    # Extract hashable content from cases
    hashable_parts = []
    for case in cases:
        # Handle both pydantic_evals Case and our wrapper types
        if hasattr(case, "inputs"):
            inputs = case.inputs
            if hasattr(inputs, "model_dump"):
                inputs = inputs.model_dump()
            hashable_parts.append(("input", json.dumps(inputs, sort_keys=True)))

        if hasattr(case, "expected_output") and case.expected_output is not None:
            expected = case.expected_output
            if hasattr(expected, "model_dump"):
                expected = expected.model_dump()
            hashable_parts.append(("expected", json.dumps(expected, sort_keys=True)))

    content = json.dumps(hashable_parts, sort_keys=True)
    return hashlib.sha256(content.encode()).hexdigest()[:12]


@dataclass
class Provenance:
    """Full provenance for reproducibility."""

    prompt: ResolvedPrompt
    git_commit: str
    git_branch: str
    git_dirty: bool
    dataset_name: str
    dataset_hash: str
    case_count: int
    created_at: datetime = field(default_factory=datetime.now)

    @staticmethod
    def capture(
        prompt: ResolvedPrompt,
        dataset_name: str,
        cases: list,
    ) -> "Provenance":
        """Capture full provenance for an experiment run."""
        git = GitState.capture()
        return Provenance(
            prompt=prompt,
            git_commit=git.commit,
            git_branch=git.branch,
            git_dirty=git.dirty,
            dataset_name=dataset_name,
            dataset_hash=hash_dataset(cases),
            case_count=len(cases),
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "prompt_source": self.prompt.source,
            "prompt_ref": self.prompt.ref,
            "prompt_hash": self.prompt.hash,
            "prompt_content": self.prompt.content,
            "git_commit": self.git_commit,
            "git_branch": self.git_branch,
            "git_dirty": self.git_dirty,
            "dataset_name": self.dataset_name,
            "dataset_hash": self.dataset_hash,
            "case_count": self.case_count,
            "created_at": self.created_at.isoformat(),
        }
