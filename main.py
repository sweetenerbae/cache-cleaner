import sys
import os
from datetime import datetime
from typing import Dict, Callable
from utils import is_admin, request_admin, BackupType
from cleanup_logic import CleanupLogic
from backup_system import BackupSystem
from gui_builder import GUIBuilder
from restore_window import RestoreWindow


class CacheCleanerApp:
    def __init__(self):
        self.log_file = "cleanup_log.txt"
        self.backup_system = BackupSystem()
        self.cleanup_logic = CleanupLogic(logger=self.log)
        self.gui_builder = None

    def log(self, text: str):
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"[{timestamp}] {text}\n")
        except Exception:
            pass

    def perform_cleanup(self, options: Dict, progress_callback: Callable):
        try:
            paths_to_clean = []

            if options["windows"]:
                paths_to_clean.extend([
                    os.getenv("TEMP"),
                    r"C:\Windows\Temp",
                    r"C:\Windows\Prefetch"
                ])

            if options["adobe"]:
                from utils import get_all_adobe_paths
                adobe_paths = get_all_adobe_paths(options.get("adobe_folder"))
                paths_to_clean.extend([p for p in adobe_paths if os.path.exists(p)])

            if options["discord"]:
                paths_to_clean.extend([
                    os.path.join(os.getenv("APPDATA"), "discord", "Cache"),
                    os.path.join(os.getenv("APPDATA"), "discord", "Code Cache")
                ])

            browser_paths = self.cleanup_logic.browser_paths
            for browser_name, enabled in options["browsers"].items():
                if enabled and browser_name in browser_paths:
                    paths_to_clean.extend(browser_paths[browser_name])

            paths_to_clean = [p for p in paths_to_clean if p and os.path.exists(p)]

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
                        "Автоматический бэкап"
                    )
                    if backup_name:
                        progress_callback(30, f"Бэкап создан: {backup_name}")

            total_freed = 0.0
            progress_callback(50, "Очистка файлов...")

            if options["windows"]:
                total_freed += self.cleanup_logic.cleanup_windows_temp()

            if options["adobe"] and options["adobe_folder"]:
                total_freed += self.cleanup_logic.cleanup_adobe(options["adobe_folder"])

            if options["discord"]:
                total_freed += self.cleanup_logic.cleanup_discord()

            total_freed += self.cleanup_logic.cleanup_browsers(options["browsers"])

            progress_callback(100, "Очистка завершена")

            message = f"Очищено: {total_freed:.2f} GB"
            if backup_name:
                message += f"\nБэкап сохранен: {backup_name}"

            self.gui_builder.show_message("Готово", message)

        except Exception as e:
            self.gui_builder.show_message("Ошибка", f"Ошибка при очистке:\n{str(e)}", True)
            self.log(f"ERROR: {str(e)}")
        finally:
            self.gui_builder.reset_progress()

    def open_restore_manager(self):
        RestoreWindow(self.gui_builder.root, self.backup_system)

    def run(self):
        if not is_admin():
            request_admin()
            return

        self.gui_builder = GUIBuilder(
            cleanup_callback=self.perform_cleanup,
            restore_callback=self.open_restore_manager
        )

        root = self.gui_builder.setup_gui()
        root.mainloop()


def main():
    app = CacheCleanerApp()
    app.run()


if __name__ == "__main__":
    main()