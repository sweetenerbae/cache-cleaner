import os
import customtkinter as ctk
from tkinter import ttk, messagebox
from backup_system import BackupSystem


class RestoreWindow:
    def __init__(self, parent, backup_system: BackupSystem):
        self.parent = parent
        self.backup_system = backup_system
        self.selected_backup = None

        self.window = ctk.CTkToplevel(parent)
        self.window.title("Восстановление файлов")
        self.window.geometry("600x400")

        self.setup_ui()
        self.load_backups()

        self.window.grab_set()

    def setup_ui(self):
        ctk.CTkLabel(self.window, text="Восстановление из бэкапа",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)

        frame = ctk.CTkFrame(self.window)
        frame.pack(fill="both", expand=True, padx=20, pady=10)

        self.tree = ttk.Treeview(frame, columns=("Дата", "Файлов", "Размер", "Описание"),
                                 show="headings", height=8)

        for col in ("Дата", "Файлов", "Размер", "Описание"):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100)

        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.tree.bind('<<TreeviewSelect>>', self.on_select)

        btn_frame = ctk.CTkFrame(self.window)
        btn_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkButton(btn_frame, text="Восстановить",
                      command=self.restore, width=120).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Удалить",
                      command=self.delete, width=120, fg_color="red").pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Закрыть",
                      command=self.window.destroy, width=120).pack(side="right", padx=5)

    def load_backups(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        backups = self.backup_system.get_available_backups()

        for backup in backups:
            ts = backup["timestamp"]
            date_str = f"{ts[6:8]}.{ts[4:6]}.{ts[:4]} {ts[9:11]}:{ts[11:13]}"

            size_mb = backup["total_size"] / (1024 * 1024)
            size_str = f"{size_mb:.1f} MB" if size_mb < 1024 else f"{size_mb / 1024:.1f} GB"

            self.tree.insert("", "end", values=(
                date_str,
                backup["file_count"],
                size_str,
                backup["description"][:40]
            ), tags=(backup["name"],))

    def on_select(self, event):
        selection = self.tree.selection()
        if selection:
            self.selected_backup = self.tree.item(selection[0], "tags")[0]

    def restore(self):
        if not self.selected_backup:
            messagebox.showwarning("Внимание", "Выберите бэкап для восстановления")
            return

        if messagebox.askyesno("Подтверждение", "Восстановить выбранный бэкап?"):
            restored, total, failed = self.backup_system.restore_files(self.selected_backup)

            if failed:
                messagebox.showwarning("Готово",
                                       f"Восстановлено {restored} из {total} файлов\nОшибок: {len(failed)}")
            else:
                messagebox.showinfo("Успешно", f"Восстановлено {restored} файлов")

    def delete(self):
        if not self.selected_backup:
            messagebox.showwarning("Внимание", "Выберите бэкап для удаления")
            return

        if messagebox.askyesno("Подтверждение", "Удалить выбранный бэкап?"):
            if self.backup_system.delete_backup(self.selected_backup):
                messagebox.showinfo("Успешно", "Бэкап удален")
                self.selected_backup = None
                self.load_backups()
            else:
                messagebox.showerror("Ошибка", "Не удалось удалить бэкап")