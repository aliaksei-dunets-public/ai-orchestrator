from __future__ import annotations

import hashlib
import json
from pathlib import Path

from orchestrator.execution import baseline_hash


def write_ready_receipt(tasks_root: Path, task_id: str) -> Path:
    checkpoint = tasks_root / "checkpoints" / f"{task_id}.checkpoint.lock"
    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    checkpoint.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "status": "completed",
                "reason": None,
                "records": [
                    {
                        "id": "finalize-task",
                        "status": "completed",
                        "attempts": 1,
                        "evidence": ["documentation, knowledge and memory gates passed"],
                    }
                ],
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    context = tasks_root / "contexts" / f"{task_id}.md"
    text = context.read_text(encoding="utf-8")
    revision = next(
        int(line.split(":", 1)[1].strip())
        for line in text.splitlines()
        if line.startswith("revision:")
    )
    unsigned = {
        "schema_version": 1,
        "task_id": task_id,
        "context_revision": revision,
        "baseline_hash": baseline_hash(text),
        "checkpoint_digest": hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
        "changed_paths_digest": hashlib.sha256(b"test paths").hexdigest(),
        "documentation_status": "completed",
        "documentation_evidence": [],
        "knowledge_status": "empty",
        "knowledge_store_digest": hashlib.sha256(b"empty graph").hexdigest(),
        "memory_status": "completed",
        "memory_proposal_hashes": [],
        "memory_entry_ids": [],
        "pending_approval_hashes": [],
        "ready_for_completion": True,
    }
    unsigned["receipt_hash"] = hashlib.sha256(
        json.dumps(
            unsigned,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    destination = tasks_root / "finalization" / f"{task_id}.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(unsigned, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return destination
