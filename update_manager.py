import hashlib
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable, Dict, Optional, Tuple

from version import APP_VERSION


class UpdateManager:
    API_URL = "https://api.github.com/repos/sweetenerbae/cache-cleaner/releases/latest"
    ASSET_NAME = "cache_clear.exe"
    USER_AGENT = f"CacheCleaner/{APP_VERSION}"

    def __init__(self):
        local_data = os.getenv("LOCALAPPDATA")
        base_dir = Path(local_data) if local_data else Path.home() / "AppData" / "Local"
        self.update_dir = base_dir / "CacheCleaner" / "updates"
        self.update_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _version_tuple(value: str) -> Tuple[int, ...]:
        clean = value.strip().lower().lstrip("v")
        clean = clean.split("-", 1)[0].split("+", 1)[0]
        result = []
        for part in clean.split("."):
            digits = "".join(character for character in part if character.isdigit())
            result.append(int(digits or 0))
        return tuple(result or [0])

    @classmethod
    def _is_newer(cls, latest: str, current: str) -> bool:
        latest_parts = cls._version_tuple(latest)
        current_parts = cls._version_tuple(current)
        length = max(len(latest_parts), len(current_parts))
        return latest_parts + (0,) * (length - len(latest_parts)) > current_parts + (0,) * (length - len(current_parts))

    @staticmethod
    def _request(url: str):
        return urllib.request.Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": UpdateManager.USER_AGENT,
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )

    def check_latest(self) -> Dict:
        try:
            with urllib.request.urlopen(self._request(self.API_URL), timeout=15) as response:
                release = json.load(response)
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return {"status": "no_releases", "current_version": APP_VERSION}
            raise RuntimeError(f"GitHub вернул ошибку HTTP {error.code}") from error
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            raise RuntimeError("Не удалось подключиться к GitHub") from error

        asset = next(
            (
                item for item in release.get("assets", [])
                if str(item.get("name", "")).lower() == self.ASSET_NAME.lower()
            ),
            None,
        )
        latest_version = str(release.get("tag_name", "0.0.0")).lstrip("v")
        return {
            "status": "available" if self._is_newer(latest_version, APP_VERSION) else "current",
            "current_version": APP_VERSION,
            "latest_version": latest_version,
            "name": release.get("name") or f"Cache Cleaner {latest_version}",
            "notes": release.get("body") or "Без описания изменений.",
            "page_url": release.get("html_url", ""),
            "asset": asset,
        }

    def download_and_install(self, release: Dict, progress: Optional[Callable] = None) -> Dict:
        if not getattr(sys, "frozen", False):
            return {"status": "source", "message": "Автообновление доступно в собранной EXE-версии."}
        asset = release.get("asset")
        if not asset or not asset.get("browser_download_url"):
            return {"status": "missing_asset", "message": "В релизе нет файла cache_clear.exe."}

        version = release.get("latest_version", "latest")
        download_path = self.update_dir / f"cache_clear-{version}.download"
        expected_size = int(asset.get("size", 0) or 0)
        digest = str(asset.get("digest", "") or "")
        hasher = hashlib.sha256()
        try:
            with urllib.request.urlopen(
                self._request(asset["browser_download_url"]), timeout=30
            ) as response, download_path.open("wb") as output:
                total = int(response.headers.get("Content-Length", expected_size) or 0)
                downloaded = 0
                while True:
                    chunk = response.read(1024 * 256)
                    if not chunk:
                        break
                    output.write(chunk)
                    hasher.update(chunk)
                    downloaded += len(chunk)
                    if progress and total:
                        progress(min(94, int(downloaded / total * 94)), "Загрузка обновления...")
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            download_path.unlink(missing_ok=True)
            return {"status": "error", "message": f"Не удалось скачать обновление: {error}"}

        actual_size = download_path.stat().st_size
        if expected_size and actual_size != expected_size:
            download_path.unlink(missing_ok=True)
            return {"status": "error", "message": "Размер скачанного файла не совпадает с данными GitHub."}
        try:
            with download_path.open("rb") as file:
                if file.read(2) != b"MZ":
                    raise ValueError("invalid executable")
        except (OSError, ValueError):
            download_path.unlink(missing_ok=True)
            return {"status": "error", "message": "Скачанный файл не является Windows-приложением."}
        if digest.lower().startswith("sha256:") and hasher.hexdigest().lower() != digest.split(":", 1)[1].lower():
            download_path.unlink(missing_ok=True)
            return {"status": "error", "message": "Контрольная сумма обновления не совпала."}

        if progress:
            progress(97, "Подготовка установки...")
        target = Path(sys.executable).resolve()
        script_path = self.update_dir / "install_update.ps1"
        script_path.write_text(
            """param([int]$ProcessId, [string]$Source, [string]$Target)
$ErrorActionPreference = 'Stop'
try { Wait-Process -Id $ProcessId -Timeout 180 -ErrorAction SilentlyContinue } catch {}
$installed = $false
for ($attempt = 0; $attempt -lt 30; $attempt++) {
  try { Copy-Item -LiteralPath $Source -Destination $Target -Force; $installed = $true; break } catch { Start-Sleep -Milliseconds 500 }
}
if ($installed) {
  Start-Process -FilePath $Target
  Remove-Item -LiteralPath $Source -Force -ErrorAction SilentlyContinue
}
Remove-Item -LiteralPath $PSCommandPath -Force -ErrorAction SilentlyContinue
""",
            encoding="utf-8-sig",
        )
        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            subprocess.Popen(
                [
                    "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
                    "-WindowStyle", "Hidden", "-File", str(script_path),
                    str(os.getpid()), str(download_path), str(target),
                ],
                close_fds=True,
                creationflags=creation_flags,
            )
        except OSError as error:
            return {"status": "error", "message": f"Не удалось запустить установку: {error}"}
        if progress:
            progress(100, "Обновление готово к установке")
        return {"status": "scheduled", "message": "Обновление установится после закрытия приложения."}
