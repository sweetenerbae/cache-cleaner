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
    BG = "#0B0D10"
    SURFACE = "#12151A"
    SURFACE_ALT = "#181C23"
    BORDER = "#262C35"
    TEXT = "#F3F5F7"
    MUTED = "#8D96A5"
    PURPLE = "#6C8CFF"
    PURPLE_HOVER = "#5879EC"
    CYAN = "#54D6C2"
    GREEN = "#5BD69D"
    RED = "#F07178"
    TRACK = "#252B34"

    CHART_COLORS = {
        "Windows": "#6C8CFF",
        "Adobe": "#F2A365",
        "Discord": "#A68AF0",
        "Browsers": "#54D6C2",
        "Launchers": "#45B7F1",
        "Developer": "#F4C95D",
        "Recycle Bin": "#F07178",
    }
    CATEGORY_LABELS = {
        "Windows": "Windows",
        "Adobe": "Adobe",
        "Discord": "Discord",
        "Browsers": "Браузеры",
        "Launchers": "Лаунчеры",
        "Developer": "Dev-кэш",
        "Recycle Bin": "Корзина",
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
        self.root.geometry("1040x860")
        self.root.minsize(660, 560)
        self.root.resizable(True, True)

        self._center_window(1040, 860)
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
        self.var_recycle = ctk.BooleanVar(value=False)
        self.var_developer_mode = ctk.BooleanVar(value=False)
        self.developer_widgets = []

        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=1)

        self._create_header()

        self.content = ctk.CTkScrollableFrame(
            self.root,
            fg_color="transparent",
            corner_radius=0,
            scrollbar_button_color=self.BORDER,
            scrollbar_button_hover_color="#3A4350",
        )
        self.content.grid(row=1, column=0, sticky="nsew", padx=(28, 18), pady=(0, 12))
        self.content.grid_columnconfigure(0, weight=10, uniform="content")
        self.content.grid_columnconfigure(1, weight=9, uniform="content")

        self._create_options_panel(self.content)
        self._create_dashboard(self.content)
        self._create_action_bar()

    def _create_header(self):
        header = ctk.CTkFrame(self.root, height=82, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=30, pady=(14, 8))
        header.grid_columnconfigure(1, weight=1)
        header.grid_propagate(False)

        logo = ctk.CTkFrame(
            header,
            width=54,
            height=54,
            corner_radius=15,
            fg_color="#171B22",
        )
        logo.grid(row=0, column=0, rowspan=2, padx=(0, 15), pady=8)
        logo.grid_propagate(False)
        try:
            logo_source = Image.open(resource_path("assets/cache_cleaner_logo.png"))
            self.logo_image = ctk.CTkImage(
                light_image=logo_source,
                dark_image=logo_source,
                size=(45, 45),
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
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
        ).grid(row=0, column=1, sticky="sw", pady=(10, 0))
        ctk.CTkLabel(
            header,
            text="Умная очистка без лишнего риска",
            text_color=self.MUTED,
            font=ctk.CTkFont(family="Segoe UI", size=12),
        ).grid(row=1, column=1, sticky="nw", pady=(2, 8))

        badge = ctk.CTkLabel(
            header,
            text="●  Система готова",
            text_color=self.GREEN,
            fg_color="#14231E",
            corner_radius=12,
            width=142,
            height=34,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
        )
        badge.grid(row=0, column=2, rowspan=2, sticky="e")

    def _create_options_panel(self, parent):
        panel = self._card(parent)
        self.options_panel = panel
        panel.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        panel.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            panel,
            text="План очистки",
            text_color=self.TEXT,
            font=ctk.CTkFont(family="Segoe UI", size=19, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=22, pady=(19, 0))
        ctk.CTkLabel(
            panel,
            text="Выберите данные, которые можно удалить",
            text_color=self.MUTED,
            font=ctk.CTkFont(family="Segoe UI", size=11),
        ).grid(row=1, column=0, sticky="w", padx=22, pady=(3, 13))

        categories = ctk.CTkFrame(panel, fg_color="transparent")
        categories.grid(row=2, column=0, sticky="ew", padx=17)
        categories.grid_columnconfigure(0, weight=1)

        self._category_tile(categories, 0, 0, "Windows", "Временные файлы системы", self.var_windows, self.PURPLE)
        self._category_tile(categories, 1, 0, "Adobe", "Media Cache и превью", self.var_adobe, "#F2A365")
        self._category_tile(categories, 2, 0, "Discord", "Cache, Code Cache и GPUCache", self.var_discord, "#A68AF0")
        self._category_tile(categories, 3, 0, "Корзина", "Безвозвратное удаление содержимого", self.var_recycle, self.RED)

        backup_tile = ctk.CTkFrame(
            categories,
            fg_color="#14201C",
            corner_radius=12,
            height=64,
        )
        backup_tile.grid(row=4, column=0, sticky="ew", padx=4, pady=(9, 5))
        backup_tile.grid_columnconfigure(0, weight=1)
        backup_tile.grid_propagate(False)
        backup_text = ctk.CTkFrame(backup_tile, fg_color="transparent")
        backup_text.place(x=15, rely=0.5, anchor="w")
        ctk.CTkLabel(
            backup_text,
            text="Защита перед очисткой",
            text_color=self.TEXT,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            height=17,
        ).pack(anchor="w")
        ctk.CTkLabel(
            backup_text,
            text="Сохранить ZIP-бэкап выбранных файлов",
            text_color=self.MUTED,
            font=ctk.CTkFont(family="Segoe UI", size=10),
            height=14,
        ).pack(anchor="w", pady=(1, 0))
        backup_switch = self._switch(backup_tile, self.var_backup, self.GREEN)
        backup_switch.place(relx=1.0, x=-14, rely=0.5, anchor="e")

        ctk.CTkLabel(
            panel,
            text="Браузеры",
            text_color=self.TEXT,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
        ).grid(row=3, column=0, sticky="w", padx=22, pady=(15, 8))
        self._create_browsers_section(panel)

        adobe_row = ctk.CTkFrame(panel, fg_color="#15191F", corner_radius=12, height=58)
        adobe_row.grid(row=5, column=0, sticky="ew", padx=21, pady=(13, 18))
        adobe_row.grid_columnconfigure(0, weight=1)
        adobe_row.grid_propagate(False)

        adobe_info = ctk.CTkFrame(adobe_row, fg_color="transparent")
        adobe_info.grid(row=0, column=0, sticky="w", padx=14)
        ctk.CTkLabel(
            adobe_info,
            text="Дополнительная папка Adobe",
            text_color=self.TEXT,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
        ).pack(anchor="w")
        self.lbl_adobe = ctk.CTkLabel(
            adobe_info,
            text="Автоматический поиск",
            text_color=self.MUTED,
            font=ctk.CTkFont(family="Segoe UI", size=10),
        )
        self.lbl_adobe.pack(anchor="w")

        self.btn_adobe = ctk.CTkButton(
            adobe_row,
            text="Изменить",
            command=self._choose_adobe_folder,
            width=86,
            height=32,
            corner_radius=9,
            fg_color="#252B34",
            hover_color="#323A46",
            font=ctk.CTkFont(family="Segoe UI", size=11),
        )
        self.btn_adobe.grid(row=0, column=1, padx=14)
        self.control_widgets.append(self.btn_adobe)

        ctk.CTkLabel(
            panel,
            text="Игровые лаунчеры",
            text_color=self.TEXT,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
        ).grid(row=6, column=0, sticky="w", padx=22, pady=(0, 8))

        launcher_box = ctk.CTkFrame(panel, fg_color="#171B21", corner_radius=12)
        launcher_box.grid(row=7, column=0, sticky="ew", padx=21)
        launcher_box.grid_columnconfigure((0, 1, 2), weight=1)
        self.launcher_vars = {
            "steam": ctk.BooleanVar(value=False),
            "epic": ctk.BooleanVar(value=False),
            "battlenet": ctk.BooleanVar(value=False),
        }
        for column, (key, title) in enumerate((
            ("steam", "Steam"), ("epic", "Epic Games"), ("battlenet", "Battle.net"),
        )):
            self._checkbox(launcher_box, title, self.launcher_vars[key], "#45B7F1").grid(
                row=0, column=column, sticky="w", padx=13, pady=12
            )

        developer_header = ctk.CTkFrame(panel, fg_color="#1F1D16", corner_radius=12, height=58)
        developer_header.grid(row=8, column=0, sticky="ew", padx=21, pady=(14, 8))
        developer_header.grid_columnconfigure(0, weight=1)
        developer_header.grid_propagate(False)
        developer_text = ctk.CTkFrame(developer_header, fg_color="transparent")
        developer_text.grid(row=0, column=0, sticky="w", padx=14)
        ctk.CTkLabel(
            developer_text, text="Режим разработчика", text_color=self.TEXT,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), height=17,
        ).pack(anchor="w")
        ctk.CTkLabel(
            developer_text, text="Кэши зависимостей будут скачаны заново", text_color=self.MUTED,
            font=ctk.CTkFont(family="Segoe UI", size=10), height=14,
        ).pack(anchor="w", pady=(1, 0))
        developer_switch = self._switch(developer_header, self.var_developer_mode, "#F4C95D")
        developer_switch.configure(command=self._update_developer_state)
        developer_switch.grid(row=0, column=1, padx=14)

        developer_box = ctk.CTkFrame(panel, fg_color="#171B21", corner_radius=12)
        developer_box.grid(row=9, column=0, sticky="ew", padx=21, pady=(0, 18))
        developer_box.grid_columnconfigure((0, 1, 2), weight=1)
        self.developer_vars = {
            key: ctk.BooleanVar(value=True)
            for key in ("pip", "npm", "pnpm", "yarn", "gradle", "nuget")
        }
        for index, (key, title) in enumerate((
            ("pip", "pip"), ("npm", "npm"), ("pnpm", "pnpm"),
            ("yarn", "Yarn"), ("gradle", "Gradle"), ("nuget", "NuGet"),
        )):
            checkbox = self._checkbox(developer_box, title, self.developer_vars[key], "#F4C95D")
            checkbox.grid(row=index // 3, column=index % 3, sticky="w", padx=13, pady=9)
            self.developer_widgets.append(checkbox)
        self._update_developer_state()

    def _create_dashboard(self, parent):
        panel = self._card(parent)
        self.dashboard_panel = panel
        panel.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(3, weight=1)

        ctk.CTkLabel(
            panel,
            text="Результат анализа",
            text_color=self.TEXT,
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
        ).grid(row=0, column=0, pady=(20, 0))
        self.lbl_metric = ctk.CTkLabel(
            panel,
            text="—",
            text_color=self.TEXT,
            font=ctk.CTkFont(family="Segoe UI", size=34, weight="bold"),
        )
        self.lbl_metric.grid(row=1, column=0, pady=(4, 0))
        self.lbl_metric_hint = ctk.CTkLabel(
            panel,
            text="Запустите сканирование",
            text_color=self.MUTED,
            font=ctk.CTkFont(family="Segoe UI", size=11),
        )
        self.lbl_metric_hint.grid(row=2, column=0, pady=(0, 4))

        self.chart = tk.Canvas(
            panel,
            width=260,
            height=225,
            bg=self.SURFACE,
            highlightthickness=0,
        )
        self.chart.grid(row=3, column=0, pady=(0, 0))
        self._draw_donut({})

        self.legend = ctk.CTkFrame(panel, fg_color="transparent")
        self.legend.grid(row=4, column=0, sticky="ew", padx=24, pady=(0, 12))
        self._render_legend({})

        status_card = ctk.CTkFrame(panel, fg_color="#171B21", corner_radius=12)
        status_card.grid(row=5, column=0, sticky="ew", padx=20, pady=(0, 18))
        status_card.grid_columnconfigure(0, weight=1)

        self.lbl_status = ctk.CTkLabel(
            status_card,
            text="Готово к работе",
            text_color=self.TEXT,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
        )
        self.lbl_status.grid(row=0, column=0, sticky="w", padx=14, pady=(11, 7))
        self.progress = ctk.CTkProgressBar(
            status_card,
            height=6,
            corner_radius=3,
            fg_color=self.TRACK,
            progress_color=self.PURPLE,
        )
        self.progress.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 13))
        self.progress.set(0)

    def _create_action_bar(self):
        bar = ctk.CTkFrame(
            self.root,
            height=70,
            fg_color="#111419",
            corner_radius=16,
        )
        bar.grid(row=2, column=0, sticky="ew", padx=28, pady=(0, 16))
        bar.grid_columnconfigure(0, weight=1)
        bar.grid_propagate(False)

        self.action_hint = ctk.CTkLabel(
            bar,
            text="Готово к безопасной очистке",
            text_color=self.MUTED,
            font=ctk.CTkFont(family="Segoe UI", size=11),
        )
        self.action_hint.grid(row=0, column=0, sticky="w", padx=18)

        self.btn_restore = ctk.CTkButton(
            bar,
            text="Бэкапы",
            command=self.restore_callback,
            width=118,
            height=44,
            corner_radius=11,
            fg_color="transparent",
            hover_color="#20252C",
            border_width=1,
            border_color=self.BORDER,
            font=ctk.CTkFont(family="Segoe UI", size=11),
        )
        self.btn_restore.grid(row=0, column=1, padx=(8, 0), pady=14)

        self.btn_scan = ctk.CTkButton(
            bar,
            text="Сканировать",
            command=self._on_scan,
            width=156,
            height=44,
            corner_radius=11,
            fg_color="#202631",
            hover_color="#2B3340",
            text_color="#D9E2F2",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
        )
        self.btn_scan.grid(row=0, column=2, padx=10, pady=14)

        self.btn_cleanup = ctk.CTkButton(
            bar,
            text="Начать очистку",
            command=self._on_cleanup,
            width=178,
            height=44,
            corner_radius=11,
            fg_color=self.PURPLE,
            hover_color=self.PURPLE_HOVER,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
        )
        self.btn_cleanup.grid(row=0, column=3, padx=(0, 18), pady=14)

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
            self.content.grid_columnconfigure(0, weight=10, uniform="content")
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
            corner_radius=18,
            border_width=1,
            border_color="#20252D",
        )

    def _switch(self, parent, variable, accent):
        switch = ctk.CTkSwitch(
            parent,
            text="",
            variable=variable,
            width=42,
            height=22,
            switch_width=42,
            switch_height=22,
            corner_radius=11,
            border_width=0,
            fg_color="#303640",
            progress_color=accent,
            button_color="#F5F7FA",
            button_hover_color="#FFFFFF",
        )
        self.control_widgets.append(switch)
        return switch

    def _checkbox(self, parent, text, variable, accent):
        checkbox = ctk.CTkCheckBox(
            parent,
            text=text,
            variable=variable,
            text_color=self.TEXT,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            checkbox_width=19,
            checkbox_height=19,
            corner_radius=5,
            border_width=1,
            border_color="#4A5360",
            fg_color=accent,
            hover_color=accent,
        )
        self.control_widgets.append(checkbox)
        return checkbox

    def _category_tile(self, parent, row, column, title, subtitle, variable, accent):
        tile = ctk.CTkFrame(
            parent,
            fg_color="#171B21",
            corner_radius=13,
            height=72,
        )
        tile.grid(row=row, column=column, sticky="ew", padx=4, pady=5)
        tile.grid_columnconfigure(1, weight=1)
        tile.grid_propagate(False)

        accent_dot = ctk.CTkFrame(
            tile,
            width=8,
            height=8,
            corner_radius=4,
            fg_color=accent,
        )
        accent_dot.place(x=15, rely=0.5, anchor="w")

        text_block = ctk.CTkFrame(tile, fg_color="transparent")
        text_block.place(x=35, rely=0.5, anchor="w")
        ctk.CTkLabel(
            text_block,
            text=title,
            text_color=self.TEXT,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            height=17,
        ).pack(anchor="w")
        ctk.CTkLabel(
            text_block,
            text=subtitle,
            text_color=self.MUTED,
            font=ctk.CTkFont(family="Segoe UI", size=10),
            height=14,
        ).pack(anchor="w", pady=(1, 0))
        switch = self._switch(tile, variable, accent)
        switch.place(relx=1.0, x=-14, rely=0.5, anchor="e")

    def _create_browsers_section(self, parent):
        browser_box = ctk.CTkFrame(parent, fg_color="#171B21", corner_radius=12)
        browser_box.grid(row=4, column=0, sticky="ew", padx=21)
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
                font=ctk.CTkFont(family="Segoe UI", size=11),
                checkbox_width=18,
                checkbox_height=18,
                corner_radius=5,
                border_width=1,
                border_color="#4A5360",
                fg_color=self.CYAN,
                hover_color=self.CYAN,
            )
            checkbox.grid(row=index // 3, column=index % 3, sticky="w", padx=14, pady=9)
            self.control_widgets.append(checkbox)

    def _draw_donut(self, category_totals: Dict[str, int]):
        self.chart.delete("all")
        x0, y0, x1, y1 = 43, 30, 217, 204
        total = sum(category_totals.values())

        self.chart.create_oval(x0, y0, x1, y1, outline=self.TRACK, width=22)
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
                    width=22,
                )
                start += extent

        self.chart.create_text(
            130,
            105,
            text="КЭШ" if total == 0 else "НАЙДЕНО",
            fill=self.MUTED,
            font=("Segoe UI", 9),
        )
        self.chart.create_text(
            130,
            132,
            text="Готово" if total == 0 else self._format_size(total),
            fill=self.TEXT,
            font=("Segoe UI", 17, "bold"),
        )

    def _render_legend(self, category_totals: Dict[str, int]):
        for child in self.legend.winfo_children():
            child.destroy()

        values = category_totals or {"Windows": 0, "Adobe": 0, "Browsers": 0, "Launchers": 0}
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
                font=ctk.CTkFont(family="Segoe UI", size=11),
            ).pack(side="left")
            label = self.CATEGORY_LABELS.get(category, category)
            value = self._format_size(size) if category_totals else label
            ctk.CTkLabel(
                item,
                text=f"{label}: {value}" if category_totals else value,
                text_color=self.MUTED,
                font=ctk.CTkFont(family="Segoe UI", size=10),
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
            "recycle_bin": self.var_recycle.get(),
            "launchers": {key: value.get() for key, value in self.launcher_vars.items()},
            "developer_mode": self.var_developer_mode.get(),
            "developer_tools": {key: value.get() for key, value in self.developer_vars.items()},
        }

    def _update_developer_state(self):
        state = "normal" if self.var_developer_mode.get() and not self.is_busy else "disabled"
        for widget in self.developer_widgets:
            widget.configure(state=state)

    def _run_background_task(self, task_callback: Callable, options: dict, start_status: str):
        if self.is_busy:
            return
        self.set_busy(True, start_status)
        threading.Thread(target=task_callback, args=(options, self._update_progress), daemon=True).start()

    def _on_cleanup(self):
        options = self._build_options()
        if options["recycle_bin"]:
            confirmed = messagebox.askyesno(
                "Очистить корзину?",
                "Файлы из корзины будут удалены безвозвратно и не попадут в ZIP-бэкап.\n\nПродолжить?",
                parent=self.root,
            )
            if not confirmed:
                return
        self._run_background_task(self.cleanup_callback, options, "Подготовка к очистке...")

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
        if not busy:
            self._update_developer_state()
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

    def update_dashboard(self, category_totals=None, total_size: int = 0, hint: str = ""):
        if self.root:
            self.root.after(
                0,
                self._apply_dashboard_update,
                category_totals or {},
                total_size,
                hint,
            )

    def _apply_dashboard_update(self, category_totals, total_size, hint):
        self.last_scan_total = total_size
        self.last_scan_categories = category_totals
        self.lbl_metric.configure(text=self._format_size(total_size))
        self.lbl_metric_hint.configure(text=hint or "текущий объём кэша")
        self._draw_donut(category_totals)
        self._render_legend(category_totals)

    def _show_scan_results_window(self, title, summary, category_totals, total_size):
        self._apply_dashboard_update(category_totals, total_size, "можно безопасно освободить")

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
