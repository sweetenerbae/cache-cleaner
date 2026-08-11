import os
import subprocess
from typing import List, Dict, Optional
from .utils import calculate_folder_size, get_adobe_cache_paths, get_browser_paths

class CleanupLogic:
    def __init__(self, logger=None):
        self.logger = logger
        self.browser_paths = get_browser_paths()

    def log(self, text: str):
        # logfile
        if self.logger:
            self.logger(text)

    def clear_directory(self, path: str) -> float:
        if not path or not os.path.exists(path):
            return 0.0

        try:
            size_before = calculate_folder_size(path)

            # removing files from directory
            for root, dirs, files in os.walk(path):
                for file in files:
                    try:
                        file_path = os.path.join(root, file)
                        os.remove(file_path)
                    except (PermissionError, OSError):
                        continue

            size_after = calculate_folder_size(path)
            freed_bytes = size_before - size_after
            freed_gb = freed_bytes / (1024 ** 3)

            self.log(f"Cleared: {path} | Freed: {freed_gb:.2f} GB")
            return freed_gb

        except Exception as e:
            self.log(f"Error clearing {path}: {str(e)}")
            return 0.0

    # windows cache/temp
    def cleanup_windows_temp(self) -> float:
        freed = 0.0
        temp_paths = [
            os.getenv("TEMP"),
            os.getenv("WINDIR") + "\\Temp" if os.getenv("WINDIR") else r"C:\Windows\Temp",
            r"C:\Windows\Prefetch",
            os.getenv("LOCALAPPDATA") + "\\Temp" if os.getenv("LOCALAPPDATA") else None
        ]

        for path in filter(None, temp_paths):
            freed += self.clear_directory(path)

        try:
            subprocess.run(["wsreset.exe"], shell=True, capture_output=True)
        except Exception:
            pass

        return freed

    # adobe cache
    def cleanup_adobe(self, custom_path: Optional[str] = None) -> float:
        freed = 0.0

        adobe_paths = get_adobe_cache_paths()
        for app_paths in adobe_paths.values():
            for path in app_paths:
                freed += self.clear_directory(path)

        # custom folder
        if custom_path and os.path.exists(custom_path):
            freed += self.clear_directory(custom_path)

        return freed

    # discord cache
    def cleanup_discord(self) -> float:
        freed = 0.0
        discord_cache_paths = [
            os.path.join(os.getenv("APPDATA"), "discord", "Cache"),
            os.path.join(os.getenv("APPDATA"), "discord", "Code Cache"),
            os.path.join(os.getenv("APPDATA"), "discord", "GPUCache"),
            os.path.join(os.getenv("LOCALAPPDATA"), "Discord", "Cache")
        ]

        for path in discord_cache_paths:
            freed += self.clear_directory(path)

        return freed
    
    # browser cache
    def cleanup_browsers(self, selected_browsers: Dict[str, bool]) -> float:
        freed = 0.0

        for browser_name, enabled in selected_browsers.items():
            if enabled and browser_name in self.browser_paths:
                for cache_path in self.browser_paths[browser_name]:
                    freed += self.clear_directory(cache_path)

        return freed

    def scan_directory_files(self, path: str) -> List[str]:
        files = []
        if os.path.exists(path):
            try:
                for root, dirs, filenames in os.walk(path):
                    for filename in filenames:
                        filepath = os.path.join(root, filename)
                        files.append(filepath)
            except Exception:
                pass
        return files