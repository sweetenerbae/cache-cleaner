import json
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict


class StatisticsStore:
    """Persist anonymous cleanup counters locally for the statistics dashboard."""

    def __init__(self, backup_dir: Path):
        local_data = os.getenv("LOCALAPPDATA")
        base_dir = Path(local_data) if local_data else Path.home() / "AppData" / "Local"
        self.data_dir = base_dir / "CacheCleaner"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.data_file = self.data_dir / "statistics.json"
        self.backup_dir = Path(backup_dir)

    @staticmethod
    def _empty_data() -> Dict:
        return {
            "total_cleaned_bytes": 0,
            "total_deleted_files": 0,
            "daily": {},
            "categories": {},
        }

    def _load(self) -> Dict:
        try:
            with self.data_file.open("r", encoding="utf-8") as file:
                raw = json.load(file)
            data = self._empty_data()
            data.update(raw if isinstance(raw, dict) else {})
            return data
        except (OSError, ValueError, TypeError):
            return self._empty_data()

    def _save(self, data: Dict):
        temporary = self.data_file.with_suffix(".tmp")
        with temporary.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=2, ensure_ascii=False)
        os.replace(temporary, self.data_file)

    def record_cleanup(self, cleaned_bytes: int, deleted_files: int, categories: Dict[str, int]):
        cleaned_bytes = max(0, int(cleaned_bytes))
        deleted_files = max(0, int(deleted_files))
        if not cleaned_bytes and not deleted_files:
            return
        data = self._load()
        today = date.today().isoformat()
        daily = data.setdefault("daily", {}).setdefault(
            today, {"cleaned_bytes": 0, "deleted_files": 0}
        )
        daily["cleaned_bytes"] = int(daily.get("cleaned_bytes", 0)) + cleaned_bytes
        daily["deleted_files"] = int(daily.get("deleted_files", 0)) + deleted_files
        data["total_cleaned_bytes"] = int(data.get("total_cleaned_bytes", 0)) + cleaned_bytes
        data["total_deleted_files"] = int(data.get("total_deleted_files", 0)) + deleted_files
        category_data = data.setdefault("categories", {})
        for category, size in categories.items():
            if size > 0:
                category_data[category] = int(category_data.get(category, 0)) + int(size)

        cutoff = (date.today() - timedelta(days=365)).isoformat()
        data["daily"] = {
            day: values for day, values in data.get("daily", {}).items() if day >= cutoff
        }
        self._save(data)

    def snapshot(self) -> Dict:
        data = self._load()
        today = date.today()
        today_values = data.get("daily", {}).get(today.isoformat(), {})
        history = []
        for offset in range(6, -1, -1):
            day = today - timedelta(days=offset)
            values = data.get("daily", {}).get(day.isoformat(), {})
            history.append(
                {
                    "date": day.isoformat(),
                    "label": day.strftime("%d.%m"),
                    "cleaned_bytes": int(values.get("cleaned_bytes", 0)),
                    "deleted_files": int(values.get("deleted_files", 0)),
                }
            )
        backup_bytes = 0
        backup_count = 0
        try:
            for path in self.backup_dir.glob("backup_*.zip"):
                backup_bytes += path.stat().st_size
                backup_count += 1
        except (OSError, PermissionError):
            pass
        categories = sorted(
            (
                {"name": name, "cleaned_bytes": int(size)}
                for name, size in data.get("categories", {}).items()
            ),
            key=lambda item: item["cleaned_bytes"],
            reverse=True,
        )
        return {
            "today_cleaned_bytes": int(today_values.get("cleaned_bytes", 0)),
            "total_cleaned_bytes": int(data.get("total_cleaned_bytes", 0)),
            "total_deleted_files": int(data.get("total_deleted_files", 0)),
            "backup_bytes": backup_bytes,
            "backup_count": backup_count,
            "history": history,
            "categories": categories[:5],
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }
