import json
import os
import shutil
import sys
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from utils import BackupInfo, BackupType, FileInfo


class BackupSystem:
    def __init__(self, backup_dir: Optional[str] = None):
        if backup_dir:
            self.backup_dir = Path(backup_dir)
        else:
            local_data = os.getenv("LOCALAPPDATA")
            base_dir = Path(local_data) if local_data else Path.home() / "AppData" / "Local"
            self.backup_dir = base_dir / "CacheCleaner" / "backups"

        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.settings_file = self.backup_dir / "backup_settings.json"
        self.auto_cleanup_days = self._load_auto_cleanup_days()
        self._migrate_legacy_backups()
        self.backup_history: List[BackupInfo] = []
        self.load_history()
        self.delete_expired_backups()

    def _load_auto_cleanup_days(self) -> int:
        try:
            with self.settings_file.open("r", encoding="utf-8") as file:
                value = int(json.load(file).get("auto_cleanup_days", 0))
                return value if value in {0, 7, 30, 90} else 0
        except (OSError, ValueError, TypeError, AttributeError):
            return 0

    def set_auto_cleanup_days(self, days: int):
        self.auto_cleanup_days = days if days in {0, 7, 30, 90} else 0
        temporary_file = self.settings_file.with_suffix(".tmp")
        with temporary_file.open("w", encoding="utf-8") as file:
            json.dump({"auto_cleanup_days": self.auto_cleanup_days}, file, indent=2)
        os.replace(temporary_file, self.settings_file)

    @staticmethod
    def _parse_timestamp(timestamp: str) -> Optional[datetime]:
        for pattern in ("%Y%m%d_%H%M%S_%f", "%Y%m%d_%H%M%S"):
            try:
                return datetime.strptime(timestamp, pattern)
            except ValueError:
                continue
        return None

    def delete_expired_backups(self, exclude_names=None) -> Tuple[int, int]:
        """Delete backups older than the persisted retention period."""
        if not self.auto_cleanup_days:
            return 0, 0

        excluded = set(exclude_names or ())
        cutoff = datetime.now() - timedelta(days=self.auto_cleanup_days)
        deleted_names = set()
        freed_bytes = 0

        for backup in self.get_available_backups():
            name = backup["name"]
            created_at = self._parse_timestamp(backup["timestamp"])
            if name in excluded or created_at is None or created_at >= cutoff:
                continue
            try:
                for suffix in (".json", ".zip"):
                    path = self.backup_dir / f"{name}{suffix}"
                    if path.exists():
                        freed_bytes += path.stat().st_size
                        path.unlink()
                deleted_names.add(name)
            except (OSError, PermissionError):
                continue

        if deleted_names:
            deleted_timestamps = {name.replace("backup_", "", 1) for name in deleted_names}
            self.backup_history = [
                backup for backup in self.backup_history
                if backup.timestamp not in deleted_timestamps
            ]
            self.save_history()

        return len(deleted_names), freed_bytes

    def _migrate_legacy_backups(self):
        """Copy backups made by older versions from their working directory."""
        candidates = [Path.cwd() / "cache_backups"]
        try:
            executable_dir = Path(sys.executable).resolve().parent
            candidates.extend(
                [
                    executable_dir / "cache_backups",
                    executable_dir.parent / "cache_backups",
                ]
            )
        except OSError:
            pass

        for legacy_dir in candidates:
            try:
                if not legacy_dir.exists() or legacy_dir.resolve() == self.backup_dir.resolve():
                    continue
                for source in legacy_dir.glob("backup_*.*"):
                    if source.suffix.lower() not in {".json", ".zip"}:
                        continue
                    target = self.backup_dir / source.name
                    if not target.exists():
                        shutil.copy2(source, target)
            except (OSError, PermissionError):
                continue

    def load_history(self):
        history_file = self.backup_dir / "backup_history.json"
        if not history_file.exists():
            return
        try:
            with history_file.open("r", encoding="utf-8") as file:
                self.backup_history = [BackupInfo.from_dict(item) for item in json.load(file)]
        except (OSError, ValueError, KeyError, TypeError):
            self.backup_history = []

    def save_history(self):
        history_file = self.backup_dir / "backup_history.json"
        temporary_file = history_file.with_suffix(".tmp")
        with temporary_file.open("w", encoding="utf-8") as file:
            json.dump(
                [backup.to_dict() for backup in self.backup_history],
                file,
                indent=2,
                ensure_ascii=False,
            )
        os.replace(temporary_file, history_file)

    def create_backup(
        self,
        files_to_backup: List[str],
        backup_type: BackupType = BackupType.SMART,
        description: str = "",
    ) -> Optional[str]:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        backup_name = f"backup_{timestamp}"
        zip_path = self.backup_dir / f"{backup_name}.zip"
        meta_file = self.backup_dir / f"{backup_name}.json"
        files_info: Dict[str, FileInfo] = {}
        total_size = 0

        unique_files = list(dict.fromkeys(os.path.normpath(path) for path in files_to_backup))
        try:
            with zipfile.ZipFile(
                zip_path,
                "w",
                compression=zipfile.ZIP_DEFLATED,
                compresslevel=6,
                allowZip64=True,
            ) as archive:
                for index, file_path in enumerate(unique_files):
                    try:
                        if not os.path.isfile(file_path):
                            continue
                        stat = os.stat(file_path)
                        archive_name = f"files/{index:08d}"
                        archive.write(file_path, archive_name)
                        files_info[file_path] = FileInfo(
                            path=file_path,
                            size=stat.st_size,
                            modified_time=stat.st_mtime,
                            backup_path=archive_name,
                        )
                        total_size += stat.st_size
                    except (OSError, PermissionError):
                        continue

            if not files_info:
                zip_path.unlink(missing_ok=True)
                return None

            with zipfile.ZipFile(zip_path, "r") as archive:
                if any(item.compress_type != zipfile.ZIP_DEFLATED for item in archive.infolist()):
                    raise zipfile.BadZipFile("Некоторые файлы не были сжаты")

            backup_info = BackupInfo(
                timestamp=timestamp,
                total_size=total_size,
                file_count=len(files_info),
                backup_type=backup_type.value,
                description=description,
                files=files_info,
            )
            with meta_file.open("w", encoding="utf-8") as file:
                json.dump(backup_info.to_dict(), file, indent=2, ensure_ascii=False)

            self.backup_history.append(backup_info)
            self.save_history()
            return backup_name
        except (OSError, PermissionError, zipfile.BadZipFile):
            zip_path.unlink(missing_ok=True)
            meta_file.unlink(missing_ok=True)
            return None

    def get_available_backups(self) -> List[Dict]:
        backups = []
        for backup_file in self.backup_dir.glob("backup_*.json"):
            try:
                with backup_file.open("r", encoding="utf-8") as file:
                    data = json.load(file)
                archive_path = self.backup_dir / f"{backup_file.stem}.zip"
                archive_exists = archive_path.exists()
                archive_size = archive_path.stat().st_size if archive_exists else 0
                total_size = int(data["total_size"])
                saved_percent = (
                    max(0, round((1 - archive_size / total_size) * 100))
                    if total_size > 0 and archive_exists
                    else 0
                )
                backups.append(
                    {
                        "name": backup_file.stem,
                        "timestamp": data["timestamp"],
                        "file_count": int(data["file_count"]),
                        "total_size": total_size,
                        "description": data.get("description", ""),
                        "archive_exists": archive_exists,
                        "archive_size": archive_size,
                        "saved_percent": saved_percent,
                    }
                )
            except (OSError, ValueError, KeyError, TypeError):
                continue
        return sorted(backups, key=lambda item: item["timestamp"], reverse=True)

    def load_backup(self, backup_name: str) -> Optional[BackupInfo]:
        backup_file = self.backup_dir / f"{backup_name}.json"
        try:
            with backup_file.open("r", encoding="utf-8") as file:
                return BackupInfo.from_dict(json.load(file))
        except (OSError, ValueError, KeyError, TypeError):
            return None

    @staticmethod
    def _find_archive_member(archive: zipfile.ZipFile, file_info: FileInfo) -> Optional[str]:
        members = archive.namelist()
        normalized = {name.replace("\\", "/").lower(): name for name in members}

        if file_info.backup_path:
            saved_name = file_info.backup_path.replace("\\", "/").lower()
            if saved_name in normalized:
                return normalized[saved_name]

        _, path_without_drive = os.path.splitdrive(file_info.path)
        legacy_name = path_without_drive.lstrip("\\/").replace("\\", "/").lower()
        if legacy_name in normalized:
            return normalized[legacy_name]

        basename = os.path.basename(file_info.path).lower()
        basename_matches = [name for name in members if os.path.basename(name).lower() == basename]
        return basename_matches[0] if len(basename_matches) == 1 else None

    def restore_files(
        self,
        backup_name: str,
        files_to_restore: Optional[List[str]] = None,
    ) -> Tuple[int, int, List[str]]:
        backup_info = self.load_backup(backup_name)
        if not backup_info:
            return 0, 0, ["Не удалось прочитать описание бэкапа"]

        selected_files = [
            info
            for info in backup_info.files.values()
            if not files_to_restore or info.path in files_to_restore
        ]
        total_files = len(selected_files)
        restored_count = 0
        failed_files: List[str] = []
        zip_path = self.backup_dir / f"{backup_name}.zip"

        if not zip_path.exists():
            return 0, total_files, ["Архив бэкапа не найден"]

        try:
            with zipfile.ZipFile(zip_path, "r") as archive:
                for file_info in selected_files:
                    archive_member = self._find_archive_member(archive, file_info)
                    if not archive_member:
                        failed_files.append(f"{file_info.path}: файла нет в архиве")
                        continue

                    target = Path(file_info.path)
                    temporary = target.with_name(target.name + ".cachecleaner-restore")
                    try:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        with archive.open(archive_member, "r") as source, temporary.open("wb") as destination:
                            shutil.copyfileobj(source, destination, length=1024 * 1024)
                        os.replace(temporary, target)
                        os.utime(target, (file_info.modified_time, file_info.modified_time))
                        restored_count += 1
                    except (OSError, PermissionError, KeyError) as error:
                        temporary.unlink(missing_ok=True)
                        failed_files.append(f"{file_info.path}: {error}")
        except (OSError, PermissionError, zipfile.BadZipFile) as error:
            return 0, total_files, [f"Не удалось открыть архив: {error}"]

        return restored_count, total_files, failed_files

    def delete_backup(self, backup_name: str) -> bool:
        try:
            (self.backup_dir / f"{backup_name}.json").unlink(missing_ok=True)
            (self.backup_dir / f"{backup_name}.zip").unlink(missing_ok=True)
            self.backup_history = [
                backup
                for backup in self.backup_history
                if backup.timestamp != backup_name.replace("backup_", "")
            ]
            self.save_history()
            return True
        except (OSError, PermissionError):
            return False
