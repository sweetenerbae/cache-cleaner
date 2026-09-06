import os
from datetime import datetime
from typing import Callable, Dict, List, Tuple

from backup_system import BackupSystem
from cleanup_logic import CleanupLogic
from gui_builder_v2 import GUIBuilder
from process_guard import close_running_apps, find_running_apps
from restore_window import RestoreWindow
from statistics_store import StatisticsStore
from update_manager import UpdateManager
from utils import (
    BackupType,
    get_all_adobe_paths,
    get_application_cache_paths,
    get_developer_cache_paths,
    get_launcher_cache_paths,
    is_admin,
    request_admin,
)


class CacheCleanerApp:
    def __init__(self):
        self.log_file = "cleanup_log.txt"
        self.backup_system = BackupSystem()
        self.statistics = StatisticsStore(self.backup_system.backup_dir)
        self.update_manager = UpdateManager()
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

        application_paths = get_application_cache_paths()
        selected_application_paths: List[str] = []
        for application, enabled in options.get("applications", {}).items():
            if enabled:
                selected_application_paths.extend(application_paths.get(application, []))
        if selected_application_paths:
            path_groups["Applications"] = selected_application_paths

        launcher_paths = get_launcher_cache_paths()
        selected_launcher_paths: List[str] = []
        for launcher, enabled in options.get("launchers", {}).items():
            if enabled:
                selected_launcher_paths.extend(launcher_paths.get(launcher, []))
        if selected_launcher_paths:
            path_groups["Launchers"] = selected_launcher_paths

        if options.get("developer_mode"):
            developer_paths = get_developer_cache_paths()
            selected_developer_paths: List[str] = []
            for tool, enabled in options.get("developer_tools", {}).items():
                if enabled:
                    selected_developer_paths.extend(developer_paths.get(tool, []))
            if selected_developer_paths:
                path_groups["Developer"] = selected_developer_paths

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
        total_size = sum(category_totals.values())
        lines = [f"Можно освободить: {self.cleanup_logic.format_size(total_size)}", ""]
        category_names = {
            "Windows": "Windows",
            "Adobe": "Adobe",
            "Discord": "Discord",
            "Browsers": "Браузеры",
            "Applications": "Приложения",
            "Launchers": "Игровые лаунчеры",
            "Developer": "Режим разработчика",
            "Recycle Bin": "Корзина",
        }

        if category_totals:
            lines.append("По категориям:")
            for category, size in category_totals.items():
                lines.append(
                    f"- {category_names.get(category, category)}: {self.cleanup_logic.format_size(size)}"
                )
            lines.append("")

        non_empty_results = [(path, size) for path, size in scan_results if size > 0]
        if non_empty_results:
            lines.append("Самые большие папки:")
            for path, size in sorted(non_empty_results, key=lambda item: item[1], reverse=True)[:5]:
                lines.append(f"- {self.cleanup_logic.format_size(size)} — {path}")
        elif total_size == 0:
            lines.append("Подходящие папки найдены, но размер кэша сейчас почти нулевой.")
        else:
            lines.append("Основной объём находится в корзине Windows.")

        return "\n".join(lines)

    def perform_cleanup(self, options: Dict, progress_callback: Callable):
        try:
            path_groups = self.collect_paths_to_clean(options)
            paths_to_clean = [path for paths in path_groups.values() for path in paths]

            recycle_selected = options.get("recycle_bin", False)
            if not paths_to_clean and not recycle_selected:
                self.gui_builder.show_message("Внимание", "Не выбрано данных для очистки")
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
            freed_by_category: Dict[str, int] = {}
            self.cleanup_logic.reset_cleanup_stats()
            progress_callback(50, "Очистка файлов...")

            for category, paths in path_groups.items():
                category_freed = 0
                for path in paths:
                    category_freed += self.cleanup_logic.clear_directory(path)
                freed_by_category[category] = category_freed
                total_freed += category_freed

            if recycle_selected:
                recycle_freed = self.cleanup_logic.empty_recycle_bin()
                freed_by_category["Recycle Bin"] = recycle_freed
                total_freed += recycle_freed

            progress_callback(90, "Проверяем результат...")
            remaining_results = self.cleanup_logic.preview_paths(paths_to_clean)
            remaining_by_category: Dict[str, int] = {}
            for category, paths in path_groups.items():
                remaining_by_category[category] = sum(
                    size for path, size in remaining_results if path in paths
                )
            if recycle_selected:
                remaining_by_category["Recycle Bin"] = self.cleanup_logic.recycle_bin_size()
            remaining_total = sum(remaining_by_category.values())
            self.gui_builder.update_dashboard(
                remaining_by_category,
                remaining_total,
                "осталось после очистки",
            )

            progress_callback(100, "Очистка завершена")

            try:
                self.statistics.record_cleanup(
                    total_freed,
                    self.cleanup_logic.deleted_files,
                    freed_by_category,
                )
            except (OSError, ValueError, TypeError) as error:
                self.log(f"STATISTICS ERROR: {error}")

            message = f"Очищено: {self.cleanup_logic.format_size(total_freed)}"
            message += f"\nОсталось: {self.cleanup_logic.format_size(remaining_total)}"
            if self.cleanup_logic.skipped_files:
                message += (
                    f"\nПропущено занятых файлов: {self.cleanup_logic.skipped_files}"
                    f" ({self.cleanup_logic.format_size(self.cleanup_logic.skipped_bytes)})"
                )
            if backup_name:
                message += f"\nБэкап сохранен: {backup_name}"
                message += "\nНе забудьте удалить ненужный бэкап — он занимает место на диске."

            deleted_backups, deleted_backup_bytes = self.backup_system.delete_expired_backups(
                exclude_names={backup_name} if backup_name else set()
            )
            if deleted_backups:
                message += (
                    f"\nАвтоочистка удалила старых бэкапов: {deleted_backups}"
                    f" ({self.cleanup_logic.format_size(deleted_backup_bytes)})"
                )

            self.gui_builder.refresh_statistics()
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

            recycle_selected = options.get("recycle_bin", False)
            if not paths_to_scan and not recycle_selected:
                self.gui_builder.show_message("Внимание", "Не найдено данных для сканирования")
                return

            progress_callback(20, "Сканирование кэша...")
            scan_results = self.cleanup_logic.preview_paths(paths_to_scan)

            category_totals: Dict[str, int] = {}
            for category, paths in path_groups.items():
                category_totals[category] = sum(size for path, size in scan_results if path in paths)
            if recycle_selected:
                category_totals["Recycle Bin"] = self.cleanup_logic.recycle_bin_size()

            progress_callback(100, "Сканирование завершено")
            self.gui_builder.show_scan_results(
                "Результат сканирования",
                self._build_scan_message(scan_results, category_totals),
                category_totals,
                sum(category_totals.values()),
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
            statistics_callback=self.statistics.snapshot,
            running_apps_callback=find_running_apps,
            close_apps_callback=close_running_apps,
            check_update_callback=self.update_manager.check_latest,
            install_update_callback=self.update_manager.download_and_install,
        )

        root = self.gui_builder.setup_gui()
        root.mainloop()


def main():
    app = CacheCleanerApp()
    app.run()


if __name__ == "__main__":
    main()
