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


def _existing_unique_paths(paths: List[Optional[str]]) -> List[str]:
    """Return existing paths without case-insensitive duplicates."""
    result = []
    seen = set()
    for path in paths:
        if not path:
            continue
        normalized = os.path.normpath(os.path.expandvars(path))
        key = os.path.normcase(normalized)
        if key not in seen and os.path.exists(normalized):
            seen.add(key)
            result.append(normalized)
    return result


def get_launcher_cache_paths() -> Dict[str, List[str]]:
    """Discover disposable UI/web caches without touching installed games."""
    local = os.getenv("LOCALAPPDATA")
    roaming = os.getenv("APPDATA")
    program_data = os.getenv("PROGRAMDATA")
    program_files_x86 = os.getenv("ProgramFiles(x86)")

    steam_root = None
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as key:
            steam_root, _ = winreg.QueryValueEx(key, "SteamPath")
    except (FileNotFoundError, OSError):
        pass
    if not steam_root and program_files_x86:
        steam_root = os.path.join(program_files_x86, "Steam")

    epic_paths = []
    if local:
        epic_paths.extend(glob.glob(os.path.join(local, "EpicGamesLauncher", "Saved", "webcache*")))

    return {
        "steam": _existing_unique_paths([
            os.path.join(steam_root, "appcache", "httpcache") if steam_root else None,
            os.path.join(steam_root, "config", "htmlcache") if steam_root else None,
            os.path.join(steam_root, "steamui", "cached") if steam_root else None,
        ]),
        "epic": _existing_unique_paths(epic_paths),
        "battlenet": _existing_unique_paths([
            os.path.join(local, "Battle.net", "Cache") if local else None,
            os.path.join(roaming, "Battle.net", "Cache") if roaming else None,
            os.path.join(program_data, "Battle.net", "Agent", "BlizzardCache") if program_data else None,
            os.path.join(program_data, "Blizzard Entertainment", "Battle.net", "Cache") if program_data else None,
        ]),
    }


def get_developer_cache_paths() -> Dict[str, List[str]]:
    """Discover package-manager caches; project sources are never included."""
    local = os.getenv("LOCALAPPDATA")
    user_profile = os.getenv("USERPROFILE")
    return {
        "pip": _existing_unique_paths([
            os.path.join(local, "pip", "Cache") if local else None,
        ]),
        "npm": _existing_unique_paths([
            os.path.join(local, "npm-cache") if local else None,
        ]),
        "pnpm": _existing_unique_paths([
            os.path.join(local, "pnpm", "store") if local else None,
            os.path.join(local, "pnpm-store") if local else None,
        ]),
        "yarn": _existing_unique_paths([
            os.path.join(local, "Yarn", "Cache") if local else None,
            os.path.join(local, "Yarn", "Berry", "cache") if local else None,
        ]),
        "gradle": _existing_unique_paths([
            os.path.join(user_profile, ".gradle", "caches") if user_profile else None,
        ]),
        "nuget": _existing_unique_paths([
            os.path.join(user_profile, ".nuget", "packages") if user_profile else None,
        ]),
    }


def get_application_cache_paths() -> Dict[str, List[str]]:
    """Discover caches for communication and media applications."""
    local = os.getenv("LOCALAPPDATA")
    roaming = os.getenv("APPDATA")

    telegram_paths: List[Optional[str]] = [
        os.path.join(roaming, "Telegram Desktop", "tdata", "temp") if roaming else None,
    ]
    if roaming:
        telegram_data = os.path.join(roaming, "Telegram Desktop", "tdata", "user_data*")
        for user_data in glob.glob(telegram_data):
            telegram_paths.extend([
                os.path.join(user_data, "cache"),
                os.path.join(user_data, "media_cache"),
            ])

    classic_teams = os.path.join(roaming, "Microsoft", "Teams") if roaming else None
    teams_paths: List[Optional[str]] = []
    for folder in ("Cache", "blob_storage", "Code Cache", "GPUCache", "IndexedDB", "Local Storage", "tmp"):
        teams_paths.append(os.path.join(classic_teams, folder) if classic_teams else None)
    teams_paths.append(
        os.path.join(
            local,
            "Packages",
            "MSTeams_8wekyb3d8bbwe",
            "LocalCache",
            "Microsoft",
            "MSTeams",
        ) if local else None
    )

    return {
        "telegram": _existing_unique_paths(telegram_paths),
        "teams": _existing_unique_paths(teams_paths),
        "spotify": _existing_unique_paths([
            os.path.join(roaming, "Spotify", "Browser", "Cache") if roaming else None,
            os.path.join(roaming, "Spotify", "Code Cache") if roaming else None,
            os.path.join(roaming, "Spotify", "GPUCache") if roaming else None,
            os.path.join(local, "Spotify", "Storage") if local else None,
            os.path.join(
                local,
                "Packages",
                "SpotifyAB.SpotifyMusic_zpdnekdrzrea0",
                "LocalCache",
                "Spotify",
                "Data",
            ) if local else None,
        ]),
    }

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
