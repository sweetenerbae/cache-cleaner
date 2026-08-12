from datetime import datetime
from tkinter import messagebox

import customtkinter as ctk

from backup_system import BackupSystem


class RestoreWindow:
    BG = "#080B14"
    SURFACE = "#101522"
    SURFACE_ALT = "#151B2B"
    BORDER = "#242C40"
    TEXT = "#F5F7FF"
    MUTED = "#8E98AE"
    PURPLE = "#7657FF"
    CYAN = "#32D6C9"
    RED = "#FF647C"

    def __init__(self, parent, backup_system: BackupSystem):
        self.parent = parent
        self.backup_system = backup_system
        self.selected_backup = None
        self.backup_rows = {}

        self.window = ctk.CTkToplevel(parent, fg_color=self.BG)
        self.window.title("Бэкапы Cache Cleaner")
        self.window.geometry("760x540")
        self.window.minsize(620, 460)
        self.window.transient(parent)

        self._setup_ui()
        self.load_backups()
        self.window.grab_set()
        self.window.after(100, self.window.focus_force)

    def _setup_ui(self):
        self.window.grid_columnconfigure(0, weight=1)
        self.window.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self.window, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(22, 12))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            header,
            text="Центр восстановления",
            text_color=self.TEXT,
            font=ctk.CTkFont(size=23, weight="bold"),
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            header,
            text="Выберите сохранённую копию для восстановления",
            text_color=self.MUTED,
            font=ctk.CTkFont(size=12),
        ).grid(row=1, column=0, sticky="w", pady=(3, 0))

        self.list_frame = ctk.CTkScrollableFrame(
            self.window,
            fg_color=self.SURFACE,
            border_width=1,
            border_color=self.BORDER,
            corner_radius=18,
            scrollbar_button_color=self.BORDER,
            scrollbar_button_hover_color=self.PURPLE,
        )
        self.list_frame.grid(row=1, column=0, sticky="nsew", padx=24, pady=(0, 14))
        self.list_frame.grid_columnconfigure(0, weight=1)

        actions = ctk.CTkFrame(
            self.window,
            fg_color=self.SURFACE,
            border_width=1,
            border_color=self.BORDER,
            corner_radius=16,
        )
        actions.grid(row=2, column=0, sticky="ew", padx=24, pady=(0, 22))
        actions.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(
            actions,
            text="Удалить",
            command=self.delete,
            width=105,
            height=40,
            corner_radius=12,
            fg_color="#39202A",
            hover_color="#542D3A",
            text_color=self.RED,
        ).grid(row=0, column=1, padx=6, pady=13)
        ctk.CTkButton(
            actions,
            text="Закрыть",
            command=self.window.destroy,
            width=105,
            height=40,
            corner_radius=12,
            fg_color=self.BORDER,
            hover_color="#303A52",
        ).grid(row=0, column=2, padx=6, pady=13)
        ctk.CTkButton(
            actions,
            text="Восстановить",
            command=self.restore,
            width=145,
            height=40,
            corner_radius=12,
            fg_color=self.PURPLE,
            hover_color="#6545EE",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=0, column=3, padx=(6, 13), pady=13)

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        if size_bytes >= 1024 ** 3:
            return f"{size_bytes / 1024 ** 3:.2f} GB"
        if size_bytes >= 1024 ** 2:
            return f"{size_bytes / 1024 ** 2:.1f} MB"
        if size_bytes >= 1024:
            return f"{size_bytes / 1024:.1f} KB"
        return f"{size_bytes} B"

    @staticmethod
    def _format_date(timestamp: str) -> str:
        for pattern in ("%Y%m%d_%H%M%S_%f", "%Y%m%d_%H%M%S"):
            try:
                return datetime.strptime(timestamp, pattern).strftime("%d.%m.%Y  %H:%M")
            except ValueError:
                continue
        return timestamp

    def load_backups(self):
        for child in self.list_frame.winfo_children():
            child.destroy()
        self.backup_rows.clear()
        self.selected_backup = None

        try:
            backups = self.backup_system.get_available_backups()
        except Exception as error:
            messagebox.showerror("Ошибка", f"Не удалось открыть список бэкапов:\n{error}", parent=self.window)
            return

        if not backups:
            empty = ctk.CTkFrame(self.list_frame, fg_color="transparent")
            empty.grid(row=0, column=0, sticky="nsew", pady=80)
            ctk.CTkLabel(
                empty,
                text="Пока нет бэкапов",
                text_color=self.TEXT,
                font=ctk.CTkFont(size=17, weight="bold"),
            ).pack()
            ctk.CTkLabel(
                empty,
                text="Они появятся здесь после очистки с включённой защитой",
                text_color=self.MUTED,
                font=ctk.CTkFont(size=11),
            ).pack(pady=(5, 0))
            return

        for row_index, backup in enumerate(backups):
            row = ctk.CTkFrame(
                self.list_frame,
                fg_color=self.SURFACE_ALT,
                border_width=1,
                border_color=self.BORDER,
                corner_radius=14,
                height=82,
            )
            row.grid(row=row_index, column=0, sticky="ew", padx=8, pady=6)
            row.grid_columnconfigure(0, weight=1)
            row.grid_propagate(False)
            self.backup_rows[backup["name"]] = row

            ctk.CTkLabel(
                row,
                text=self._format_date(backup["timestamp"]),
                text_color=self.TEXT,
                font=ctk.CTkFont(size=13, weight="bold"),
            ).grid(row=0, column=0, sticky="sw", padx=14, pady=(13, 0))
            archive_status = "готов" if backup["archive_exists"] else "архив не найден"
            details = f"{backup['file_count']} файлов  •  {self._format_size(backup['total_size'])}  •  {archive_status}"
            ctk.CTkLabel(
                row,
                text=details,
                text_color=self.CYAN if backup["archive_exists"] else self.RED,
                font=ctk.CTkFont(size=11),
            ).grid(row=1, column=0, sticky="nw", padx=14, pady=(2, 10))
            ctk.CTkButton(
                row,
                text="Выбрать",
                command=lambda name=backup["name"]: self._select_backup(name),
                width=100,
                height=34,
                corner_radius=11,
                fg_color=self.BORDER,
                hover_color="#303A52",
            ).grid(row=0, column=1, rowspan=2, padx=14)

    def _select_backup(self, backup_name: str):
        self.selected_backup = backup_name
        for name, row in self.backup_rows.items():
            if name == backup_name:
                row.configure(border_color=self.PURPLE, border_width=2, fg_color="#191A32")
            else:
                row.configure(border_color=self.BORDER, border_width=1, fg_color=self.SURFACE_ALT)

    def restore(self):
        if not self.selected_backup:
            messagebox.showwarning("Внимание", "Сначала выберите бэкап", parent=self.window)
            return
        if not messagebox.askyesno(
            "Подтверждение",
            "Восстановить файлы из выбранного бэкапа?",
            parent=self.window,
        ):
            return

        try:
            restored, total, failed = self.backup_system.restore_files(self.selected_backup)
        except Exception as error:
            messagebox.showerror("Ошибка", f"Не удалось восстановить бэкап:\n{error}", parent=self.window)
            return

        if failed:
            details = "\n".join(failed[:4])
            if len(failed) > 4:
                details += f"\n…и ещё {len(failed) - 4}"
            messagebox.showwarning(
                "Восстановление завершено",
                f"Восстановлено: {restored} из {total}\n\n{details}",
                parent=self.window,
            )
        else:
            messagebox.showinfo(
                "Готово",
                f"Успешно восстановлено файлов: {restored}",
                parent=self.window,
            )

    def delete(self):
        if not self.selected_backup:
            messagebox.showwarning("Внимание", "Сначала выберите бэкап", parent=self.window)
            return
        if not messagebox.askyesno(
            "Удаление бэкапа",
            "Удалить выбранный бэкап без возможности восстановления?",
            parent=self.window,
        ):
            return

        if self.backup_system.delete_backup(self.selected_backup):
            self.load_backups()
        else:
            messagebox.showerror("Ошибка", "Не удалось удалить бэкап", parent=self.window)
