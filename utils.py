import os
import ctypes
import sys
import json
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple
from enum import Enum
from pathlib import Path
import winreg
import glob

class BackupType(Enum):
    FULL = "full"
    SMART = "smart"
    METADATA = "metadata"

@dataclass
class FileInfo:
    path: str
    size: int
    modified_time: float
    backup_path: Optional[str] = None

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        return cls(**data)

@dataclass
class BackupInfo:
    timestamp: str
    total_size: int
    file_count: int
    backup_type: str
    description: str
    files: Dict[str, FileInfo]

    def to_dict(self):
        return {
            "timestamp": self.timestamp,
            "total_size": self.total_size,
            "file_count": self.file_count,
            "backup_type": self.backup_type,
            "description": self.description,
            "files": {path: info.to_dict() for path, info in self.files.items()}
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            timestamp=data["timestamp"],
            total_size=data["total_size"],
            file_count=data["file_count"],
            backup_type=data["backup_type"],
            description=data["description"],
            files={path: FileInfo.from_dict(info) for path, info in data["files"].items()}
        )

# admin check
def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def request_admin():
    if getattr(sys, 'frozen', False):
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, "", None, 1)
    else:
        ctypes.windll.shell32.ShellExecuteW(None, "runas", "python", sys.argv[0], None, 1)
    sys.exit()


def calculate_folder_size(path: str) -> int:
    total = 0
    if not os.path.exists(path):
        return 0

    try:
        for dirpath, _, filenames in os.walk(path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                try:
                    if os.path.exists(filepath):
                        total += os.path.getsize(filepath)
                except (OSError, PermissionError):
                    continue
    except Exception:
        return 0
    return total

def get_browser_paths() -> Dict[str, List[str]]:
    browsers = {
        "chrome": [os.path.join(os.getenv("LOCALAPPDATA"), "Google", "Chrome", "User Data", "Default", "Cache")],
        "firefox": [os.path.join(p, "cache2") for p in
                    glob.glob(os.path.join(os.getenv("APPDATA"), "Mozilla", "Firefox", "Profiles", "*"))],
        "edge": [os.path.join(os.getenv("LOCALAPPDATA"), "Microsoft", "Edge", "User Data", "Default", "Cache")],
        "brave": [
            os.path.join(os.getenv("LOCALAPPDATA"), "BraveSoftware", "Brave-Browser", "User Data", "Default", "Cache")],
        "yandex": [os.path.join(os.getenv("LOCALAPPDATA"), "Yandex", "YandexBrowser", "User Data", "Default", "Cache")]
    }
    return browsers

def get_all_adobe_paths(custom_path: Optional[str] = None) -> List[str]:
    all_paths = []

    reg_paths = get_adobe_cache_paths()
    for app_paths in reg_paths.values():
        all_paths.extend([p for p in app_paths if os.path.exists(p)])

    standard_paths = [
        os.path.join(os.getenv("LOCALAPPDATA"), "Adobe", "Common", "Media Cache"),
        os.path.join(os.getenv("LOCALAPPDATA"), "Adobe", "Common", "Media Cache Files"),
        os.path.join(os.getenv("APPDATA"), "Adobe", "Common", "Media Cache"),
        os.path.join(os.getenv("APPDATA"), "Adobe", "Common", "Media Cache Files"),

        # Premiere Pro
        os.path.join(os.getenv("LOCALAPPDATA"), "Adobe", "Premiere Pro", "*", "Media Cache"),
        os.path.join(os.getenv("LOCALAPPDATA"), "Adobe", "Premiere Pro", "*", "Media Cache Files"),
        os.path.join(os.getenv("LOCALAPPDATA"), "Adobe", "Premiere Pro", "*", "Peak Files"),

        # After Effects
        os.path.join(os.getenv("LOCALAPPDATA"), "Adobe", "After Effects", "*", "Disk Cache"),
        os.path.join(os.getenv("LOCALAPPDATA"), "Adobe", "After Effects", "*", "Preview Files"),

        # Media Encoder
        os.path.join(os.getenv("LOCALAPPDATA"), "Adobe", "Adobe Media Encoder", "*", "Media Cache"),

        # Photoshop
        os.path.join(os.getenv("LOCALAPPDATA"), "Adobe", "Photoshop", "*", "Adobe Photoshop Temp*"),

        # Camera Raw Cache
        os.path.join(os.getenv("LOCALAPPDATA"), "Adobe", "CameraRaw", "Cache"),
        os.path.join(os.getenv("APPDATA"), "Adobe", "CameraRaw", "Cache"),
    ]

    for pattern in standard_paths:
        if '*' in pattern:
            expanded_paths = glob.glob(pattern)
            for path in expanded_paths:
                if os.path.exists(path):
                    all_paths.append(path)
        else:
            if os.path.exists(pattern):
                all_paths.append(pattern)

    if custom_path and os.path.exists(custom_path):
        all_paths.append(custom_path)

    return list(set(all_paths))


def get_adobe_cache_paths(apps=None) -> Dict[str, List[str]]:
    if apps is None:
        apps = [
            "AfterFX",
            "Premiere Pro",
            "Photoshop",
            "Media Encoder",
            "Illustrator",
            "Audition",
            "Lightroom",
            "Character Animator",
            "InDesign",
            "Animate"
        ]

    result = {}
    for app in apps:
        paths = []

        reg_keys_to_try = [
            f"Software\\Adobe\\{app}",
            f"Software\\Adobe\\{app.replace(' ', '')}",
            f"Software\\Adobe\\{app.split()[0]}",
        ]

        for reg_path in reg_keys_to_try:
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path) as key:
                    for i in range(winreg.QueryInfoKey(key)[0]):
                        version_key = winreg.EnumKey(key, i)
                        try:
                            subkey_path = f"{reg_path}\\{version_key}"
                            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, subkey_path) as subkey:
                                cache_keys = [
                                    "MediaCachePath",
                                    "MediaCacheFilesPath",
                                    "CacheFolder",
                                    "DiskCacheFolder",
                                    "PreviewCacheFolder",
                                    "PeakFilesFolder",
                                    "WaveformCacheFolder"
                                ]

                                for cache_key in cache_keys:
                                    try:
                                        value, _ = winreg.QueryValueEx(subkey, cache_key)
                                        if value and os.path.exists(value):
                                            paths.append(value)
                                    except FileNotFoundError:
                                        continue
                        except (FileNotFoundError, PermissionError):
                            continue
            except FileNotFoundError:
                continue

        common_cache_keys = [
            "CommonMediaCachePath",
            "CommonMediaCacheFilesPath"
        ]

        for cache_key in common_cache_keys:
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                    f"Software\\Adobe\\Common\\{app}") as key:
                    value, _ = winreg.QueryValueEx(key, cache_key)
                    if value and os.path.exists(value):
                        paths.append(value)
            except (FileNotFoundError, PermissionError):
                continue

        if paths:
            result[app] = list(set(paths))

    return result