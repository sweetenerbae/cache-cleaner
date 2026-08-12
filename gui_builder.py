import os
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Callable, Dict, Optional

import customtkinter as ctk
from PIL import Image


def resource_path(relative_path: str) -> str:
    base_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return str(base_path / relative_path)


class GUIBuilder:
    BG = "#080B14"
    SURFACE = "#101522"
    SURFACE_ALT = "#151B2B"
    BORDER = "#242C40"
    TEXT = "#F5F7FF"
    MUTED = "#8E98AE"
    PURPLE = "#7657FF"
    PURPLE_HOVER = "#6545EE"
    CYAN = "#32D6C9"
    GREEN = "#35D07F"
    RED = "#FF647C"
    TRACK = "#252C3D"

    CHART_COLORS = {
        "Windows": "#7657FF",
        "Adobe": "#FF8A5B",
        "Discord": "#8C7CFF",
        "Browsers": "#32D6C9",
    }

    def __init__(self, cleanup_callback: Callable, restore_callback: Callable, scan_callback: Callable):
        self.cleanup_callback = cleanup_callback
        self.restore_callback = restore_callback
        self.scan_callback = scan_callback
        self.root: Optional[ctk.CTk] = None
        self.user_folder: Optional[str] = None
        self.is_busy = False
        self.control_widgets = []
        self.last_scan_total = 0
        self.last_scan_categories: Dict[str, int] = {}

    def setup_gui(self) -> ctk.CTk:
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.root = ctk.CTk(fg_color=self.BG)
        self.root.title("Cache Cleaner Pro")
        try:
            self.root.iconbitmap(resource_path("assets/cache_cleaner.ico"))
        except (OSError, tk.TclError):
            pass
        self.root.geometry("980x720")
        self.root.minsize(620, 520)
        self.root.resizable(True, True)

        self._center_window(980, 720)
        self._create_widgets()
        self.root.bind("<Configure>", self._on_root_configure)
        self.root.after_idle(lambda: self._apply_responsive_layout(self.root.winfo_width()))
        return self.root

    def _center_window(self, width: int, height: int):
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = max(0, (screen_width - width) // 2)
        y = max(0, (screen_height - height) // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def _create_widgets(self):
        self.var_windows = ctk.BooleanVar(value=True)
        self.var_adobe = ctk.BooleanVar(value=True)
        self.var_discord = ctk.BooleanVar(value=True)
        self.var_backup = ctk.BooleanVar(value=True)

        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=1)

        self._create_header()

        self.content = ctk.CTkScrollableFrame(
            self.root,
            fg_color="transparent",
            corner_radius=0,
            scrollbar_button_color=self.BORDER,
            scrollbar_button_hover_color=self.PURPLE,
        )
        self.content.grid(row=1, column=0, sticky="nsew", padx=(24, 14), pady=(0, 14))
        self.content.grid_columnconfigure(0, weight=11, uniform="content")
        self.content.grid_columnconfigure(1, weight=9, uniform="content")

        self._create_options_panel(self.content)
        self._create_dashboard(self.content)
        self._create_action_bar()

    def _create_header(self):
        header = ctk.CTkFrame(self.root, height=94, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(18, 12))
        header.grid_columnconfigure(1, weight=1)
        header.grid_propagate(False)

        logo = ctk.CTkFrame(
            header,
            width=58,
            height=58,
            corner_radius=18,
            fg_color=self.SURFACE_ALT,
            border_width=1,
            border_color=self.BORDER,
        )
        logo.grid(row=0, column=0, rowspan=2, padx=(0, 14), pady=8)
        logo.grid_propagate(False)
        try:
            logo_source = Image.open(resource_path("assets/cache_cleaner_logo.png"))
            self.logo_image = ctk.CTkImage(
                light_image=logo_source,
                dark_image=logo_source,
                size=(50, 50),
            )
            ctk.CTkLabel(logo, text="", image=self.logo_image).place(relx=0.5, rely=0.5, anchor="center")
        except OSError:
            ctk.CTkLabel(logo, text="✦", text_color=self.CYAN, font=ctk.CTkFont(size=25)).place(
                relx=0.5,
                rely=0.5,
                anchor="center",
            )

        ctk.CTkLabel(
            header,
            text="Cache Cleaner",
            text_color=self.TEXT,
            font=ctk.CTkFont(size=25, weight="bold"),
        ).grid(row=0, column=1, sticky="sw", pady=(9, 0))
        ctk.CTkLabel(
            header,
            text="Умная очистка без лишнего риска",
            text_color=self.MUTED,
            font=ctk.CTkFont(size=13),
        ).grid(row=1, column=1, sticky="nw", pady=(2, 8))

        badge = ctk.CTkLabel(
            header,
            text="●  SYSTEM READY",
            text_color=self.CYAN,
            fg_color="#102724",
            corner_radius=13,
            width=150,
            height=32,
            font=ctk.CTkFont(size=11, weight="bold"),
        )
        badge.grid(row=0, column=2, rowspan=2, sticky="e")

    def _create_options_panel(self, parent):
        panel = self._card(parent)
        self.options_panel = panel
        panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        panel.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            panel,
            text="ЧТО ОЧИЩАЕМ",
            text_color=self.MUTED,
            font=ctk.CTkFont(size=11, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(18, 4))
        ctk.CTkLabel(
            panel,
            text="Выберите категории",
            text_color=self.TEXT,
            font=ctk.CTkFont(size=19, weight="bold"),
        ).grid(row=1, column=0, sticky="w", padx=20, pady=(0, 12))

        categories = ctk.CTkFrame(panel, fg_color="transparent")
        categories.grid(row=2, column=0, sticky="ew", padx=14)
        categories.grid_columnconfigure((0, 1), weight=1, uniform="category")

        self._category_tile(categories, 0, 0, "Windows", "Временные файлы", self.var_windows, self.PURPLE)
        self._category_tile(categories, 0, 1, "Adobe", "Media Cache", self.var_adobe, "#FF8A5B")
        self._category_tile(categories, 1, 0, "Discord", "Cache и GPUCache", self.var_discord, "#8C7CFF")

        backup_tile = ctk.CTkFrame(
            categories,
            fg_color="#11251E",
            border_width=1,
            border_color="#214936",
            corner_radius=15,
            height=72,
        )
        backup_tile.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)
        backup_tile.grid_propagate(False)
        backup_check = self._checkbox(
            backup_tile,
            "Создать бэкап\nперед очисткой",
            self.var_backup,
            self.GREEN,
        )
        backup_check.place(x=14, rely=0.5, anchor="w")

        ctk.CTkLabel(
            panel,
            text="БРАУЗЕРЫ",
            text_color=self.MUTED,
            font=ctk.CTkFont(size=11, weight="bold"),
        ).grid(row=3, column=0, sticky="w", padx=20, pady=(17, 8))
        self._create_browsers_section(panel)

        adobe_row = ctk.CTkFrame(panel, fg_color=self.SURFACE_ALT, corner_radius=14, height=66)
        adobe_row.grid(row=5, column=0, sticky="ew", padx=18, pady=(15, 18))
        adobe_row.grid_columnconfigure(0, weight=1)
        adobe_row.grid_propagate(False)

        adobe_info = ctk.CTkFrame(adobe_row, fg_color="transparent")
        adobe_info.grid(row=0, column=0, sticky="w", padx=14)
        ctk.CTkLabel(
            adobe_info,
            text="Папка Adobe",
            text_color=self.TEXT,
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(anchor="w")
        self.lbl_adobe = ctk.CTkLabel(
            adobe_info,
            text="Автоматический поиск",
            text_color=self.MUTED,
            font=ctk.CTkFont(size=11),
        )
        self.lbl_adobe.pack(anchor="w")

        self.btn_adobe = ctk.CTkButton(
            adobe_row,
            text="Изменить",
            command=self._choose_adobe_folder,
            width=92,
            height=34,
            corner_radius=11,
            fg_color=self.BORDER,
            hover_color="#303A52",
        )
        self.btn_adobe.grid(row=0, column=1, padx=14)
        self.control_widgets.append(self.btn_adobe)

    def _create_dashboard(self, parent):
        panel = self._card(parent)
        self.dashboard_panel = panel
        panel.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(3, weight=1)

        ctk.CTkLabel(
            panel,
            text="АНАЛИЗ ХРАНИЛИЩА",
            text_color=self.MUTED,
            font=ctk.CTkFont(size=11, weight="bold"),
        ).grid(row=0, column=0, pady=(18, 0))
        self.lbl_metric = ctk.CTkLabel(
            panel,
            text="—",
            text_color=self.TEXT,
            font=ctk.CTkFont(size=35, weight="bold"),
        )
        self.lbl_metric.grid(row=1, column=0, pady=(4, 0))
        self.lbl_metric_hint = ctk.CTkLabel(
            panel,
            text="Запустите сканирование",
            text_color=self.MUTED,
            font=ctk.CTkFont(size=12),
        )
        self.lbl_metric_hint.grid(row=2, column=0, pady=(0, 4))

        self.chart = tk.Canvas(
            panel,
            width=260,
            height=260,
            bg=self.SURFACE,
            highlightthickness=0,
        )
        self.chart.grid(row=3, column=0, pady=(0, 0))
        self._draw_donut({})

        self.legend = ctk.CTkFrame(panel, fg_color="transparent")
        self.legend.grid(row=4, column=0, sticky="ew", padx=24, pady=(0, 12))
        self._render_legend({})

        status_card = ctk.CTkFrame(panel, fg_color=self.SURFACE_ALT, corner_radius=14)
        status_card.grid(row=5, column=0, sticky="ew", padx=18, pady=(0, 18))
        status_card.grid_columnconfigure(0, weight=1)

        self.lbl_status = ctk.CTkLabel(
            status_card,
            text="Готово к работе",
            text_color=self.TEXT,
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.lbl_status.grid(row=0, column=0, sticky="w", padx=14, pady=(11, 7))
        self.progress = ctk.CTkProgressBar(
            status_card,
            height=8,
            corner_radius=4,
            fg_color=self.TRACK,
            progress_color=self.CYAN,
        )
        self.progress.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 13))
        self.progress.set(0)

    def _create_action_bar(self):
        bar = ctk.CTkFrame(
            self.root,
            height=82,
            fg_color=self.SURFACE,
            corner_radius=18,
            border_width=1,
            border_color=self.BORDER,
        )
        bar.grid(row=2, column=0, sticky="ew", padx=24, pady=(0, 20))
        bar.grid_columnconfigure(0, weight=1)
        bar.grid_propagate(False)

        self.action_hint = ctk.CTkLabel(
            bar,
            text="Сначала проверьте объём — затем очистите",
            text_color=self.MUTED,
            font=ctk.CTkFont(size=12),
        )
        self.action_hint.grid(row=0, column=0, sticky="w", padx=18)

        self.btn_restore = ctk.CTkButton(
            bar,
            text="↶  Бэкапы",
            command=self.restore_callback,
            width=118,
            height=44,
            corner_radius=13,
            fg_color=self.BORDER,
            hover_color="#303A52",
        )
        self.btn_restore.grid(row=0, column=1, padx=(8, 0), pady=18)

        self.btn_scan = ctk.CTkButton(
            bar,
            text="◎  Сканировать",
            command=self._on_scan,
            width=156,
            height=44,
            corner_radius=13,
            fg_color="#1B4351",
            hover_color="#245B6D",
            text_color=self.CYAN,
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.btn_scan.grid(row=0, column=2, padx=10, pady=18)

        self.btn_cleanup = ctk.CTkButton(
            bar,
            text="✦  Начать очистку",
            command=self._on_cleanup,
            width=178,
            height=44,
            corner_radius=13,
            fg_color=self.PURPLE,
            hover_color=self.PURPLE_HOVER,
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.btn_cleanup.grid(row=0, column=3, padx=(0, 18), pady=18)

        self.control_widgets.extend([self.btn_restore, self.btn_scan, self.btn_cleanup])

    def _on_root_configure(self, event):
        if event.widget is self.root:
            self._apply_responsive_layout(event.width)

    def _apply_responsive_layout(self, width: int):
        mode = "compact" if width < 860 else "desktop"
        if getattr(self, "_layout_mode", None) == mode:
            return
        self._layout_mode = mode

        if mode == "compact":
            self.content.grid_columnconfigure(0, weight=1, uniform="")
            self.content.grid_columnconfigure(1, weight=0, uniform="")
            self.options_panel.grid_configure(row=0, column=0, padx=0, pady=(0, 8))
            self.dashboard_panel.grid_configure(row=1, column=0, padx=0, pady=(8, 0))

            self.action_hint.grid_remove()
            self.btn_restore.configure(width=105)
            self.btn_scan.configure(width=140)
            self.btn_cleanup.configure(width=165)
        else:
            self.content.grid_columnconfigure(0, weight=11, uniform="content")
            self.content.grid_columnconfigure(1, weight=9, uniform="content")
            self.options_panel.grid_configure(row=0, column=0, padx=(0, 8), pady=0)
            self.dashboard_panel.grid_configure(row=0, column=1, padx=(8, 0), pady=0)

            self.action_hint.grid()
            self.btn_restore.configure(width=118)
            self.btn_scan.configure(width=156)
            self.btn_cleanup.configure(width=178)

    def _card(self, parent):
        return ctk.CTkFrame(
            parent,
            fg_color=self.SURFACE,
            corner_radius=20,
            border_width=1,
            border_color=self.BORDER,
        )

    def _checkbox(self, parent, text, variable, accent):
        checkbox = ctk.CTkCheckBox(
            parent,
            text=text,
            variable=variable,
            text_color=self.TEXT,
            font=ctk.CTkFont(size=12, weight="bold"),
            checkbox_width=22,
            checkbox_height=22,
            corner_radius=7,
            border_width=2,
            border_color="#4A546D",
            fg_color=accent,
            hover_color=accent,
        )
        self.control_widgets.append(checkbox)
        return checkbox

    def _category_tile(self, parent, row, column, title, subtitle, variable, accent):
        tile = ctk.CTkFrame(
            parent,
            fg_color=self.SURFACE_ALT,
            border_width=1,
            border_color=self.BORDER,
            corner_radius=15,
            height=82,
        )
        tile.grid(row=row, column=column, sticky="nsew", padx=5, pady=5)
        tile.grid_propagate(False)

        accent_line = ctk.CTkFrame(
            tile,
            width=4,
            height=38,
            corner_radius=2,
            fg_color=accent,
        )
        accent_line.place(x=14, rely=0.5, anchor="w")

        checkbox = self._checkbox(tile, f"{title}\n{subtitle}", variable, accent)
        checkbox.place(x=28, rely=0.5, anchor="w")

    def _create_browsers_section(self, parent):
        browser_box = ctk.CTkFrame(parent, fg_color=self.SURFACE_ALT, corner_radius=14)
        browser_box.grid(row=4, column=0, sticky="ew", padx=18)
        browser_box.grid_columnconfigure((0, 1, 2), weight=1)

        self.browser_vars = {
            "chrome": ctk.BooleanVar(value=True),
            "firefox": ctk.BooleanVar(value=True),
            "edge": ctk.BooleanVar(value=True),
            "brave": ctk.BooleanVar(value=True),
            "yandex": ctk.BooleanVar(value=True),
        }
        names = [("chrome", "Chrome"), ("firefox", "Firefox"), ("edge", "Edge"), ("brave", "Brave"), ("yandex", "Yandex")]
        for index, (key, title) in enumerate(names):
            checkbox = ctk.CTkCheckBox(
                browser_box,
                text=title,
                variable=self.browser_vars[key],
                text_color=self.TEXT,
                font=ctk.CTkFont(size=12),
                checkbox_width=20,
                checkbox_height=20,
                corner_radius=6,
                border_width=2,
                border_color="#4A546D",
                fg_color=self.CYAN,
                hover_color=self.CYAN,
            )
            checkbox.grid(row=index // 3, column=index % 3, sticky="w", padx=14, pady=10)
            self.control_widgets.append(checkbox)

    def _draw_donut(self, category_totals: Dict[str, int]):
        self.chart.delete("all")
        x0, y0, x1, y1 = 34, 24, 226, 216
        total = sum(category_totals.values())

        self.chart.create_oval(x0, y0, x1, y1, outline=self.TRACK, width=28)
        if total > 0:
            start = 90
            for category, size in category_totals.items():
                if size <= 0:
                    continue
                extent = -(size / total) * 359.8
                self.chart.create_arc(
                    x0,
                    y0,
                    x1,
                    y1,
                    start=start,
                    extent=extent,
                    style="arc",
                    outline=self.CHART_COLORS.get(category, self.PURPLE),
                    width=28,
                )
                start += extent

        self.chart.create_text(
            130,
            110,
            text="CACHE" if total == 0 else "НАЙДЕНО",
            fill=self.MUTED,
            font=("Segoe UI", 9, "bold"),
        )
        self.chart.create_text(
            130,
            136,
            text="READY" if total == 0 else self._format_size(total),
            fill=self.TEXT,
            font=("Segoe UI", 16, "bold"),
        )

    def _render_legend(self, category_totals: Dict[str, int]):
        for child in self.legend.winfo_children():
            child.destroy()

        values = category_totals or {"Windows": 0, "Adobe": 0, "Discord": 0, "Browsers": 0}
        for index, (category, size) in enumerate(values.items()):
            row = index // 2
            column = index % 2
            item = ctk.CTkFrame(self.legend, fg_color="transparent")
            item.grid(row=row, column=column, sticky="w", padx=8, pady=3)
            ctk.CTkLabel(
                item,
                text="●",
                text_color=self.CHART_COLORS.get(category, self.PURPLE),
                width=16,
                font=ctk.CTkFont(size=13),
            ).pack(side="left")
            value = self._format_size(size) if category_totals else category
            ctk.CTkLabel(
                item,
                text=f"{category}: {value}" if category_totals else value,
                text_color=self.MUTED,
                font=ctk.CTkFont(size=10),
            ).pack(side="left")

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        if size_bytes >= 1024 ** 3:
            return f"{size_bytes / 1024 ** 3:.2f} GB"
        if size_bytes >= 1024 ** 2:
            return f"{size_bytes / 1024 ** 2:.1f} MB"
        if size_bytes >= 1024:
            return f"{size_bytes / 1024:.1f} KB"
        return f"{size_bytes} B"

    def _choose_adobe_folder(self):
        folder = filedialog.askdirectory(title="Выберите папку Adobe Cache")
        if folder:
            self.user_folder = folder
            display_name = os.path.basename(folder) or folder
            if len(display_name) > 30:
                display_name = display_name[:27] + "..."
            self.lbl_adobe.configure(text=display_name, text_color=self.CYAN)

    def _build_options(self):
        return {
            "windows": self.var_windows.get(),
            "adobe": self.var_adobe.get(),
            "discord": self.var_discord.get(),
            "create_backup": self.var_backup.get(),
            "adobe_folder": self.user_folder,
            "browsers": {key: value.get() for key, value in self.browser_vars.items()},
        }

    def _run_background_task(self, task_callback: Callable, options: dict, start_status: str):
        if self.is_busy:
            return
        self.set_busy(True, start_status)
        threading.Thread(target=task_callback, args=(options, self._update_progress), daemon=True).start()

    def _on_cleanup(self):
        self._run_background_task(self.cleanup_callback, self._build_options(), "Подготовка к очистке...")

    def _on_scan(self):
        options = self._build_options()
        options["create_backup"] = False
        self._run_background_task(self.scan_callback, options, "Анализируем выбранные категории...")

    def _update_progress(self, value: int, status: str):
        if self.root:
            self.root.after(0, self._apply_progress_update, value, status)

    def _apply_progress_update(self, value: int, status: str):
        self.progress.set(max(0, min(value, 100)) / 100)
        self.lbl_status.configure(text=status)

    def set_busy(self, busy: bool, status: Optional[str] = None):
        if not self.root:
            return
        self.is_busy = busy
        self.root.after(0, self._apply_busy_state, busy, status)

    def _apply_busy_state(self, busy: bool, status: Optional[str]):
        self.is_busy = busy
        state = "disabled" if busy else "normal"
        for widget in self.control_widgets:
            try:
                widget.configure(state=state)
            except Exception:
                pass
        if status:
            self.lbl_status.configure(text=status)

    def show_message(self, title: str, message: str, is_error: bool = False):
        if self.root:
            self.root.after(0, self._show_message_dialog, title, message, is_error)

    @staticmethod
    def _show_message_dialog(title: str, message: str, is_error: bool):
        if is_error:
            messagebox.showerror(title, message)
        else:
            messagebox.showinfo(title, message)

    def show_scan_results(self, title: str, summary: str, category_totals=None, total_size: int = 0):
        if self.root:
            self.root.after(
                0,
                self._show_scan_results_window,
                title,
                summary,
                category_totals or {},
                total_size,
            )

    def _show_scan_results_window(self, title, summary, category_totals, total_size):
        self.last_scan_total = total_size
        self.last_scan_categories = category_totals
        self.lbl_metric.configure(text=self._format_size(total_size))
        self.lbl_metric_hint.configure(text="можно безопасно освободить")
        self._draw_donut(category_totals)
        self._render_legend(category_totals)

        window = ctk.CTkToplevel(self.root, fg_color=self.BG)
        window.title(title)
        window.geometry("760x560")
        window.minsize(680, 500)
        window.transient(self.root)
        window.grab_set()

        shell = self._card(window)
        shell.pack(fill="both", expand=True, padx=20, pady=20)
        shell.grid_columnconfigure(1, weight=1)
        shell.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            shell,
            text="Сканирование завершено",
            text_color=self.TEXT,
            font=ctk.CTkFont(size=23, weight="bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=22, pady=(20, 12))

        chart = tk.Canvas(shell, width=250, height=260, bg=self.SURFACE, highlightthickness=0)
        chart.grid(row=1, column=0, padx=(18, 4), pady=4)
        self._draw_result_donut(chart, category_totals, total_size)

        text_box = ctk.CTkTextbox(
            shell,
            wrap="word",
            fg_color=self.SURFACE_ALT,
            border_width=0,
            corner_radius=14,
            text_color=self.TEXT,
            font=ctk.CTkFont(size=12),
        )
        text_box.grid(row=1, column=1, sticky="nsew", padx=(4, 20), pady=4)
        text_box.insert("1.0", summary)
        text_box.configure(state="disabled")

        ctk.CTkButton(
            shell,
            text="Отлично",
            command=window.destroy,
            width=150,
            height=42,
            corner_radius=13,
            fg_color=self.PURPLE,
            hover_color=self.PURPLE_HOVER,
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=2, column=1, sticky="e", padx=20, pady=18)

    def _draw_result_donut(self, canvas, category_totals, total_size):
        canvas.create_oval(31, 31, 219, 219, outline=self.TRACK, width=30)
        if total_size > 0:
            start = 90
            for category, size in category_totals.items():
                if size <= 0:
                    continue
                extent = -(size / total_size) * 359.8
                canvas.create_arc(
                    31,
                    31,
                    219,
                    219,
                    start=start,
                    extent=extent,
                    style="arc",
                    outline=self.CHART_COLORS.get(category, self.PURPLE),
                    width=30,
                )
                start += extent
        canvas.create_text(125, 112, text="МОЖНО ОЧИСТИТЬ", fill=self.MUTED, font=("Segoe UI", 9, "bold"))
        canvas.create_text(125, 139, text=self._format_size(total_size), fill=self.TEXT, font=("Segoe UI", 17, "bold"))

    def reset_progress(self):
        if self.root:
            self.is_busy = False
            self.root.after(0, self._reset_progress_ui)

    def _reset_progress_ui(self):
        self.progress.set(0)
        self.lbl_status.configure(text="Готово к работе")
        self._apply_busy_state(False, None)
