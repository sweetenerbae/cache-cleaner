import ctypes
import glob
import os
import subprocess
import sys
import traceback
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

import customtkinter as ctk
import winreg
from tkinter import filedialog, messagebox


@dataclass
class BrowserInfo:
    name: str
    cache_paths: List[str]


class CacheCleaner:
    def __init__(self, log_file: str = "clear_cache_log.txt"):
        self.log_file = log_file
        self.user_folder: Optional[str] = None
        self.browsers: Dict[str, BrowserInfo] = {}
        self.initialize_browsers()

    @staticmethod
    def _expand_env_path(*parts: Optional[str]) -> Optional[str]:
        """Собирает путь только если все его части существуют."""
        if any(not part for part in parts):
            return None
        return os.path.join(*parts)

    @staticmethod
    def _normalize_existing_paths(paths: List[Optional[str]]) -> List[str]:
        unique_paths: List[str] = []
        seen = set()

        for path in paths:
            if not path:
                continue
            normalized_path = os.path.normpath(path)
            lowered_path = normalized_path.lower()
            if lowered_path not in seen and os.path.exists(normalized_path):
                seen.add(lowered_path)
                unique_paths.append(normalized_path)

        return unique_paths

    def _get_browser_profile_paths(self, *parts: str) -> List[str]:
        local_app_data = os.getenv("LOCALAPPDATA")
        user_data_root = self._expand_env_path(local_app_data, *parts)
        if not user_data_root:
            return []

        profiles = glob.glob(os.path.join(user_data_root, "*"))
        cache_paths = []
        for profile_path in profiles:
            if os.path.isdir(profile_path):
                cache_paths.append(os.path.join(profile_path, "Cache"))

        return self._normalize_existing_paths(cache_paths)

    def initialize_browsers(self):
        """Инициализация информации о браузерах."""
        app_data = os.getenv("APPDATA")

        firefox_profiles = []
        if app_data:
            firefox_profiles = [
                os.path.join(profile_path, "cache2")
                for profile_path in glob.glob(os.path.join(app_data, "Mozilla", "Firefox", "Profiles", "*"))
                if os.path.isdir(profile_path)
            ]

        self.browsers = {
            "chrome": BrowserInfo(
                "Chrome",
                self._get_browser_profile_paths("Google", "Chrome", "User Data"),
            ),
            "firefox": BrowserInfo(
                "Firefox",
                self._normalize_existing_paths(firefox_profiles),
            ),
            "edge": BrowserInfo(
                "Edge",
                self._get_browser_profile_paths("Microsoft", "Edge", "User Data"),
            ),
            "brave": BrowserInfo(
                "Brave",
                self._get_browser_profile_paths("BraveSoftware", "Brave-Browser", "User Data"),
            ),
            "yandex": BrowserInfo(
                "Yandex",
                self._get_browser_profile_paths("Yandex", "YandexBrowser", "User Data"),
            ),
        }

    @staticmethod
    def is_admin() -> bool:
        """Проверка прав администратора."""
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except OSError:
            return False

    def request_admin(self):
        """Запрос прав администратора."""
        executable = sys.executable
        script_args = subprocess.list2cmdline(sys.argv)
        ctypes.windll.shell32.ShellExecuteW(None, "runas", executable, script_args, None, 1)
        sys.exit()

    def log(self, text: str):
        """Логирование в файл."""
        try:
            with open(self.log_file, "a", encoding="utf-8") as log_file:
                log_file.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {text}\n")
        except OSError as error:
            print(f"Log error: {error}")

    @staticmethod
    def calculate_folder_size(path: str) -> int:
        """Вычисление размера папки в байтах."""
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
        except OSError:
            return 0

        return total

    @staticmethod
    def is_safe_cleanup_path(path: str) -> bool:
        """Защита от очистки слишком широких или системных корней."""
        normalized_path = os.path.normpath(path)
        drive, tail = os.path.splitdrive(normalized_path)
        trimmed_tail = tail.strip("\\/")

        if not drive:
            return False

        if not trimmed_tail:
            return False

        path_parts = [part for part in trimmed_tail.split(os.sep) if part]
        return len(path_parts) >= 2

    def clear_directory(self, path: str) -> float:
        """Очистка папки с возвратом освобождённого места."""
        if not path or not os.path.exists(path) or not self.is_safe_cleanup_path(path):
            if path:
                self.log(f"Skipped unsafe or missing path: {path}")
            return 0.0

        try:
            size_before = self.calculate_folder_size(path)

            for root, dirs, files in os.walk(path, topdown=False):
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    try:
                        os.remove(file_path)
                    except (PermissionError, OSError):
                        continue

                for dir_name in dirs:
                    dir_path = os.path.join(root, dir_name)
                    try:
                        os.rmdir(dir_path)
                    except (PermissionError, OSError):
                        continue

            size_after = self.calculate_folder_size(path)
            freed_bytes = max(0, size_before - size_after)
            freed_gb = freed_bytes / (1024 ** 3)

            self.log(f"Cleared: {path} | Freed: {freed_gb:.2f} GB")
            return freed_gb

        except OSError as error:
            self.log(f"Error clearing {path}: {error}")
            return 0.0

    def get_adobe_cache_paths(self) -> Dict[str, List[str]]:
        """Получение путей к кэшу Adobe из реестра."""
        result: Dict[str, List[str]] = {}
        apps = ["AfterFX", "Premiere Pro", "Photoshop", "Media Encoder"]

        for app in apps:
            paths: List[str] = []
            try:
                reg_path = f"Software\\Adobe\\{app}"
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path) as key:
                    subkey_count = winreg.QueryInfoKey(key)[0]
                    for index in range(subkey_count):
                        version_key = winreg.EnumKey(key, index)
                        subkey_path = f"{reg_path}\\{version_key}"

                        try:
                            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, subkey_path) as subkey:
                                for cache_key in ("MediaCachePath", "MediaCacheFilesPath"):
                                    try:
                                        value, _ = winreg.QueryValueEx(subkey, cache_key)
                                        if value:
                                            paths.append(value)
                                    except FileNotFoundError:
                                        continue
                        except (FileNotFoundError, PermissionError, OSError):
                            continue
            except FileNotFoundError:
                continue

            unique_existing_paths = self._normalize_existing_paths(paths)
            if unique_existing_paths:
                result[app] = unique_existing_paths

        return result

    def cleanup_windows(self) -> float:
        """Очистка временных файлов Windows."""
        freed = 0.0
        windir = os.getenv("WINDIR")
        local_app_data = os.getenv("LOCALAPPDATA")

        temp_paths = self._normalize_existing_paths(
            [
                os.getenv("TEMP"),
                self._expand_env_path(windir, "Temp"),
                r"C:\Windows\Prefetch",
                self._expand_env_path(local_app_data, "Temp"),
            ]
        )

        for path in temp_paths:
            freed += self.clear_directory(path)

        try:
            subprocess.run(
                ["wsreset.exe"],
                capture_output=True,
                text=True,
                check=False,
                shell=False,
            )
        except OSError:
            self.log("wsreset.exe is unavailable on this system")

        return freed

    def cleanup_adobe(self, custom_path: Optional[str] = None) -> float:
        """Очистка кэша Adobe."""
        freed = 0.0

        adobe_paths = self.get_adobe_cache_paths()
        for app_paths in adobe_paths.values():
            for path in app_paths:
                freed += self.clear_directory(path)

        if custom_path and os.path.exists(custom_path):
            freed += self.clear_directory(custom_path)

        return freed

    def cleanup_discord(self) -> float:
        """Очистка кэша Discord."""
        freed = 0.0
        app_data = os.getenv("APPDATA")
        local_app_data = os.getenv("LOCALAPPDATA")

        discord_cache_paths = self._normalize_existing_paths(
            [
                self._expand_env_path(app_data, "discord", "Cache"),
                self._expand_env_path(app_data, "discord", "Code Cache"),
                self._expand_env_path(app_data, "discord", "GPUCache"),
                self._expand_env_path(local_app_data, "Discord", "Cache"),
            ]
        )

        for path in discord_cache_paths:
            freed += self.clear_directory(path)

        return freed

    def cleanup_browsers(self, selected_browsers: Dict[str, bool]) -> float:
        """Очистка кэша браузеров."""
        freed = 0.0

        for browser_name, enabled in selected_browsers.items():
            if enabled and browser_name in self.browsers:
                browser = self.browsers[browser_name]
                for cache_path in browser.cache_paths:
                    freed += self.clear_directory(cache_path)

        return freed

    def run_full_cleanup(
        self,
        clean_windows: bool,
        clean_adobe: bool,
        clean_discord: bool,
        browsers_to_clean: Dict[str, bool],
        adobe_custom_path: Optional[str] = None,
        progress_callback=None,
    ) -> float:
        """Основная функция очистки."""
        self.log("=" * 50)
        self.log(f"Cleanup started: {datetime.now()}")
        self.log("User: hidden")

        total_freed = 0.0
        steps = []

        if clean_windows:
            steps.append(("Windows Temp", lambda: self.cleanup_windows()))
        if clean_adobe:
            steps.append(("Adobe Cache", lambda: self.cleanup_adobe(adobe_custom_path)))
        if clean_discord:
            steps.append(("Discord Cache", lambda: self.cleanup_discord()))
        if any(browsers_to_clean.values()):
            steps.append(("Browsers", lambda: self.cleanup_browsers(browsers_to_clean)))

        if not steps:
            self.log("Cleanup skipped: nothing selected")
            return total_freed

        for step_number, (name, cleanup_func) in enumerate(steps, 1):
            if progress_callback:
                progress_callback((step_number - 1) * 100 // len(steps), f"Очистка: {name}...")

            freed = cleanup_func()
            total_freed += freed
            self.log(f"{name}: Freed {freed:.2f} GB")

        if progress_callback:
            progress_callback(100, "Очистка завершена!")

        self.log(f"Total Freed: {total_freed:.2f} GB")
        self.log(f"Cleanup finished: {datetime.now()}")
        self.log("=" * 50)

        return total_freed


class CacheCleanerGUI:
    def __init__(self):
        self.cleaner = CacheCleaner()
        self.root = ctk.CTk()
        self.setup_gui()

    def setup_gui(self):
        """Настройка графического интерфейса."""
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.root.title("Cache Cleaner Pro")
        self.root.geometry("550x500")
        self.root.resizable(False, False)

        title = ctk.CTkLabel(
            self.root,
            text="Очистка кэша системы",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        title.pack(pady=10)

        self.var_windows = ctk.BooleanVar(value=True)
        self.var_adobe = ctk.BooleanVar(value=True)
        self.var_discord = ctk.BooleanVar(value=True)

        ctk.CTkCheckBox(
            self.root,
            text="Windows временные файлы",
            variable=self.var_windows,
        ).pack(pady=5, anchor="w", padx=20)
        ctk.CTkCheckBox(
            self.root,
            text="Adobe Cache",
            variable=self.var_adobe,
        ).pack(pady=5, anchor="w", padx=20)
        ctk.CTkCheckBox(
            self.root,
            text="Discord Cache",
            variable=self.var_discord,
        ).pack(pady=5, anchor="w", padx=20)

        self.setup_browsers_frame()

        self.btn_adobe_folder = ctk.CTkButton(
            self.root,
            text="Выбрать папку кэша Adobe",
            command=self.choose_adobe_folder,
            width=220,
        )
        self.btn_adobe_folder.pack(pady=10)

        self.lbl_adobe_folder = ctk.CTkLabel(
            self.root,
            text="Не выбрано",
            text_color="gray",
        )
        self.lbl_adobe_folder.pack()

        self.progress = ctk.CTkProgressBar(self.root, width=400)
        self.progress.set(0)
        self.progress.pack(pady=20)

        self.lbl_status = ctk.CTkLabel(self.root, text="Готово к очистке")
        self.lbl_status.pack()

        self.btn_clean = ctk.CTkButton(
            self.root,
            text="Запустить очистку",
            command=self.start_cleanup,
            height=40,
            font=ctk.CTkFont(size=14),
        )
        self.btn_clean.pack(pady=10)

        info = ctk.CTkLabel(
            self.root,
            text="Логи сохраняются в файл clear_cache_log.txt",
            font=ctk.CTkFont(size=10),
        )
        info.pack(pady=5)

    def setup_browsers_frame(self):
        """Настройка фрейма с выбором браузеров."""
        frame = ctk.CTkFrame(self.root)
        frame.pack(pady=10, padx=20, fill="x")

        ctk.CTkLabel(
            frame,
            text="Браузеры:",
            font=ctk.CTkFont(weight="bold"),
        ).pack(anchor="w", padx=10, pady=5)

        self.browser_vars = {}
        for browser_id, browser_info in self.cleaner.browsers.items():
            var = ctk.BooleanVar(value=True)
            self.browser_vars[browser_id] = var

            ctk.CTkCheckBox(
                frame,
                text=browser_info.name,
                variable=var,
            ).pack(anchor="w", padx=20, pady=2)

    def choose_adobe_folder(self):
        """Выбор пользовательской папки Adobe."""
        folder = filedialog.askdirectory(title="Выберите папку кэша Adobe")
        if folder:
            self.cleaner.user_folder = folder
            display_name = os.path.basename(folder) if len(folder) < 40 else f"{folder[:37]}..."
            self.lbl_adobe_folder.configure(
                text=f"Выбрано: {display_name}",
                text_color="white",
            )

    def update_progress(self, value: int, status: str):
        """Обновление прогресса."""
        self.progress.set(max(0, min(value, 100)) / 100)
        self.lbl_status.configure(text=status)
        self.root.update_idletasks()

    def start_cleanup(self):
        """Запуск процесса очистки."""
        browsers_to_clean = {
            browser_id: var.get()
            for browser_id, var in self.browser_vars.items()
        }

        if not any(
            [
                self.var_windows.get(),
                self.var_adobe.get(),
                self.var_discord.get(),
                any(browsers_to_clean.values()),
            ]
        ):
            messagebox.showwarning("Нечего очищать", "Выберите хотя бы один тип очистки.")
            return

        try:
            self.btn_clean.configure(state="disabled")
            self.update_progress(0, "Подготовка к очистке...")

            total_freed = self.cleaner.run_full_cleanup(
                clean_windows=self.var_windows.get(),
                clean_adobe=self.var_adobe.get(),
                clean_discord=self.var_discord.get(),
                browsers_to_clean=browsers_to_clean,
                adobe_custom_path=self.cleaner.user_folder,
                progress_callback=self.update_progress,
            )

            messagebox.showinfo(
                "Готово",
                "Очистка завершена успешно!\n\n"
                f"Освобождено: {total_freed:.2f} ГБ\n"
                "Детали в лог-файле.",
            )
        except Exception as error:
            messagebox.showerror("Ошибка", f"Произошла ошибка:\n{error}")
            self.cleaner.log(f"ERROR: {traceback.format_exc()}")
        finally:
            self.btn_clean.configure(state="normal")
            self.progress.set(0)
            self.lbl_status.configure(text="Готово к очистке")

    def run(self):
        """Запуск приложения."""
        self.root.mainloop()


def main():
    cleaner = CacheCleaner()
    if not cleaner.is_admin():
        cleaner.request_admin()
        return

    app = CacheCleanerGUI()
    app.run()


if __name__ == "__main__":
    main()
