from datetime import datetime
from tkinter import messagebox
from typing import Dict, Set

import customtkinter as ctk

from backup_system import BackupSystem


class RestoreWindow:
    BG = "#0B0D10"
    SURFACE = "#12151A"
    SURFACE_ALT = "#181C23"
    BORDER = "#262C35"
    TEXT = "#F3F5F7"
    MUTED = "#8D96A5"
    ACCENT = "#6C8CFF"
    ACCENT_HOVER = "#5879EC"
    CYAN = "#54D6C2"
    RED = "#F07178"

    def __init__(self, parent, backup_system: BackupSystem):
        self.parent = parent
        self.backup_system = backup_system
        self.selected_backups: Set[str] = set()
        self.backup_rows: Dict[str, ctk.CTkFrame] = {}
        self.backup_vars: Dict[str, ctk.BooleanVar] = {}

        self.window = ctk.CTkToplevel(parent, fg_color=self.BG)
        self.window.title("Бэкапы Cache Cleaner")
        self.window.geometry("820x590")
        self.window.minsize(660, 500)
        self.window.transient(parent)

        self._setup_ui()
        self.load_backups()
        self.window.grab_set()
        self.window.after(100, self.window.focus_force)

    def _setup_ui(self):
        self.window.grid_columnconfigure(0, weight=1)
        self.window.grid_rowconfigure(2, weight=1)

        header = ctk.CTkFrame(self.window, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=26, pady=(22, 8))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            header,
            text="Центр восстановления",
            text_color=self.TEXT,
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            header,
            text="Можно отметить сразу несколько копий для быстрого удаления",
            text_color=self.MUTED,
            font=ctk.CTkFont(family="Segoe UI", size=11),
        ).grid(row=1, column=0, sticky="w", pady=(3, 0))

        selection_bar = ctk.CTkFrame(self.window, fg_color="transparent")
        selection_bar.grid(row=1, column=0, sticky="ew", padx=26, pady=(0, 9))
        selection_bar.grid_columnconfigure(0, weight=1)
        self.selection_label = ctk.CTkLabel(
            selection_bar,
            text="Ничего не выбрано",
            text_color=self.MUTED,
            font=ctk.CTkFont(family="Segoe UI", size=11),
        )
        self.selection_label.grid(row=0, column=0, sticky="w")
        ctk.CTkButton(
            selection_bar,
            text="Снять выбор",
            command=self.clear_selection,
            width=96,
            height=30,
            corner_radius=9,
            fg_color="transparent",
            hover_color="#20252C",
            text_color=self.MUTED,
            font=ctk.CTkFont(family="Segoe UI", size=10),
        ).grid(row=0, column=1, padx=(6, 0))
        ctk.CTkButton(
            selection_bar,
            text="Выбрать все",
            command=self.select_all,
            width=96,
            height=30,
            corner_radius=9,
            fg_color="#202631",
            hover_color="#2B3340",
            font=ctk.CTkFont(family="Segoe UI", size=10),
        ).grid(row=0, column=2, padx=(6, 0))

        self.list_frame = ctk.CTkScrollableFrame(
            self.window,
            fg_color=self.SURFACE,
            border_width=1,
            border_color=self.BORDER,
            corner_radius=16,
            scrollbar_button_color=self.BORDER,
            scrollbar_button_hover_color="#3A4350",
        )
        self.list_frame.grid(row=2, column=0, sticky="nsew", padx=26, pady=(0, 13))
        self.list_frame.grid_columnconfigure(0, weight=1)

        actions = ctk.CTkFrame(self.window, fg_color=self.SURFACE, corner_radius=15)
        actions.grid(row=3, column=0, sticky="ew", padx=26, pady=(0, 22))
        actions.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            actions,
            text="Удаляйте старые бэкапы, чтобы не занимать место на диске",
            text_color=self.MUTED,
            font=ctk.CTkFont(family="Segoe UI", size=10),
        ).grid(row=0, column=0, sticky="w", padx=15)

        self.btn_delete = ctk.CTkButton(
            actions,
            text="Удалить",
            command=self.delete,
            width=112,
            height=40,
            corner_radius=11,
            fg_color="#2A1C20",
            hover_color="#3A252B",
            text_color=self.RED,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
        )
        self.btn_delete.grid(row=0, column=1, padx=6, pady=13)
        ctk.CTkButton(
            actions,
            text="Закрыть",
            command=self.window.destroy,
            width=100,
            height=40,
            corner_radius=11,
            fg_color=self.BORDER,
            hover_color="#323A46",
            font=ctk.CTkFont(family="Segoe UI", size=11),
        ).grid(row=0, column=2, padx=6, pady=13)
        ctk.CTkButton(
            actions,
            text="Восстановить",
            command=self.restore,
            width=138,
            height=40,
            corner_radius=11,
            fg_color=self.ACCENT,
            hover_color=self.ACCENT_HOVER,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
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
        self.backup_vars.clear()
        self.selected_backups.clear()
        self._update_selection_ui()

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
                font=ctk.CTkFont(family="Segoe UI", size=17, weight="bold"),
            ).pack()
            ctk.CTkLabel(
                empty,
                text="Они появятся после очистки с включённой защитой",
                text_color=self.MUTED,
                font=ctk.CTkFont(family="Segoe UI", size=11),
            ).pack(pady=(4, 0))
            return

        for row_index, backup in enumerate(backups):
            row = ctk.CTkFrame(
                self.list_frame,
                fg_color=self.SURFACE_ALT,
                border_width=1,
                border_color=self.BORDER,
                corner_radius=13,
                height=84,
            )
            row.grid(row=row_index, column=0, sticky="ew", padx=8, pady=6)
            row.grid_columnconfigure(1, weight=1)
            row.grid_propagate(False)
            self.backup_rows[backup["name"]] = row

            selected_var = ctk.BooleanVar(value=False)
            self.backup_vars[backup["name"]] = selected_var
            ctk.CTkCheckBox(
                row,
                text="",
                variable=selected_var,
                command=lambda name=backup["name"]: self._toggle_backup(name),
                width=22,
                height=22,
                checkbox_width=22,
                checkbox_height=22,
                corner_radius=6,
                border_width=1,
                border_color="#535D6B",
                fg_color=self.ACCENT,
                hover_color=self.ACCENT_HOVER,
            ).grid(row=0, column=0, rowspan=2, padx=(15, 10))

            ctk.CTkLabel(
                row,
                text=self._format_date(backup["timestamp"]),
                text_color=self.TEXT,
                font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            ).grid(row=0, column=1, sticky="sw", pady=(14, 0))

            if backup["archive_exists"]:
                archive_details = f"ZIP {self._format_size(backup['archive_size'])}"
                if backup["saved_percent"] > 0:
                    archive_details += f" · сжато на {backup['saved_percent']}%"
                details = (
                    f"{backup['file_count']} файлов · исходно {self._format_size(backup['total_size'])}"
                    f" · {archive_details}"
                )
                details_color = self.CYAN
            else:
                details = f"{backup['file_count']} файлов · архив не найден"
                details_color = self.RED

            ctk.CTkLabel(
                row,
                text=details,
                text_color=details_color,
                font=ctk.CTkFont(family="Segoe UI", size=10),
            ).grid(row=1, column=1, sticky="nw", pady=(2, 13))

    def _toggle_backup(self, backup_name: str):
        if self.backup_vars[backup_name].get():
            self.selected_backups.add(backup_name)
        else:
            self.selected_backups.discard(backup_name)
        self._update_selection_ui()

    def _update_selection_ui(self):
        count = len(self.selected_backups)
        if count:
            self.selection_label.configure(text=f"Выбрано бэкапов: {count}", text_color=self.TEXT)
            self.btn_delete.configure(text=f"Удалить ({count})")
        else:
            self.selection_label.configure(text="Ничего не выбрано", text_color=self.MUTED)
            self.btn_delete.configure(text="Удалить")

        for name, row in self.backup_rows.items():
            if name in self.selected_backups:
                row.configure(border_color=self.ACCENT, border_width=2, fg_color="#1A202C")
            else:
                row.configure(border_color=self.BORDER, border_width=1, fg_color=self.SURFACE_ALT)

    def select_all(self):
        for name, variable in self.backup_vars.items():
            variable.set(True)
            self.selected_backups.add(name)
        self._update_selection_ui()

    def clear_selection(self):
        for variable in self.backup_vars.values():
            variable.set(False)
        self.selected_backups.clear()
        self._update_selection_ui()

    def restore(self):
        count = len(self.selected_backups)
        if count == 0:
            messagebox.showwarning("Внимание", "Сначала выберите один бэкап", parent=self.window)
            return
        if count > 1:
            messagebox.showwarning(
                "Выбрано несколько бэкапов",
                "Для восстановления выберите только один бэкап. Несколько копий можно удалить одновременно.",
                parent=self.window,
            )
            return

        backup_name = next(iter(self.selected_backups))
        if not messagebox.askyesno(
            "Подтверждение",
            "Восстановить файлы из выбранного бэкапа?",
            parent=self.window,
        ):
            return

        try:
            restored, total, failed = self.backup_system.restore_files(backup_name)
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
            messagebox.showinfo("Готово", f"Успешно восстановлено файлов: {restored}", parent=self.window)

    def delete(self):
        selected = sorted(self.selected_backups)
        if not selected:
            messagebox.showwarning("Внимание", "Отметьте бэкапы для удаления", parent=self.window)
            return

        count = len(selected)
        question = (
            f"Удалить выбранные бэкапы ({count} шт.) без возможности восстановления?"
            if count > 1
            else "Удалить выбранный бэкап без возможности восстановления?"
        )
        if not messagebox.askyesno("Удаление бэкапов", question, parent=self.window):
            return

        failed = [name for name in selected if not self.backup_system.delete_backup(name)]
        deleted_count = count - len(failed)
        self.load_backups()

        if failed:
            messagebox.showwarning(
                "Удаление завершено",
                f"Удалено: {deleted_count} из {count}. Не удалось удалить: {len(failed)}.",
                parent=self.window,
            )
        else:
            messagebox.showinfo(
                "Готово",
                f"Удалено бэкапов: {deleted_count}",
                parent=self.window,
            )
