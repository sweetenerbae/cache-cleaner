import os
import sys
from typing import Dict, List, Optional, Tuple

from utils import get_all_adobe_paths, get_browser_paths


class CleanupLogic:
    def __init__(self, logger=None):
        self.logger = logger
        self.browser_paths = get_browser_paths()
        self.skipped_files = 0
        self.skipped_bytes = 0
        runtime_dir = getattr(sys, "_MEIPASS", None)
        self.protected_paths = [os.path.normcase(os.path.abspath(runtime_dir))] if runtime_dir else []

    def log(self, text: str):
        if self.logger:
            self.logger(text)

    @staticmethod
    def format_size(size_bytes: int) -> str:
        if size_bytes >= 1024 ** 3:
            return f"{size_bytes / (1024 ** 3):.2f} GB"
        if size_bytes >= 1024 ** 2:
            return f"{size_bytes / (1024 ** 2):.2f} MB"
        if size_bytes >= 1024:
            return f"{size_bytes / 1024:.2f} KB"
        return f"{size_bytes} B"

    def reset_cleanup_stats(self):
        self.skipped_files = 0
        self.skipped_bytes = 0

    def _is_protected_path(self, path: str) -> bool:
        normalized = os.path.normcase(os.path.abspath(path))
        return any(
            normalized == protected or normalized.startswith(protected + os.sep)
            for protected in self.protected_paths
        )

    def _calculate_cleanable_size(self, path: str) -> int:
        total = 0
        if not path or not os.path.exists(path):
            return total
        try:
            for root, dirs, files in os.walk(path):
                dirs[:] = [
                    directory
                    for directory in dirs
                    if not self._is_protected_path(os.path.join(root, directory))
                ]
                if self._is_protected_path(root):
                    continue
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    if self._is_protected_path(file_path):
                        continue
                    try:
                        total += os.path.getsize(file_path)
                    except (OSError, PermissionError):
                        continue
        except (OSError, PermissionError):
            pass
        return total

    def clear_directory(self, path: str) -> int:
        if not path or not os.path.exists(path):
            return 0

        try:
            size_before = self._calculate_cleanable_size(path)
            skipped_here = 0

            for root, dirs, files in os.walk(path, topdown=False):
                if self._is_protected_path(root):
                    continue
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    if self._is_protected_path(file_path):
                        continue
                    try:
                        os.remove(file_path)
                    except (PermissionError, OSError):
                        skipped_here += 1
                        self.skipped_files += 1
                        try:
                            self.skipped_bytes += os.path.getsize(file_path)
                        except (OSError, PermissionError):
                            pass
                        continue

                for dir_name in dirs:
                    directory_path = os.path.join(root, dir_name)
                    if self._is_protected_path(directory_path):
                        continue
                    try:
                        os.rmdir(directory_path)
                    except (PermissionError, OSError):
                        continue

            size_after = self._calculate_cleanable_size(path)
            freed_bytes = max(0, size_before - size_after)
            self.log(
                f"Cleared: {path} | Freed: {self.format_size(freed_bytes)}"
                f" | Skipped locked files: {skipped_here}"
            )
            return freed_bytes
        except Exception as error:
            self.log(f"Error clearing {path}: {error}")
            return 0

    def preview_paths(self, paths: List[str]) -> List[Tuple[str, int]]:
        results: List[Tuple[str, int]] = []
        for path in paths:
            results.append((path, self._calculate_cleanable_size(path)))
        return results

    def cleanup_windows_temp(self) -> int:
        freed = 0
        temp_paths = [
            os.getenv("TEMP"),
            os.path.join(os.getenv("WINDIR"), "Temp") if os.getenv("WINDIR") else r"C:\Windows\Temp",
            r"C:\Windows\Prefetch",
            os.path.join(os.getenv("LOCALAPPDATA"), "Temp") if os.getenv("LOCALAPPDATA") else None,
        ]

        unique_paths = list(dict.fromkeys(os.path.normcase(os.path.normpath(path)) for path in filter(None, temp_paths)))
        for path in unique_paths:
            freed += self.clear_directory(path)

        return freed

    def cleanup_adobe(self, custom_path: Optional[str] = None) -> int:
        freed = 0

        for path in get_all_adobe_paths(custom_path):
            freed += self.clear_directory(path)

        return freed

    def cleanup_discord(self) -> int:
        freed = 0
        discord_cache_paths = [
            os.path.join(os.getenv("APPDATA"), "discord", "Cache") if os.getenv("APPDATA") else None,
            os.path.join(os.getenv("APPDATA"), "discord", "Code Cache") if os.getenv("APPDATA") else None,
            os.path.join(os.getenv("APPDATA"), "discord", "GPUCache") if os.getenv("APPDATA") else None,
            os.path.join(os.getenv("LOCALAPPDATA"), "Discord", "Cache") if os.getenv("LOCALAPPDATA") else None,
        ]

        for path in filter(None, discord_cache_paths):
            freed += self.clear_directory(path)

        return freed

    def cleanup_browsers(self, selected_browsers: Dict[str, bool]) -> int:
        freed = 0

        for browser_name, enabled in selected_browsers.items():
            if enabled and browser_name in self.browser_paths:
                for cache_path in self.browser_paths[browser_name]:
                    freed += self.clear_directory(cache_path)

        return freed

    def scan_directory_files(self, path: str) -> List[str]:
        files: List[str] = []
        if not os.path.exists(path):
            return files

        try:
            for root, dirs, filenames in os.walk(path):
                dirs[:] = [
                    directory
                    for directory in dirs
                    if not self._is_protected_path(os.path.join(root, directory))
                ]
                if self._is_protected_path(root):
                    continue
                for filename in filenames:
                    file_path = os.path.join(root, filename)
                    if not self._is_protected_path(file_path):
                        files.append(file_path)
        except Exception:
            pass

        return files
