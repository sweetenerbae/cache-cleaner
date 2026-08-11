import customtkinter as ctk
from tkinter import messagebox, filedialog
import os
from typing import Callable, Optional


class GUIBuilder:
    def __init__(self, cleanup_callback: Callable, restore_callback: Callable):
        self.cleanup_callback = cleanup_callback
        self.restore_callback = restore_callback
        self.root = None
        self.user_folder = None

    def setup_gui(self) -> ctk.CTk:
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.root = ctk.CTk()
        self.root.title("Cache Cleaner Pro")
        self.root.geometry("500x500")

        self._create_widgets()
        return self.root

    def _create_widgets(self):
        #  main view
        title = ctk.CTkLabel(
            self.root,
            text="Очистка кэша системы",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title.pack(pady=10)

        # checkboxes
        self.var_windows = ctk.BooleanVar(value=True)
        self.var_adobe = ctk.BooleanVar(value=True)
        self.var_discord = ctk.BooleanVar(value=True)
        self.var_backup = ctk.BooleanVar(value=True)

        frame_options = ctk.CTkFrame(self.root)
        frame_options.pack(fill="x", padx=20, pady=10)

        ctk.CTkCheckBox(
            frame_options,
            text="Создать бэкап",
            variable=self.var_backup
        ).pack(anchor="w", pady=5)

        ctk.CTkCheckBox(
            frame_options,
            text="Windows временные файлы",
            variable=self.var_windows
        ).pack(anchor="w", pady=5)

        ctk.CTkCheckBox(
            frame_options,
            text="Adobe Cache",
            variable=self.var_adobe
        ).pack(anchor="w", pady=5)

        ctk.CTkCheckBox(
            frame_options,
            text="Discord Cache",
            variable=self.var_discord
        ).pack(anchor="w", pady=5)

        # browsers
        self._create_browsers_section()

        # adobe choose button
        btn_adobe = ctk.CTkButton(
            self.root,
            text="Выбрать папку Adobe",
            command=self._choose_adobe_folder
        )
        btn_adobe.pack(pady=10)

        self.lbl_adobe = ctk.CTkLabel(self.root, text="Не выбрано", text_color="gray")
        self.lbl_adobe.pack()

        # progress bar
        self.progress = ctk.CTkProgressBar(self.root, width=400)
        self.progress.set(0)
        self.progress.pack(pady=20)

        self.lbl_status = ctk.CTkLabel(self.root, text="Готово")
        self.lbl_status.pack()

        frame_buttons = ctk.CTkFrame(self.root)
        frame_buttons.pack(pady=20)

        ctk.CTkButton(
            frame_buttons,
            text="Очистить",
            command=self._on_cleanup,
            width=120
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            frame_buttons,
            text="Восстановить",
            command=self.restore_callback,
            width=120,
            fg_color="green"
        ).pack(side="left", padx=5)

    def _create_browsers_section(self):
        frame_browsers = ctk.CTkFrame(self.root)
        frame_browsers.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(frame_browsers, text="Браузеры:").pack(anchor="w", padx=10)

        # browsers checkboxes
        self.browser_vars = {
            "chrome": ctk.BooleanVar(value=True),
            "firefox": ctk.BooleanVar(value=True),
            "edge": ctk.BooleanVar(value=True),
            "brave": ctk.BooleanVar(value=True),
            "yandex": ctk.BooleanVar(value=True)
        }

        browsers_frame = ctk.CTkFrame(frame_browsers)
        browsers_frame.pack(fill="x", padx=20, pady=5)

        ctk.CTkCheckBox(
            browsers_frame,
            text="Chrome",
            variable=self.browser_vars["chrome"]
        ).grid(row=0, column=0, padx=5, pady=2, sticky="w")

        ctk.CTkCheckBox(
            browsers_frame,
            text="Firefox",
            variable=self.browser_vars["firefox"]
        ).grid(row=0, column=1, padx=5, pady=2, sticky="w")

        ctk.CTkCheckBox(
            browsers_frame,
            text="Edge",
            variable=self.browser_vars["edge"]
        ).grid(row=1, column=0, padx=5, pady=2, sticky="w")

        ctk.CTkCheckBox(
            browsers_frame,
            text="Brave",
            variable=self.browser_vars["brave"]
        ).grid(row=1, column=1, padx=5, pady=2, sticky="w")

        ctk.CTkCheckBox(
            browsers_frame,
            text="Yandex",
            variable=self.browser_vars["yandex"]
        ).grid(row=2, column=0, padx=5, pady=2, sticky="w")

    def _choose_adobe_folder(self):
        folder = filedialog.askdirectory(title="Выберите папку Adobe Cache")
        if folder:
            self.user_folder = folder
            display_name = os.path.basename(folder)
            if len(folder) > 40:
                display_name = folder[:37] + "..."
            self.lbl_adobe.configure(
                text=f"Выбрано: {display_name}",
                text_color="white"
            )

    def _on_cleanup(self):
        options = {
            "windows": self.var_windows.get(),
            "adobe": self.var_adobe.get(),
            "discord": self.var_discord.get(),
            "create_backup": self.var_backup.get(),
            "adobe_folder": self.user_folder,
            "browsers": {k: v.get() for k, v in self.browser_vars.items()}
        }

        self.cleanup_callback(options, self._update_progress)

    def _update_progress(self, value: int, status: str):
        if self.root and self.progress and self.lbl_status:
            self.progress.set(value / 100)
            self.lbl_status.configure(text=status)
            self.root.update()

    def show_message(self, title: str, message: str, is_error: bool = False):
        if is_error:
            messagebox.showerror(title, message)
        else:
            messagebox.showinfo(title, message)

    def reset_progress(self):
        if self.progress and self.lbl_status:
            self.progress.set(0)
            self.lbl_status.configure(text="Готово")