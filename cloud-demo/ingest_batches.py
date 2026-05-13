#!/usr/bin/env python3
"""入库批次记录。

批次记录让每次自动入库都可观察、可追溯、可回滚。这里使用 JSON 文件，
保持本地部署简单，也避免引入数据库迁移成本。
"""
import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class IngestBatchStore:
    """JSON backed ingest batch store."""

    def __init__(self, store_dir: str):
        self.store_dir = Path(store_dir)
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self.store_file = self.store_dir / "ingest_batches.json"
        if not self.store_file.exists():
            self._write([])

    def _read(self) -> List[Dict]:
        try:
            return json.loads(self.store_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _write(self, batches: List[Dict]) -> None:
        self.store_file.write_text(
            json.dumps(batches, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def create_batch(self, file_names: List[str]) -> Dict:
        now = datetime.now().isoformat(timespec="seconds")
        batch = {
            "id": f"batch-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}",
            "status": "running",
            "created_at": now,
            "updated_at": now,
            "file_names": file_names,
            "original_files": [],
            "generated_files": [],
            "entities": [],
            "links": [],
            "errors": [],
            "log": [],
        }
        batches = self._read()
        batches.insert(0, batch)
        self._write(batches)
        return batch

    def list_batches(self) -> List[Dict]:
        return self._read()

    def get_batch(self, batch_id: str) -> Optional[Dict]:
        for batch in self._read():
            if batch.get("id") == batch_id:
                return batch
        return None

    def update_batch(self, batch_id: str, **updates) -> Dict:
        batches = self._read()
        now = datetime.now().isoformat(timespec="seconds")
        for index, batch in enumerate(batches):
            if batch.get("id") == batch_id:
                batch.update(updates)
                batch["updated_at"] = now
                batches[index] = batch
                self._write(batches)
                return batch
        raise KeyError(f"Batch not found: {batch_id}")

    def delete_batch(self, batch_id: str) -> Dict:
        batches = self._read()
        kept = []
        deleted = None
        for batch in batches:
            if batch.get("id") == batch_id:
                deleted = batch
            else:
                kept.append(batch)
        if deleted is None:
            raise KeyError(f"Batch not found: {batch_id}")
        self._write(kept)
        return deleted

    def delete_batches(self, batch_ids: List[str]) -> List[Dict]:
        id_set = set(batch_ids)
        batches = self._read()
        kept = []
        deleted = []
        for batch in batches:
            if batch.get("id") in id_set:
                deleted.append(batch)
            else:
                kept.append(batch)
        self._write(kept)
        return deleted

    def append_log(self, batch_id: str, message: str) -> Dict:
        batch = self.get_batch(batch_id)
        if not batch:
            raise KeyError(f"Batch not found: {batch_id}")
        log = batch.get("log", [])
        log.append({"time": datetime.now().isoformat(timespec="seconds"), "message": message})
        return self.update_batch(batch_id, log=log)


def default_store(project_dir: str) -> IngestBatchStore:
    return IngestBatchStore(os.path.join(project_dir, "data"))
