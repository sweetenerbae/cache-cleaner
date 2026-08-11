import os
import json
import zipfile
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from utils import BackupInfo, FileInfo, BackupType


class BackupSystem:
    def __init__(self, backup_dir: str = "cache_backups"):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)
        self.backup_history: List[BackupInfo] = []
        self.load_history()

    # backup history loading
    def load_history(self):
        history_file = self.backup_dir / "backup_history.json"
        if history_file.exists():
            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.backup_history = [
                        BackupInfo.from_dict(item) for item in data
                    ]
            except Exception:
                self.backup_history = []

    # save backup
    def save_history(self):
        history_file = self.backup_dir / "backup_history.json"
        try:
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(
                    [backup.to_dict() for backup in self.backup_history],
                    f,
                    indent=2,
                    ensure_ascii=False
                )
        except Exception as e:
            print(f"Error saving history: {e}")

    # create backup
    def create_backup(
            self,
            files_to_backup: List[str],
            backup_type: BackupType = BackupType.SMART,
            description: str = ""
    ) -> Optional[str]:
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"backup_{timestamp}"

            files_info = {}
            total_size = 0

            files_to_copy = []
            if backup_type == BackupType.FULL:
                files_to_copy = files_to_backup
            elif backup_type == BackupType.SMART:
                for file_path in files_to_backup:
                    try:
                        if os.path.getsize(file_path) < 50 * 1024 * 1024:  # 50MB
                            files_to_copy.append(file_path)
                    except Exception:
                        continue

            # zip file create
            zip_path = self.backup_dir / f"{backup_name}.zip"
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in files_to_copy:
                    try:
                        if os.path.exists(file_path):
                            arcname = os.path.relpath(file_path, '/')
                            zipf.write(file_path, arcname)

                            stat = os.stat(file_path)
                            files_info[file_path] = FileInfo(
                                path=file_path,
                                size=stat.st_size,
                                modified_time=stat.st_mtime,
                                backup_path=str(self.backup_dir / os.path.basename(file_path))
                            )
                            total_size += stat.st_size
                    except Exception:
                        continue

            for file_path in set(files_to_backup) - set(files_to_copy):
                try:
                    if os.path.exists(file_path):
                        stat = os.stat(file_path)
                        files_info[file_path] = FileInfo(
                            path=file_path,
                            size=stat.st_size,
                            modified_time=stat.st_mtime,
                            backup_path=None
                        )
                        total_size += stat.st_size
                except Exception:
                    continue

            backup_info = BackupInfo(
                timestamp=timestamp,
                total_size=total_size,
                file_count=len(files_info),
                backup_type=backup_type.value,
                description=description,
                files=files_info
            )

            meta_file = self.backup_dir / f"{backup_name}.json"
            with open(meta_file, 'w', encoding='utf-8') as f:
                json.dump(backup_info.to_dict(), f, indent=2, ensure_ascii=False)

            self.backup_history.append(backup_info)
            self.save_history()

            return backup_name

        except Exception as e:
            print(f"Backup creation error: {e}")
            return None

    def get_available_backups(self) -> List[Dict]:
        backups = []
        for backup_file in self.backup_dir.glob("backup_*.json"):
            try:
                with open(backup_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    backups.append({
                        "name": backup_file.stem,
                        "timestamp": data["timestamp"],
                        "file_count": data["file_count"],
                        "total_size": data["total_size"],
                        "description": data["description"]
                    })
            except Exception:
                continue

        backups.sort(key=lambda x: x["timestamp"], reverse=True)
        return backups

    def load_backup(self, backup_name: str) -> Optional[BackupInfo]:
        backup_file = self.backup_dir / f"{backup_name}.json"
        if backup_file.exists():
            try:
                with open(backup_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return BackupInfo.from_dict(data)
            except Exception:
                return None
        return None

    def restore_files(
            self,
            backup_name: str,
            files_to_restore: Optional[List[str]] = None
    ) -> Tuple[int, int, List[str]]:
        backup_info = self.load_backup(backup_name)
        if not backup_info:
            return 0, 0, []

        restored_count = 0
        total_files = len(backup_info.files)
        failed_files = []

        zip_path = self.backup_dir / f"{backup_name}.zip"
        has_zip = zip_path.exists()

        if has_zip:
            with zipfile.ZipFile(zip_path, 'r') as zipf:
                for file_info in backup_info.files.values():
                    if files_to_restore and file_info.path not in files_to_restore:
                        continue

                    try:
                        os.makedirs(os.path.dirname(file_info.path), exist_ok=True)
                        arcname = os.path.relpath(file_info.path, '/')
                        zipf.extract(arcname, os.path.dirname(file_info.path))
                        os.utime(file_info.path,
                                 (file_info.modified_time, file_info.modified_time))
                        restored_count += 1
                    except Exception as e:
                        failed_files.append(f"{file_info.path}: {str(e)}")
        else:
            for file_info in backup_info.files.values():
                if files_to_restore and file_info.path not in files_to_restore:
                    continue

                try:
                    os.makedirs(os.path.dirname(file_info.path), exist_ok=True)
                    with open(file_info.path, 'wb') as f:
                        f.seek(file_info.size - 1)
                        f.write(b'\0')
                    os.utime(file_info.path,
                             (file_info.modified_time, file_info.modified_time))
                    restored_count += 1
                except Exception as e:
                    failed_files.append(f"{file_info.path}: {str(e)}")

        return restored_count, total_files, failed_files

    def delete_backup(self, backup_name: str) -> bool:
        try:
            json_file = self.backup_dir / f"{backup_name}.json"
            if json_file.exists():
                json_file.unlink()

            zip_file = self.backup_dir / f"{backup_name}.zip"
            if zip_file.exists():
                zip_file.unlink()

            self.backup_history = [
                b for b in self.backup_history
                if b.timestamp != backup_name.replace('backup_', '')
            ]
            self.save_history()

            return True
        except Exception:
            return False
