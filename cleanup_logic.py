import os
import subprocess
from typing import Dict, List, Optional, Tuple

from utils import calculate_folder_size, get_all_adobe_paths, get_browser_paths


class CleanupLogic:
    def __init__(self, logger=None):
        self.logger = logger
        self.browser_paths = get_browser_paths()

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

    def clear_directory(self, path: str) -> float:
        if not path or not os.path.exists(path):
            return 0.0

        try:
            size_before = calculate_folder_size(path)

            for root, dirs, files in os.walk(path, topdown=False):
                for file_name in files:
                    try:
                        os.remove(os.path.join(root, file_name))
                    except (PermissionError, OSError):
                        continue

                for dir_name in dirs:
                    try:
                        os.rmdir(os.path.join(root, dir_name))
                    except (PermissionError, OSError):
                        continue

            size_after = calculate_folder_size(path)
            freed_bytes = max(0, size_before - size_after)
            freed_gb = freed_bytes / (1024 ** 3)

            self.log(f"Cleared: {path} | Freed: {freed_gb:.2f} GB")
            return freed_gb
        except Exception as error:
            self.log(f"Error clearing {path}: {error}")
            return 0.0

    def preview_paths(self, paths: List[str]) -> List[Tuple[str, int]]:
        results: List[Tuple[str, int]] = []
        for path in paths:
            results.append((path, calculate_folder_size(path)))
        return results

    def cleanup_windows_temp(self) -> float:
        freed = 0.0
        temp_paths = [
            os.getenv("TEMP"),
            os.path.join(os.getenv("WINDIR"), "Temp") if os.getenv("WINDIR") else r"C:\Windows\Temp",
            r"C:\Windows\Prefetch",
            os.path.join(os.getenv("LOCALAPPDATA"), "Temp") if os.getenv("LOCALAPPDATA") else None,
        ]

        for path in filter(None, temp_paths):
            freed += self.clear_directory(path)

        try:
            subprocess.run(["wsreset.exe"], shell=False, capture_output=True, check=False)
        except Exception:
            pass

        return freed

    def cleanup_adobe(self, custom_path: Optional[str] = None) -> float:
        freed = 0.0

        for path in get_all_adobe_paths(custom_path):
            freed += self.clear_directory(path)

        return freed

    def cleanup_discord(self) -> float:
        freed = 0.0
        discord_cache_paths = [
            os.path.join(os.getenv("APPDATA"), "discord", "Cache") if os.getenv("APPDATA") else None,
            os.path.join(os.getenv("APPDATA"), "discord", "Code Cache") if os.getenv("APPDATA") else None,
            os.path.join(os.getenv("APPDATA"), "discord", "GPUCache") if os.getenv("APPDATA") else None,
            os.path.join(os.getenv("LOCALAPPDATA"), "Discord", "Cache") if os.getenv("LOCALAPPDATA") else None,
        ]

        for path in filter(None, discord_cache_paths):
            freed += self.clear_directory(path)

        return freed

    def cleanup_browsers(self, selected_browsers: Dict[str, bool]) -> float:
        freed = 0.0

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
                for filename in filenames:
                    files.append(os.path.join(root, filename))
        except Exception:
            pass

        return files
