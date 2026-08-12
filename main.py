import os
from datetime import datetime
from typing import Callable, Dict, List, Tuple

from backup_system import BackupSystem
from cleanup_logic import CleanupLogic
from gui_builder import GUIBuilder
from restore_window import RestoreWindow
from utils import BackupType, get_all_adobe_paths, is_admin, request_admin


class CacheCleanerApp:
    def __init__(self):
        self.log_file = "cleanup_log.txt"
        self.backup_system = BackupSystem()
        self.cleanup_logic = CleanupLogic(logger=self.log)
        self.gui_builder = None

    def log(self, text: str):
        try:
            with open(self.log_file, "a", encoding="utf-8") as log_file:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                log_file.write(f"[{timestamp}] {text}\n")
        except Exception:
            pass

    def collect_paths_to_clean(self, options: Dict) -> Dict[str, List[str]]:
        path_groups: Dict[str, List[str]] = {}

        if options["windows"]:
            path_groups["Windows"] = [
                os.getenv("TEMP"),
                r"C:\Windows\Temp",
                r"C:\Windows\Prefetch",
                os.path.join(os.getenv("LOCALAPPDATA"), "Temp") if os.getenv("LOCALAPPDATA") else None,
            ]

        if options["adobe"]:
            path_groups["Adobe"] = get_all_adobe_paths(options.get("adobe_folder"))

        if options["discord"]:
            app_data = os.getenv("APPDATA")
            local_app_data = os.getenv("LOCALAPPDATA")
            path_groups["Discord"] = [
                os.path.join(app_data, "discord", "Cache") if app_data else None,
                os.path.join(app_data, "discord", "Code Cache") if app_data else None,
                os.path.join(app_data, "discord", "GPUCache") if app_data else None,
                os.path.join(local_app_data, "Discord", "Cache") if local_app_data else None,
            ]

        enabled_browser_paths: List[str] = []
        for browser_name, enabled in options["browsers"].items():
            if enabled and browser_name in self.cleanup_logic.browser_paths:
                enabled_browser_paths.extend(self.cleanup_logic.browser_paths[browser_name])

        if enabled_browser_paths:
            path_groups["Browsers"] = enabled_browser_paths

        normalized_groups: Dict[str, List[str]] = {}
        seen_paths = set()

        for category, paths in path_groups.items():
            category_paths: List[str] = []
            for path in paths:
                if not path or not os.path.exists(path):
                    continue

                normalized_path = os.path.normpath(path)
                lowered_path = normalized_path.lower()
                if lowered_path in seen_paths:
                    continue

                seen_paths.add(lowered_path)
                category_paths.append(normalized_path)

            if category_paths:
                normalized_groups[category] = category_paths

        return normalized_groups

    def _build_scan_message(self, scan_results: List[Tuple[str, int]], category_totals: Dict[str, int]) -> str:
        total_size = sum(size for _, size in scan_results)
        lines = [f"Можно освободить: {self.cleanup_logic.format_size(total_size)}", ""]

        if category_totals:
            lines.append("По категориям:")
            for category, size in category_totals.items():
                lines.append(f"- {category}: {self.cleanup_logic.format_size(size)}")
            lines.append("")

        non_empty_results = [(path, size) for path, size in scan_results if size > 0]
        if non_empty_results:
            lines.append("Самые большие папки:")
            for path, size in sorted(non_empty_results, key=lambda item: item[1], reverse=True)[:5]:
                lines.append(f"- {self.cleanup_logic.format_size(size)} — {path}")
        else:
            lines.append("Подходящие папки найдены, но размер кэша сейчас почти нулевой.")

        return "\n".join(lines)

    def perform_cleanup(self, options: Dict, progress_callback: Callable):
        try:
            path_groups = self.collect_paths_to_clean(options)
            paths_to_clean = [path for paths in path_groups.values() for path in paths]

            if not paths_to_clean:
                self.gui_builder.show_message("Внимание", "Не выбрано ни одной папки для очистки")
                return

            backup_name = None
            if options["create_backup"]:
                progress_callback(10, "Создание бэкапа...")

                files_for_backup = []
                for path in paths_to_clean:
                    if os.path.isdir(path):
                        files_for_backup.extend(self.cleanup_logic.scan_directory_files(path))
                    elif os.path.isfile(path):
                        files_for_backup.append(path)

                if files_for_backup:
                    backup_name = self.backup_system.create_backup(
                        files_for_backup,
                        BackupType.SMART,
                        "Автоматический бэкап",
                    )
                    if backup_name:
                        progress_callback(30, f"Бэкап создан: {backup_name}")

            total_freed = 0
            self.cleanup_logic.reset_cleanup_stats()
            progress_callback(50, "Очистка файлов...")

            if options["windows"]:
                total_freed += self.cleanup_logic.cleanup_windows_temp()

            if options["adobe"]:
                total_freed += self.cleanup_logic.cleanup_adobe(options["adobe_folder"])

            if options["discord"]:
                total_freed += self.cleanup_logic.cleanup_discord()

            total_freed += self.cleanup_logic.cleanup_browsers(options["browsers"])

            progress_callback(100, "Очистка завершена")

            message = f"Очищено: {self.cleanup_logic.format_size(total_freed)}"
            if self.cleanup_logic.skipped_files:
                message += (
                    f"\nПропущено занятых файлов: {self.cleanup_logic.skipped_files}"
                    f" ({self.cleanup_logic.format_size(self.cleanup_logic.skipped_bytes)})"
                )
            if backup_name:
                message += f"\nБэкап сохранен: {backup_name}"

            self.gui_builder.show_message("Готово", message)
        except Exception as error:
            self.gui_builder.show_message("Ошибка", f"Ошибка при очистке:\n{error}", True)
            self.log(f"ERROR: {error}")
        finally:
            self.gui_builder.reset_progress()

    def perform_scan(self, options: Dict, progress_callback: Callable):
        try:
            path_groups = self.collect_paths_to_clean(options)
            paths_to_scan = [path for paths in path_groups.values() for path in paths]

            if not paths_to_scan:
                self.gui_builder.show_message("Внимание", "Не найдено папок для сканирования")
                return

            progress_callback(20, "Сканирование кэша...")
            scan_results = self.cleanup_logic.preview_paths(paths_to_scan)

            category_totals: Dict[str, int] = {}
            for category, paths in path_groups.items():
                category_totals[category] = sum(size for path, size in scan_results if path in paths)

            progress_callback(100, "Сканирование завершено")
            self.gui_builder.show_scan_results(
                "Результат сканирования",
                self._build_scan_message(scan_results, category_totals),
                category_totals,
                sum(size for _, size in scan_results),
            )
        except Exception as error:
            self.gui_builder.show_message("Ошибка", f"Ошибка при сканировании:\n{error}", True)
            self.log(f"SCAN ERROR: {error}")
        finally:
            self.gui_builder.reset_progress()

    def open_restore_manager(self):
        try:
            RestoreWindow(self.gui_builder.root, self.backup_system)
        except Exception as error:
            self.log(f"BACKUP WINDOW ERROR: {error}")
            self.gui_builder.show_message(
                "Ошибка бэкапа",
                f"Не удалось открыть центр восстановления:\n{error}",
                True,
            )

    def run(self):
        if not is_admin():
            request_admin()
            return

        self.gui_builder = GUIBuilder(
            cleanup_callback=self.perform_cleanup,
            restore_callback=self.open_restore_manager,
            scan_callback=self.perform_scan,
        )

        root = self.gui_builder.setup_gui()
        root.mainloop()


def main():
    app = CacheCleanerApp()
    app.run()


if __name__ == "__main__":
    main()
