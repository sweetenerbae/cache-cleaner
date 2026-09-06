import csv
import io
import subprocess
from typing import Dict, List


PROCESS_GROUPS = {
    "chrome": [("chrome.exe", "Google Chrome", "chrome")],
    "firefox": [("firefox.exe", "Mozilla Firefox", "firefox")],
    "edge": [("msedge.exe", "Microsoft Edge", "edge")],
    "brave": [("brave.exe", "Brave", "brave")],
    "yandex": [("browser.exe", "Яндекс Браузер", "yandex")],
    "telegram": [("telegram.exe", "Telegram", "telegram")],
    "teams": [("ms-teams.exe", "Microsoft Teams", "teams"), ("teams.exe", "Microsoft Teams", "teams")],
    "spotify": [("spotify.exe", "Spotify", "spotify")],
    "discord": [("discord.exe", "Discord", "discord")],
    "steam": [("steam.exe", "Steam", "steam")],
    "epic": [("epicgameslauncher.exe", "Epic Games Launcher", "epic")],
    "battlenet": [("battle.net.exe", "Battle.net", "battlenet")],
}


def _selected_groups(options: Dict) -> set:
    selected = {key for key, enabled in options.get("browsers", {}).items() if enabled}
    selected.update(key for key, enabled in options.get("applications", {}).items() if enabled)
    selected.update(key for key, enabled in options.get("launchers", {}).items() if enabled)
    if options.get("discord"):
        selected.add("discord")
    return selected


def find_running_apps(options: Dict) -> List[Dict]:
    selected = _selected_groups(options)
    if not selected:
        return []
    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        result = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=creation_flags,
            timeout=8,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    known = {}
    for group in selected:
        for executable, display_name, icon in PROCESS_GROUPS.get(group, []):
            known[executable.lower()] = (display_name, icon)
    found = {}
    for row in csv.reader(io.StringIO(result.stdout)):
        if len(row) < 2:
            continue
        executable = row[0].strip().lower()
        if executable not in known:
            continue
        try:
            pid = int(row[1].replace(",", "").replace(" ", ""))
        except ValueError:
            continue
        display_name, icon = known[executable]
        entry = found.setdefault(
            executable,
            {"executable": executable, "name": display_name, "icon": icon, "pids": []},
        )
        entry["pids"].append(pid)
    return sorted(found.values(), key=lambda item: item["name"].lower())


def close_running_apps(apps: List[Dict]) -> List[str]:
    failed = []
    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    for app in apps:
        succeeded = True
        for pid in app.get("pids", []):
            try:
                result = subprocess.run(
                    ["taskkill", "/PID", str(pid)],
                    capture_output=True,
                    creationflags=creation_flags,
                    timeout=8,
                    check=False,
                )
                succeeded = succeeded and result.returncode == 0
            except (OSError, subprocess.SubprocessError):
                succeeded = False
        if not succeeded:
            failed.append(app.get("name", app.get("executable", "Приложение")))
    return failed
