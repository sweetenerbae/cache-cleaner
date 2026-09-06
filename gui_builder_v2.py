import os
import sys
import threading
import tkinter as tk
import tkinter.font as tkfont
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Callable, Dict, Optional

import customtkinter as ctk
from PIL import Image, ImageDraw


def resource_path(relative_path: str) -> str:
    base_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return str(base_path / relative_path)


class GUIBuilder:
    BG = "#050505"
    SIDEBAR = "#0B0B0B"
    SIDEBAR_ACTIVE = "#24230F"
    SURFACE = "#141414"
    SURFACE_ALT = "#1A1A1A"
    SURFACE_RAISED = "#242424"
    BORDER = "#303030"
    BORDER_SOFT = "#222222"
    TEXT = "#F5F5F5"
    MUTED = "#929292"
    ACCENT = "#FFEA00"
    ACCENT_HOVER = "#E6D300"
    CYAN = "#FFCC33"
    GREEN = "#B6F24A"
    RED = "#FF5C66"
    AMBER = "#FFB84D"
    TRACK = "#2B2B2B"

    CHART_COLORS = {
        "Windows": "#FFEA00",
        "Adobe": "#FF9D3D",
        "Discord": "#D45CFF",
        "Browsers": "#FF526C",
        "Applications": "#C56CFF",
        "Launchers": "#A9E84A",
        "Developer": "#FFC247",
        "Recycle Bin": "#FF5C66",
    }
    CATEGORY_LABELS = {
        "Windows": "Windows",
        "Adobe": "Adobe",
        "Discord": "Discord",
        "Browsers": "Браузеры",
        "Applications": "Приложения",
        "Launchers": "Лаунчеры",
        "Developer": "Dev-кэш",
        "Recycle Bin": "Корзина",
    }
    PAGE_META = {
        "overview": ("Обзор", "Состояние системы и быстрые сценарии очистки"),
        "statistics": ("Статистика", "Результаты очистки и использование дискового пространства"),
        "system": ("Система", "Временные файлы Windows и защита данных"),
        "applications": ("Приложения", "Браузеры, мессенджеры и медиаприложения"),
        "games": ("Игры", "Безопасная очистка кэша игровых лаунчеров"),
        "developer": ("Разработчик", "Кэши менеджеров пакетов и инструментов сборки"),
    }

    def __init__(
        self,
        cleanup_callback: Callable,
        restore_callback: Callable,
        scan_callback: Callable,
        statistics_callback: Optional[Callable] = None,
        running_apps_callback: Optional[Callable] = None,
        close_apps_callback: Optional[Callable] = None,
    ):
        self.cleanup_callback = cleanup_callback
        self.restore_callback = restore_callback
        self.scan_callback = scan_callback
        self.statistics_callback = statistics_callback
        self.running_apps_callback = running_apps_callback
        self.close_apps_callback = close_apps_callback
        self.root: Optional[ctk.CTk] = None
        self.user_folder: Optional[str] = None
        self.is_busy = False
        self.control_widgets = []
        self.developer_widgets = []
        self.brand_images: Dict[tuple, ctk.CTkImage] = {}
        self.pages = {}
        self.nav_buttons = {}
        self.summary_pills = []
        self._summary_legend_height = 0
        self.statistics_data: Dict = {}
        self.nav_labels = {
            "overview": "Обзор",
            "statistics": "Статистика",
            "system": "Система",
            "applications": "Приложения",
            "games": "Игры",
            "developer": "Разработчик",
        }
        self.current_page = "overview"
        self._layout_mode = None
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
        self.root.geometry("1280x820")
        self.root.minsize(860, 620)
        self.root.resizable(True, True)
        self._center_window(1280, 820)
        self._create_variables()
        self._create_shell()
        self.root.bind("<Configure>", self._on_root_configure)
        self.root.after_idle(lambda: self._apply_responsive_layout(self.root.winfo_width()))
        return self.root

    def _center_window(self, width: int, height: int):
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = max(0, (screen_width - width) // 2)
        y = max(0, (screen_height - height) // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def _create_variables(self):
        self.var_windows = ctk.BooleanVar(value=True)
        self.var_adobe = ctk.BooleanVar(value=True)
        self.var_discord = ctk.BooleanVar(value=True)
        self.var_backup = ctk.BooleanVar(value=True)
        self.var_recycle = ctk.BooleanVar(value=False)
        self.var_developer_mode = ctk.BooleanVar(value=False)
        self.var_browsers_master = ctk.BooleanVar(value=True)
        self.var_applications_master = ctk.BooleanVar(value=False)
        self.var_games_master = ctk.BooleanVar(value=False)
        self.browser_vars = {
            key: ctk.BooleanVar(value=True)
            for key in ("chrome", "firefox", "edge", "brave", "yandex")
        }
        self.application_vars = {
            key: ctk.BooleanVar(value=False)
            for key in ("telegram", "teams", "spotify")
        }
        self.launcher_vars = {
            key: ctk.BooleanVar(value=False)
            for key in ("steam", "epic", "battlenet")
        }
        self.developer_vars = {
            key: ctk.BooleanVar(value=True)
            for key in ("pip", "npm", "pnpm", "yarn", "gradle", "nuget")
        }

    def _create_shell(self):
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)
        self._create_sidebar()

        self.main_shell = ctk.CTkFrame(self.root, fg_color=self.BG, corner_radius=0)
        self.main_shell.grid(row=0, column=1, sticky="nsew")
        self.main_shell.grid_columnconfigure(0, weight=1)
        self.main_shell.grid_rowconfigure(1, weight=1)
        self._create_header()

        self.page_host = ctk.CTkFrame(self.main_shell, fg_color="transparent")
        self.page_host.grid(row=1, column=0, sticky="nsew", padx=24, pady=(0, 12))
        self.page_host.grid_rowconfigure(0, weight=1)
        self.page_host.grid_columnconfigure(0, weight=1)
        self._create_pages()
        self._create_action_bar()
        self.show_page("overview")

    def _create_sidebar(self):
        self.sidebar = ctk.CTkFrame(
            self.root,
            width=238,
            fg_color=self.BG,
            corner_radius=0,
            border_width=0,
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_rowconfigure(0, weight=1)
        self.sidebar.grid_columnconfigure(0, weight=1)

        self.sidebar_glass = ctk.CTkFrame(
            self.sidebar,
            fg_color="#101010",
            corner_radius=24,
            border_width=1,
            border_color="#383838",
        )
        self.sidebar_glass.grid(row=0, column=0, sticky="nsew", padx=(10, 6), pady=10)
        self.sidebar_glass.grid_columnconfigure(0, weight=1)
        self.sidebar_glass.grid_rowconfigure(2, weight=1)
        ctk.CTkFrame(
            self.sidebar_glass, height=2, fg_color="#575757", corner_radius=2
        ).place(relx=.12, rely=0, relwidth=.76, y=1)
        ctk.CTkFrame(
            self.sidebar_glass, width=3, fg_color="#6B6400", corner_radius=3
        ).place(relx=1, rely=.12, relheight=.72, x=-3, anchor="ne")

        brand = ctk.CTkFrame(self.sidebar_glass, fg_color="transparent", height=104)
        brand.grid(row=0, column=0, sticky="ew", padx=18, pady=(20, 8))
        brand.grid_propagate(False)
        brand.grid_columnconfigure(1, weight=1)
        try:
            logo_source = Image.open(resource_path("assets/cache_cleaner_logo.png"))
            self.logo_image = ctk.CTkImage(logo_source, logo_source, size=(48, 48))
            ctk.CTkLabel(brand, text="", image=self.logo_image, width=52).grid(
                row=0, column=0, rowspan=2, sticky="w"
            )
        except OSError:
            ctk.CTkLabel(brand, text="✦", text_color=self.CYAN, font=ctk.CTkFont(size=28)).grid(
                row=0, column=0, rowspan=2
            )
        self.brand_title = ctk.CTkLabel(
            brand, text="Cache Cleaner", text_color=self.TEXT,
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
        )
        self.brand_title.grid(row=0, column=1, sticky="sw", padx=(10, 0), pady=(8, 0))
        self.brand_subtitle = ctk.CTkLabel(
            brand, text="SMART CLEAN", text_color=self.MUTED,
            font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"),
        )
        self.brand_subtitle.grid(row=1, column=1, sticky="nw", padx=(10, 0), pady=(2, 8))

        divider = ctk.CTkFrame(self.sidebar_glass, height=1, fg_color="#303030")
        divider.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 14))

        nav = ctk.CTkFrame(self.sidebar_glass, fg_color="transparent")
        nav.grid(row=2, column=0, sticky="nsew", padx=12)
        nav.grid_columnconfigure(0, weight=1)
        nav_items = [
            ("overview", "Обзор", "cache_cleaner_logo.png", True),
            ("statistics", "Статистика", None, False),
            ("system", "Система", "brand-icons/windows.png", False),
            ("applications", "Приложения", "brand-icons/telegram.png", False),
            ("games", "Игры", "brand-icons/steam.png", False),
            ("developer", "Разработчик", "brand-icons/pypi.png", False),
        ]
        for row, (key, label, image_path, is_logo) in enumerate(nav_items):
            image = self._statistics_image(22) if key == "statistics" else self._asset_image(
                image_path, 22 if not is_logo else 24
            )
            button = ctk.CTkButton(
                nav,
                text=label,
                image=image,
                compound="left",
                anchor="w",
                command=lambda page=key: self.show_page(page),
                height=44,
                corner_radius=12,
                fg_color="#101010",
                hover_color="#292929",
                border_width=1,
                border_color="#242424",
                text_color="#C8C8C8",
                font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            )
            button.grid(row=row, column=0, sticky="ew", pady=2)
            self.nav_buttons[key] = button

        backup_button = ctk.CTkButton(
            nav,
            text="Бэкапы",
            image=self._brand_image("backup", 22),
            compound="left",
            anchor="w",
            command=self.restore_callback,
            height=44,
            corner_radius=12,
            fg_color="#101010",
            hover_color="#292929",
            border_width=1,
            border_color="#242424",
            text_color="#C8C8C8",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
        )
        backup_button.grid(row=len(nav_items), column=0, sticky="ew", pady=2)
        self.nav_buttons["backups"] = backup_button
        self.control_widgets.append(backup_button)

        footer = ctk.CTkFrame(
            self.sidebar_glass, fg_color="#1B1B0F", corner_radius=14,
            border_width=1, border_color="#4A4718",
        )
        footer.grid(row=3, column=0, sticky="ew", padx=14, pady=18)
        self.sidebar_status_icon = ctk.CTkLabel(
            footer, text="", image=self._brand_image("backup", 24), width=32
        )
        self.sidebar_status_icon.pack(side="left", padx=(12, 5), pady=12)
        self.sidebar_status_text = ctk.CTkLabel(
            footer, text="Безопасная\nочистка", justify="left", text_color=self.GREEN,
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
        )
        self.sidebar_status_text.pack(side="left", pady=10)

    def _create_header(self):
        header = ctk.CTkFrame(self.main_shell, height=92, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=28, pady=(6, 0))
        header.grid_propagate(False)
        header.grid_columnconfigure(0, weight=1)
        self.page_title = ctk.CTkLabel(
            header, text="Обзор", text_color=self.TEXT,
            font=ctk.CTkFont(family="Segoe UI", size=26, weight="bold"),
        )
        self.page_title.grid(row=0, column=0, sticky="sw", pady=(15, 0))
        self.page_subtitle = ctk.CTkLabel(
            header, text="", text_color=self.MUTED,
            font=ctk.CTkFont(family="Segoe UI", size=11),
        )
        self.page_subtitle.grid(row=1, column=0, sticky="nw", pady=(2, 10))
        self.ready_badge = ctk.CTkLabel(
            header, text="●  Система готова", text_color=self.GREEN,
            fg_color="#1B1B0F", corner_radius=14, width=148, height=34,
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
        )
        self.ready_badge.grid(row=0, column=1, rowspan=2, sticky="e")

    def _create_pages(self):
        self.pages["overview"] = self._create_page()
        self.pages["statistics"] = self._create_page()
        self.pages["system"] = self._create_page()
        self.pages["applications"] = self._create_page()
        self.pages["games"] = self._create_page()
        self.pages["developer"] = self._create_page()
        self._build_overview(self.pages["overview"])
        self._build_statistics_page(self.pages["statistics"])
        self._build_system_page(self.pages["system"])
        self._build_applications_page(self.pages["applications"])
        self._build_games_page(self.pages["games"])
        self._build_developer_page(self.pages["developer"])

    def _create_page(self):
        page = ctk.CTkScrollableFrame(
            self.page_host,
            fg_color="transparent",
            corner_radius=0,
            scrollbar_button_color=self.BORDER,
            scrollbar_button_hover_color="#4A4A4A",
        )
        page.grid(row=0, column=0, sticky="nsew")
        page.grid_columnconfigure(0, weight=1)
        return page

    def _build_overview(self, page):
        top = ctk.CTkFrame(page, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew")
        top.grid_columnconfigure(0, weight=2)
        top.grid_columnconfigure(1, weight=1)

        summary = self._glass_card(top)
        summary.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        summary.grid_columnconfigure(1, weight=1)
        self.chart = tk.Canvas(summary, width=250, height=230, bg=self.SURFACE, highlightthickness=0)
        self.chart.grid(row=0, column=0, rowspan=3, padx=(18, 2), pady=10)
        self._draw_donut({})
        self.lbl_metric = ctk.CTkLabel(
            summary, text="—", text_color=self.TEXT,
            font=ctk.CTkFont(family="Segoe UI", size=31, weight="bold"),
        )
        self.lbl_metric.grid(row=0, column=1, sticky="sw", padx=12, pady=(28, 0))
        self.lbl_metric_hint = ctk.CTkLabel(
            summary, text="Запустите сканирование", text_color=self.MUTED,
            font=ctk.CTkFont(family="Segoe UI", size=11),
        )
        self.lbl_metric_hint.grid(row=1, column=1, sticky="nw", padx=12, pady=(3, 6))
        self.summary_legend = ctk.CTkFrame(summary, fg_color="transparent")
        self.summary_legend.grid(row=2, column=1, sticky="nsew", padx=(8, 18), pady=(0, 16))
        self.summary_legend.grid_propagate(False)
        self.summary_legend.bind("<Configure>", self._layout_summary_pills)
        self._render_summary_legend({})

        safety = self._glass_card(top)
        safety.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
        ctk.CTkLabel(safety, text="", image=self._brand_image("backup", 44)).pack(
            anchor="w", padx=22, pady=(25, 12)
        )
        ctk.CTkLabel(
            safety, text="Система в порядке", text_color=self.TEXT,
            font=ctk.CTkFont(family="Segoe UI", size=17, weight="bold"),
        ).pack(anchor="w", padx=22)
        ctk.CTkLabel(
            safety,
            text="Проверяем только безопасные\nкэши и временные файлы.",
            justify="left", text_color=self.MUTED,
            font=ctk.CTkFont(family="Segoe UI", size=11),
        ).pack(anchor="w", padx=22, pady=(7, 18))
        ctk.CTkLabel(
            safety, text="✓  Безопасно и надёжно", text_color=self.GREEN,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
        ).pack(anchor="w", padx=22, pady=(0, 22))

        ctk.CTkLabel(
            page, text="Быстрые режимы", text_color=self.TEXT,
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
        ).grid(row=1, column=0, sticky="w", pady=(18, 9))
        presets = ctk.CTkFrame(page, fg_color="transparent")
        presets.grid(row=2, column=0, sticky="ew")
        presets.grid_columnconfigure((0, 1, 2), weight=1, uniform="preset")
        self._preset_card(presets, 0, "Быстрая очистка", "Система и браузеры", "windows", self._preset_quick)
        self._preset_card(presets, 1, "Игровой режим", "Лаунчеры и временные файлы", "steam", self._preset_gaming)
        self._preset_card(presets, 2, "Для разработчика", "Кэши пакетов и сборок", "pypi", self._preset_developer)

        ctk.CTkLabel(
            page, text="План очистки", text_color=self.TEXT,
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
        ).grid(row=3, column=0, sticky="w", pady=(18, 9))
        plan = ctk.CTkFrame(page, fg_color="transparent")
        plan.grid(row=4, column=0, sticky="ew", pady=(0, 12))
        plan.grid_columnconfigure((0, 1, 2), weight=1, uniform="plan")
        cards = [
            ("Windows", "Временные файлы", "windows", self.var_windows, self.ACCENT, None),
            ("Браузеры", "Chrome, Firefox и другие", "chrome", self.var_browsers_master, self.CYAN, self._toggle_all_browsers),
            ("Приложения", "Telegram, Teams, Spotify", "telegram", self.var_applications_master, self.CYAN, self._toggle_all_applications),
            ("Игры", "Steam, Epic, Battle.net", "steam", self.var_games_master, self.ACCENT, self._toggle_all_games),
            ("Dev-кэш", "pip, npm, Gradle и другие", "pypi", self.var_developer_mode, self.AMBER, self._update_developer_state),
            ("Корзина", "Безвозвратное удаление", "recycle", self.var_recycle, self.RED, None),
        ]
        for index, data in enumerate(cards):
            self._overview_option(plan, index // 3, index % 3, *data)

    def _build_statistics_page(self, page):
        metrics = ctk.CTkFrame(page, fg_color="transparent")
        metrics.grid(row=0, column=0, sticky="ew")
        metrics.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="metric")
        self.statistics_labels = {}
        metric_data = [
            ("today", "Очищено сегодня", "0 B", self.ACCENT),
            ("total", "За всё время", "0 B", "#FF526C"),
            ("files", "Удалено файлов", "0", "#C56CFF"),
            ("backups", "Бэкапы", "0 B", self.GREEN),
        ]
        for column, (key, title, value, color) in enumerate(metric_data):
            card = self._glass_card(metrics)
            card.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 6, 0 if column == 3 else 6))
            ctk.CTkFrame(card, width=4, height=38, fg_color=color, corner_radius=2).pack(
                side="left", padx=(15, 10), pady=18
            )
            body = ctk.CTkFrame(card, fg_color="transparent")
            body.pack(side="left", fill="both", expand=True, pady=13)
            ctk.CTkLabel(
                body, text=title, text_color=self.MUTED,
                font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"),
            ).pack(anchor="w")
            label = ctk.CTkLabel(
                body, text=value, text_color=self.TEXT,
                font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            )
            label.pack(anchor="w", pady=(2, 0))
            self.statistics_labels[key] = label

        content = ctk.CTkFrame(page, fg_color="transparent")
        content.grid(row=1, column=0, sticky="nsew", pady=(14, 12))
        content.grid_columnconfigure(0, weight=2)
        content.grid_columnconfigure(1, weight=1)

        history_card = self._glass_card(content)
        history_card.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        ctk.CTkLabel(
            history_card, text="Динамика за 7 дней", text_color=self.TEXT,
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(18, 2))
        ctk.CTkLabel(
            history_card, text="Сколько места освобождено каждый день", text_color=self.MUTED,
            font=ctk.CTkFont(family="Segoe UI", size=10),
        ).pack(anchor="w", padx=20)
        self.statistics_chart = tk.Canvas(
            history_card, height=270, bg=self.SURFACE, highlightthickness=0
        )
        self.statistics_chart.pack(fill="both", expand=True, padx=14, pady=(8, 14))
        self.statistics_chart.bind("<Configure>", self._draw_statistics_chart)

        categories_card = self._glass_card(content)
        categories_card.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
        ctk.CTkLabel(
            categories_card, text="Самые объёмные", text_color=self.TEXT,
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(18, 2))
        ctk.CTkLabel(
            categories_card, text="Категории за всё время", text_color=self.MUTED,
            font=ctk.CTkFont(family="Segoe UI", size=10),
        ).pack(anchor="w", padx=20)
        self.statistics_categories = ctk.CTkFrame(categories_card, fg_color="transparent")
        self.statistics_categories.pack(fill="both", expand=True, padx=18, pady=14)

        note = self._glass_card(page)
        note.grid(row=2, column=0, sticky="ew")
        ctk.CTkLabel(
            note, text="●  Статистика хранится только на этом компьютере",
            text_color=self.GREEN, font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
        ).pack(side="left", padx=18, pady=15)
        ctk.CTkLabel(
            note, text="Никакой телеметрии и отправки данных",
            text_color=self.MUTED, font=ctk.CTkFont(family="Segoe UI", size=10),
        ).pack(side="right", padx=18, pady=15)
        self.root.after_idle(self.refresh_statistics)

    def refresh_statistics(self):
        if not self.statistics_callback or not self.root:
            return
        if threading.current_thread() is not threading.main_thread():
            self.root.after(0, self.refresh_statistics)
            return
        try:
            data = self.statistics_callback() or {}
        except (OSError, ValueError, TypeError):
            data = {}
        self.statistics_data = data
        if not hasattr(self, "statistics_labels"):
            return
        self.statistics_labels["today"].configure(
            text=self._format_size(int(data.get("today_cleaned_bytes", 0)))
        )
        self.statistics_labels["total"].configure(
            text=self._format_size(int(data.get("total_cleaned_bytes", 0)))
        )
        self.statistics_labels["files"].configure(
            text=f"{int(data.get('total_deleted_files', 0)):,}".replace(",", " ")
        )
        backup_size = self._format_size(int(data.get("backup_bytes", 0)))
        self.statistics_labels["backups"].configure(
            text=f"{backup_size} · {int(data.get('backup_count', 0))} шт."
        )
        self._render_statistics_categories(data.get("categories", []))
        self._draw_statistics_chart()

    def _draw_statistics_chart(self, _event=None):
        if not hasattr(self, "statistics_chart"):
            return
        canvas = self.statistics_chart
        canvas.delete("all")
        history = self.statistics_data.get("history", [])
        width = max(420, canvas.winfo_width())
        height = max(220, canvas.winfo_height())
        left, right, top, bottom = 42, 18, 24, 38
        chart_width = width - left - right
        chart_height = height - top - bottom
        canvas.create_line(left, top + chart_height, width - right, top + chart_height, fill="#353535")
        if not history:
            canvas.create_text(width / 2, height / 2, text="Статистика появится после первой очистки", fill=self.MUTED, font=("Segoe UI", 11))
            return
        maximum = max((int(item.get("cleaned_bytes", 0)) for item in history), default=0)
        maximum = max(maximum, 1)
        slot = chart_width / max(len(history), 1)
        bar_width = min(48, slot * .56)
        for index, item in enumerate(history):
            value = int(item.get("cleaned_bytes", 0))
            bar_height = (value / maximum) * (chart_height - 26) if value else 3
            x = left + slot * index + slot / 2
            y0 = top + chart_height - bar_height
            canvas.create_rectangle(
                x - bar_width / 2, y0, x + bar_width / 2, top + chart_height,
                fill=self.ACCENT if value else "#343434", outline="",
            )
            if value:
                canvas.create_text(x, max(10, y0 - 10), text=self._format_size(value), fill=self.TEXT, font=("Segoe UI", 8, "bold"))
            canvas.create_text(x, height - 17, text=item.get("label", ""), fill=self.MUTED, font=("Segoe UI", 8))

    def _render_statistics_categories(self, categories):
        for child in self.statistics_categories.winfo_children():
            child.destroy()
        if not categories:
            ctk.CTkLabel(
                self.statistics_categories,
                text="Пока нет данных\nЗапустите первую очистку",
                justify="left", text_color=self.MUTED,
                font=ctk.CTkFont(family="Segoe UI", size=11),
            ).pack(anchor="w", pady=12)
            return
        maximum = max(int(item.get("cleaned_bytes", 0)) for item in categories) or 1
        for item in categories:
            name = item.get("name", "")
            size = int(item.get("cleaned_bytes", 0))
            row = ctk.CTkFrame(self.statistics_categories, fg_color="transparent")
            row.pack(fill="x", pady=7)
            ctk.CTkLabel(
                row, text=self.CATEGORY_LABELS.get(name, name), text_color=self.TEXT,
                font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            ).pack(anchor="w")
            ctk.CTkLabel(
                row, text=self._format_size(size), text_color=self.MUTED,
                font=ctk.CTkFont(family="Segoe UI", size=9),
            ).pack(anchor="e")
            progress = ctk.CTkProgressBar(
                row, height=5, corner_radius=3, fg_color="#303030",
                progress_color=self.CHART_COLORS.get(name, self.ACCENT),
            )
            progress.pack(fill="x", pady=(3, 0))
            progress.set(size / maximum)

    def _build_system_page(self, page):
        intro = self._section_intro(page, "Безопасная системная очистка", "Выберите только те данные, которые хотите удалить.")
        intro.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        grid = ctk.CTkFrame(page, fg_color="transparent")
        grid.grid(row=1, column=0, sticky="ew")
        grid.grid_columnconfigure((0, 1), weight=1, uniform="system")
        self._large_option(grid, 0, 0, "Временные файлы Windows", "TEMP, Windows Temp и Prefetch", "windows", self.var_windows, self.ACCENT)
        self._large_option(grid, 0, 1, "Корзина", "Потребуется отдельное подтверждение", "recycle", self.var_recycle, self.RED)
        self._large_option(grid, 1, 0, "Защита перед очисткой", "Создать проверенный сжатый ZIP-бэкап", "backup", self.var_backup, self.GREEN)

    def _build_applications_page(self, page):
        intro = self._section_intro(page, "Кэши приложений", "Закройте выбранные программы, чтобы очистить больше файлов.")
        intro.grid(row=0, column=0, sticky="ew", pady=(0, 14))

        core = ctk.CTkFrame(page, fg_color="transparent")
        core.grid(row=1, column=0, sticky="ew")
        core.grid_columnconfigure((0, 1), weight=1, uniform="core")
        self._large_option(core, 0, 0, "Adobe", "Media Cache, превью и временные файлы", "adobe", self.var_adobe, "#F2A365")
        self._large_option(core, 0, 1, "Discord", "Cache, Code Cache и GPUCache", "discord", self.var_discord, "#9C7BEF")

        adobe_path = self._glass_card(page)
        adobe_path.grid(row=2, column=0, sticky="ew", pady=(12, 18))
        adobe_path.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            adobe_path, text="Дополнительная папка Adobe", text_color=self.TEXT,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
        ).grid(row=0, column=0, sticky="sw", padx=18, pady=(12, 0))
        self.lbl_adobe = ctk.CTkLabel(
            adobe_path, text="Автоматический поиск", text_color=self.MUTED,
            font=ctk.CTkFont(family="Segoe UI", size=10),
        )
        self.lbl_adobe.grid(row=1, column=0, sticky="nw", padx=18, pady=(2, 12))
        button = ctk.CTkButton(
            adobe_path, text="Изменить", command=self._choose_adobe_folder,
            width=94, height=34, corner_radius=10, fg_color=self.SURFACE_RAISED,
            hover_color="#2A2A2A", border_width=1, border_color=self.BORDER,
            font=ctk.CTkFont(family="Segoe UI", size=11),
        )
        button.grid(row=0, column=1, rowspan=2, padx=16)
        self.control_widgets.append(button)

        self._choice_section(
            page, 3, "Браузеры", self.browser_vars,
            [("chrome", "Chrome"), ("firefox", "Firefox"), ("edge", "Edge"), ("brave", "Brave"), ("yandex", "Yandex")],
            self.CYAN,
        )
        self._choice_section(
            page, 4, "Мессенджеры и музыка", self.application_vars,
            [("telegram", "Telegram"), ("teams", "Teams"), ("spotify", "Spotify")],
            self.CYAN,
        )

    def _build_games_page(self, page):
        intro = self._section_intro(page, "Игровая очистка", "Игры и сохранения не удаляются — только веб-кэш интерфейса лаунчеров.")
        intro.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        self._choice_section(
            page, 2, "Игровые лаунчеры", self.launcher_vars,
            [("steam", "Steam"), ("epic", "Epic Games"), ("battlenet", "Battle.net")],
            self.ACCENT,
            descriptions={
                "steam": "Веб-кэш и интерфейс",
                "epic": "Кэш Epic Games Launcher",
                "battlenet": "Кэш клиента Battle.net",
            },
        )

    def _build_developer_page(self, page):
        intro = self._section_intro(page, "Режим разработчика", "Зависимости при необходимости будут скачаны заново.")
        intro.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        master = self._glass_card(page)
        master.grid(row=1, column=0, sticky="ew", pady=(0, 16))
        master.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(master, text="", image=self._brand_image("pypi", 42), width=58).grid(
            row=0, column=0, rowspan=2, padx=(18, 8), pady=16
        )
        ctk.CTkLabel(
            master, text="Включить Dev-режим", text_color=self.TEXT,
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
        ).grid(row=0, column=1, sticky="sw", pady=(17, 0))
        ctk.CTkLabel(
            master, text="Даёт доступ к очистке локальных кэшей пакетов", text_color=self.MUTED,
            font=ctk.CTkFont(family="Segoe UI", size=10),
        ).grid(row=1, column=1, sticky="nw", pady=(3, 17))
        switch = self._switch(master, self.var_developer_mode, self.AMBER, self._update_developer_state)
        switch.grid(row=0, column=2, rowspan=2, padx=20)

        self._choice_section(
            page, 2, "Инструменты", self.developer_vars,
            [("pip", "pip / PyPI"), ("npm", "npm"), ("pnpm", "pnpm"), ("yarn", "Yarn"), ("gradle", "Gradle"), ("nuget", "NuGet")],
            self.AMBER,
            developer=True,
        )
        self._update_developer_state()

    def _create_action_bar(self):
        bar = ctk.CTkFrame(
            self.main_shell, height=76, fg_color="#101010", corner_radius=16,
            border_width=1, border_color=self.BORDER_SOFT,
        )
        bar.grid(row=2, column=0, sticky="ew", padx=24, pady=(0, 16))
        bar.grid_propagate(False)
        bar.grid_columnconfigure(0, weight=1)
        self.action_hint = ctk.CTkLabel(
            bar, text="◈  Готово к безопасной очистке", text_color=self.MUTED,
            font=ctk.CTkFont(family="Segoe UI", size=11),
        )
        self.action_hint.grid(row=0, column=0, sticky="w", padx=18)
        self.btn_restore = ctk.CTkButton(
            bar, text="Бэкапы", image=self._brand_image("backup", 18), command=self.restore_callback,
            width=118, height=44, corner_radius=12, fg_color="transparent",
            hover_color=self.SURFACE_RAISED, border_width=1, border_color=self.BORDER,
            font=ctk.CTkFont(family="Segoe UI", size=11),
        )
        self.btn_restore.grid(row=0, column=1, padx=(8, 0), pady=15)
        self.btn_scan = ctk.CTkButton(
            bar, text="Сканировать", command=self._on_scan,
            width=164, height=44, corner_radius=12, fg_color=self.SURFACE_RAISED,
            hover_color="#2A2A2A", border_width=1, border_color="#3A3A3A",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
        )
        self.btn_scan.grid(row=0, column=2, padx=10, pady=15)
        self.btn_cleanup = ctk.CTkButton(
            bar, text="Начать очистку", command=self._on_cleanup,
            width=186, height=46, corner_radius=12, fg_color=self.ACCENT,
            hover_color=self.ACCENT_HOVER, text_color="#090909",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
        )
        self.btn_cleanup.grid(row=0, column=3, padx=(0, 16), pady=15)
        self.control_widgets.extend([self.btn_restore, self.btn_scan, self.btn_cleanup])

        self.progress_strip = ctk.CTkProgressBar(
            bar, height=2, corner_radius=0, fg_color="#101010", progress_color=self.ACCENT
        )
        self.progress_strip.place(relx=0, rely=1, relwidth=1, y=-2)
        self.progress_strip.set(0)
        self.lbl_status = self.action_hint
        self.progress = self.progress_strip

    def show_page(self, page_name: str):
        if page_name not in self.pages:
            return
        self._sync_master_vars()
        if page_name == "statistics":
            self.refresh_statistics()
        self.current_page = page_name
        for name, page in self.pages.items():
            if name == page_name:
                page.grid()
            else:
                page.grid_remove()
        title, subtitle = self.PAGE_META[page_name]
        self.page_title.configure(text=title)
        self.page_subtitle.configure(text=subtitle)
        for name, button in self.nav_buttons.items():
            if name == page_name:
                button.configure(
                    fg_color=self.SIDEBAR_ACTIVE,
                    text_color=self.TEXT,
                    border_color="#706900",
                )
            else:
                button.configure(
                    fg_color="#101010",
                    text_color="#C8C8C8",
                    border_color="#242424",
                )

    def _glass_card(self, parent):
        return ctk.CTkFrame(
            parent, fg_color=self.SURFACE, corner_radius=17,
            border_width=1, border_color=self.BORDER,
        )

    def _section_intro(self, parent, title: str, text: str):
        frame = self._glass_card(parent)
        ctk.CTkLabel(
            frame, text=title, text_color=self.TEXT,
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(17, 3))
        ctk.CTkLabel(
            frame, text=text, text_color=self.MUTED,
            font=ctk.CTkFont(family="Segoe UI", size=11),
        ).pack(anchor="w", padx=20, pady=(0, 17))
        return frame

    def _preset_card(self, parent, column, title, subtitle, icon, command):
        button = ctk.CTkButton(
            parent, text=f"{title}\n{subtitle}", image=self._brand_image(icon, 35),
            compound="left", anchor="w", command=command, height=88,
            corner_radius=15, fg_color=self.SURFACE, hover_color="#292929",
            border_width=1, border_color=self.BORDER, text_color=self.TEXT,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
        )
        button.grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else 6, 0 if column == 2 else 6))
        self.control_widgets.append(button)

    def _overview_option(self, parent, row, column, title, subtitle, icon, variable, accent, command):
        card = self._glass_card(parent)
        card.grid(row=row, column=column, sticky="nsew", padx=5, pady=5)
        card.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(card, text="", image=self._brand_image(icon, 34), width=46).grid(
            row=0, column=0, rowspan=2, padx=(12, 4), pady=14
        )
        ctk.CTkLabel(
            card, text=title, text_color=self.TEXT,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
        ).grid(row=0, column=1, sticky="sw", pady=(13, 0))
        ctk.CTkLabel(
            card, text=subtitle, text_color=self.MUTED,
            font=ctk.CTkFont(family="Segoe UI", size=9),
        ).grid(row=1, column=1, sticky="nw", pady=(2, 13))
        switch = self._switch(card, variable, accent, command)
        switch.grid(row=0, column=2, rowspan=2, padx=13)

    def _large_option(self, parent, row, column, title, subtitle, icon, variable, accent):
        card = self._glass_card(parent)
        card.grid(row=row, column=column, sticky="nsew", padx=6, pady=6)
        card.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(card, text="", image=self._brand_image(icon, 42), width=58).grid(
            row=0, column=0, rowspan=2, padx=(16, 6), pady=19
        )
        ctk.CTkLabel(
            card, text=title, text_color=self.TEXT,
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
        ).grid(row=0, column=1, sticky="sw", pady=(18, 0))
        ctk.CTkLabel(
            card, text=subtitle, text_color=self.MUTED,
            font=ctk.CTkFont(family="Segoe UI", size=10),
        ).grid(row=1, column=1, sticky="nw", pady=(3, 18))
        switch = self._switch(card, variable, accent)
        switch.grid(row=0, column=2, rowspan=2, padx=18)

    def _choice_section(self, page, row, title, variables, choices, accent, descriptions=None, developer=False):
        ctk.CTkLabel(
            page, text=title, text_color=self.TEXT,
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
        ).grid(row=row * 2 - 2, column=0, sticky="w", pady=(0 if row == 1 else 16, 8))
        grid = ctk.CTkFrame(page, fg_color="transparent")
        grid.grid(row=row * 2 - 1, column=0, sticky="ew")
        grid.grid_columnconfigure((0, 1, 2), weight=1, uniform=f"choices-{row}")
        for index, (key, label) in enumerate(choices):
            description = (descriptions or {}).get(key, "Выбрать для очистки")
            icon_name = "pypi" if key == "pip" else key
            card = self._glass_card(grid)
            card.grid(row=index // 3, column=index % 3, sticky="nsew", padx=5, pady=5)
            card.grid_columnconfigure(1, weight=1)
            ctk.CTkLabel(card, text="", image=self._brand_image(icon_name, 32), width=44).grid(
                row=0, column=0, rowspan=2, padx=(11, 3), pady=13
            )
            ctk.CTkLabel(
                card, text=label, text_color=self.TEXT,
                font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            ).grid(row=0, column=1, sticky="sw", pady=(12, 0))
            ctk.CTkLabel(
                card, text=description, text_color=self.MUTED,
                font=ctk.CTkFont(family="Segoe UI", size=9),
            ).grid(row=1, column=1, sticky="nw", pady=(2, 12))
            checkbox = ctk.CTkCheckBox(
                card, text="", variable=variables[key], width=22,
                checkbox_width=21, checkbox_height=21, corner_radius=7,
                border_width=1, border_color="#5A5A5A", fg_color=accent,
                hover_color=accent, command=self._sync_master_vars,
            )
            checkbox.grid(row=0, column=2, rowspan=2, padx=13)
            self.control_widgets.append(checkbox)
            if developer:
                self.developer_widgets.append(checkbox)

    def _switch(self, parent, variable, accent, command=None):
        switch = ctk.CTkSwitch(
            parent, text="", variable=variable, command=command,
            width=44, height=24, switch_width=44, switch_height=24,
            corner_radius=12, border_width=0, fg_color="#3A3A3A",
            progress_color=accent, button_color="#F5F5F5", button_hover_color="#FFFFFF",
        )
        self.control_widgets.append(switch)
        return switch

    def _asset_image(self, relative_asset: str, size: int):
        key = (relative_asset, size)
        if key not in self.brand_images:
            try:
                source = Image.open(resource_path(f"assets/{relative_asset}"))
                self.brand_images[key] = ctk.CTkImage(source, source, size=(size, size))
            except OSError:
                return None
        return self.brand_images[key]

    def _brand_image(self, name: str, size: int = 22):
        return self._asset_image(f"brand-icons/{name}.png", size)

    def _statistics_image(self, size: int = 22):
        key = ("statistics-icon", size)
        if key not in self.brand_images:
            scale = 3
            source = Image.new("RGBA", (size * scale, size * scale), (0, 0, 0, 0))
            draw = ImageDraw.Draw(source)
            color = (255, 234, 0, 255)
            gap = max(2, size * scale // 12)
            bar_width = max(4, size * scale // 7)
            heights = (.38, .68, .92)
            x = gap * 2
            baseline = size * scale - gap * 2
            for ratio in heights:
                height = int((size * scale - gap * 4) * ratio)
                draw.rounded_rectangle(
                    (x, baseline - height, x + bar_width, baseline),
                    radius=max(2, bar_width // 3), fill=color,
                )
                x += bar_width + gap
            self.brand_images[key] = ctk.CTkImage(source, source, size=(size, size))
        return self.brand_images[key]

    def _draw_donut(self, category_totals: Dict[str, int]):
        self.chart.delete("all")
        x0, y0, x1, y1 = 35, 20, 215, 200
        total = sum(category_totals.values())
        self.chart.create_oval(x0, y0, x1, y1, outline=self.TRACK, width=21)
        if total > 0:
            start = 90
            for category, size in category_totals.items():
                if size <= 0:
                    continue
                extent = -(size / total) * 359.8
                self.chart.create_arc(
                    x0, y0, x1, y1, start=start, extent=extent, style="arc",
                    outline=self.CHART_COLORS.get(category, self.ACCENT), width=21,
                )
                start += extent
        self.chart.create_text(
            125, 99, text="КЭШ" if total == 0 else "НАЙДЕНО",
            fill=self.MUTED, font=("Segoe UI", 9),
        )
        self.chart.create_text(
            125, 126, text="Готово" if total == 0 else self._format_size(total),
            fill=self.TEXT, font=("Segoe UI", 17, "bold"),
        )

    def _render_summary_legend(self, category_totals: Dict[str, int]):
        for child in self.summary_legend.winfo_children():
            child.destroy()
        self.summary_pills = []
        values = category_totals or {"Windows": 0, "Browsers": 0, "Applications": 0, "Launchers": 0}
        legend_font = tkfont.Font(root=self.root, family="Segoe UI", size=9, weight="bold")
        for category, size in values.items():
            label = self.CATEGORY_LABELS.get(category, category)
            value = self._format_size(size) if category_totals else label
            display_text = f"{label}: {value}" if category_totals else value
            item = ctk.CTkFrame(
                self.summary_legend,
                height=30,
                fg_color="#202020",
                corner_radius=15,
                border_width=1,
                border_color="#3A3A3A",
            )
            item.pack_propagate(False)
            item.flow_width = max(86, legend_font.measure(display_text) + 36)
            ctk.CTkLabel(
                item, text="●", width=13, text_color=self.CHART_COLORS.get(category, self.ACCENT),
                font=ctk.CTkFont(size=10),
            ).pack(side="left", padx=(8, 1))
            ctk.CTkLabel(
                item, text=display_text,
                text_color="#D0D0D0", font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"),
            ).pack(side="left", padx=(0, 9))
            self.summary_pills.append(item)
        self.summary_legend.after_idle(self._layout_summary_pills)

    def _layout_summary_pills(self, _event=None):
        if not self.summary_pills:
            return
        available_width = self.summary_legend.winfo_width()
        if available_width <= 1:
            self.summary_legend.after(20, self._layout_summary_pills)
            return
        gap = 6
        pill_height = 30
        x = 0
        y = 0
        for pill in self.summary_pills:
            pill_width = min(pill.flow_width, available_width)
            if x and x + pill_width > available_width:
                x = 0
                y += pill_height + gap
            pill.configure(width=pill_width, height=pill_height)
            pill.place(x=x, y=y)
            x += pill_width + gap
        required_height = y + pill_height
        if required_height != self._summary_legend_height:
            self._summary_legend_height = required_height
            self.summary_legend.configure(height=required_height)

    def _preset_quick(self):
        self.var_windows.set(True)
        self.var_recycle.set(False)
        self.var_adobe.set(False)
        self.var_discord.set(False)
        self.var_developer_mode.set(False)
        self._set_group(self.browser_vars, True)
        self._set_group(self.application_vars, False)
        self._set_group(self.launcher_vars, False)
        self.var_browsers_master.set(True)
        self.var_applications_master.set(False)
        self.var_games_master.set(False)
        self.var_backup.set(True)
        self._update_developer_state()
        self._preset_feedback("Быстрый режим выбран")

    def _preset_gaming(self):
        self.var_windows.set(True)
        self.var_recycle.set(False)
        self.var_developer_mode.set(False)
        self._set_group(self.browser_vars, False)
        self._set_group(self.application_vars, False)
        self._set_group(self.launcher_vars, True)
        self.var_browsers_master.set(False)
        self.var_applications_master.set(False)
        self.var_games_master.set(True)
        self.var_backup.set(True)
        self._update_developer_state()
        self._preset_feedback("Игровой режим выбран")

    def _preset_developer(self):
        self.var_windows.set(False)
        self.var_recycle.set(False)
        self.var_developer_mode.set(True)
        self._set_group(self.browser_vars, False)
        self._set_group(self.application_vars, False)
        self._set_group(self.launcher_vars, False)
        self._set_group(self.developer_vars, True)
        self.var_browsers_master.set(False)
        self.var_applications_master.set(False)
        self.var_games_master.set(False)
        self.var_backup.set(True)
        self._update_developer_state()
        self._preset_feedback("Режим разработчика выбран")

    @staticmethod
    def _set_group(group, enabled):
        for variable in group.values():
            variable.set(enabled)

    def _sync_master_vars(self):
        self.var_browsers_master.set(all(variable.get() for variable in self.browser_vars.values()))
        self.var_applications_master.set(all(variable.get() for variable in self.application_vars.values()))
        self.var_games_master.set(all(variable.get() for variable in self.launcher_vars.values()))

    def _toggle_all_browsers(self):
        self._set_group(self.browser_vars, self.var_browsers_master.get())

    def _toggle_all_applications(self):
        self._set_group(self.application_vars, self.var_applications_master.get())

    def _toggle_all_games(self):
        self._set_group(self.launcher_vars, self.var_games_master.get())

    def _preset_feedback(self, text):
        self.action_hint.configure(text=f"✓  {text}", text_color=self.GREEN)

    def _choose_adobe_folder(self):
        folder = filedialog.askdirectory(title="Выберите папку Adobe Cache")
        if folder:
            self.user_folder = folder
            display_name = os.path.basename(folder) or folder
            if len(display_name) > 42:
                display_name = display_name[:39] + "..."
            self.lbl_adobe.configure(text=display_name, text_color=self.CYAN)

    def _build_options(self):
        self._sync_master_vars()
        return {
            "windows": self.var_windows.get(),
            "adobe": self.var_adobe.get(),
            "discord": self.var_discord.get(),
            "create_backup": self.var_backup.get(),
            "adobe_folder": self.user_folder,
            "browsers": {key: value.get() for key, value in self.browser_vars.items()},
            "applications": {key: value.get() for key, value in self.application_vars.items()},
            "recycle_bin": self.var_recycle.get(),
            "launchers": {key: value.get() for key, value in self.launcher_vars.items()},
            "developer_mode": self.var_developer_mode.get(),
            "developer_tools": {key: value.get() for key, value in self.developer_vars.items()},
        }

    def _update_developer_state(self):
        state = "normal" if self.var_developer_mode.get() and not self.is_busy else "disabled"
        for widget in self.developer_widgets:
            try:
                widget.configure(state=state)
            except tk.TclError:
                pass

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
        if self.running_apps_callback:
            try:
                running_apps = self.running_apps_callback(options) or []
            except (OSError, ValueError, TypeError):
                running_apps = []
            if running_apps:
                action = self._ask_running_apps(running_apps)
                if action == "cancel":
                    return
                if action == "close" and self.close_apps_callback:
                    try:
                        failed = self.close_apps_callback(running_apps) or []
                    except (OSError, ValueError, TypeError):
                        failed = [app.get("name", "Приложение") for app in running_apps]
                    if failed:
                        messagebox.showwarning(
                            "Не все приложения закрыты",
                            "Не удалось закрыть: " + ", ".join(failed) +
                            ".\nЗанятые файлы будут безопасно пропущены.",
                            parent=self.root,
                        )
        self._run_background_task(self.cleanup_callback, options, "Подготовка к очистке...")

    def _ask_running_apps(self, apps):
        result = {"action": "cancel"}
        window = ctk.CTkToplevel(self.root, fg_color=self.BG)
        window.title("Открытые приложения")
        window.geometry("620x560")
        window.minsize(560, 480)
        window.transient(self.root)
        window.grab_set()
        window.grid_columnconfigure(0, weight=1)
        window.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(window, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=26, pady=(24, 12))
        ctk.CTkLabel(
            header, text="Некоторые приложения открыты", text_color=self.TEXT,
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
        ).pack(anchor="w")
        ctk.CTkLabel(
            header,
            text="Закройте их, чтобы освободить больше места и уменьшить число пропущенных файлов.",
            wraplength=550, justify="left", text_color=self.MUTED,
            font=ctk.CTkFont(family="Segoe UI", size=11),
        ).pack(anchor="w", pady=(5, 0))

        app_list = ctk.CTkScrollableFrame(
            window, fg_color=self.SURFACE, corner_radius=18,
            border_width=1, border_color=self.BORDER,
        )
        app_list.grid(row=1, column=0, sticky="nsew", padx=24, pady=6)
        app_list.grid_columnconfigure(0, weight=1)
        for row, app in enumerate(apps):
            card = ctk.CTkFrame(app_list, fg_color=self.SURFACE_ALT, corner_radius=13)
            card.grid(row=row, column=0, sticky="ew", padx=5, pady=5)
            card.grid_columnconfigure(1, weight=1)
            ctk.CTkLabel(
                card, text="", image=self._brand_image(app.get("icon", "backup"), 34), width=48,
            ).grid(row=0, column=0, rowspan=2, padx=(12, 5), pady=11)
            ctk.CTkLabel(
                card, text=app.get("name", "Приложение"), text_color=self.TEXT,
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            ).grid(row=0, column=1, sticky="sw", pady=(10, 0))
            process_count = len(app.get("pids", []))
            ctk.CTkLabel(
                card, text=f"Запущено процессов: {process_count}", text_color=self.MUTED,
                font=ctk.CTkFont(family="Segoe UI", size=9),
            ).grid(row=1, column=1, sticky="nw", pady=(2, 10))

        warning = ctk.CTkLabel(
            window,
            text="Перед закрытием сохраните вкладки, сообщения и несохранённые данные.",
            text_color=self.AMBER, font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
        )
        warning.grid(row=2, column=0, sticky="w", padx=28, pady=(8, 2))

        actions = ctk.CTkFrame(window, fg_color="transparent")
        actions.grid(row=3, column=0, sticky="ew", padx=24, pady=(10, 22))
        actions.grid_columnconfigure(0, weight=1)

        def finish(action):
            result["action"] = action
            window.destroy()

        ctk.CTkButton(
            actions, text="Отмена", command=lambda: finish("cancel"), width=92, height=42,
            fg_color="transparent", hover_color=self.SURFACE_RAISED,
            border_width=1, border_color=self.BORDER, corner_radius=12,
        ).grid(row=0, column=1, padx=(8, 0))
        ctk.CTkButton(
            actions, text="Продолжить", command=lambda: finish("continue"), width=120, height=42,
            fg_color=self.SURFACE_RAISED, hover_color="#303030",
            border_width=1, border_color=self.BORDER, corner_radius=12,
        ).grid(row=0, column=2, padx=8)
        ctk.CTkButton(
            actions, text="Закрыть и очистить", command=lambda: finish("close"), width=174, height=44,
            fg_color=self.ACCENT, hover_color=self.ACCENT_HOVER, text_color="#090909",
            corner_radius=12, font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
        ).grid(row=0, column=3)
        window.protocol("WM_DELETE_WINDOW", lambda: finish("cancel"))
        self.root.wait_window(window)
        return result["action"]

    def _on_scan(self):
        options = self._build_options()
        options["create_backup"] = False
        self._run_background_task(self.scan_callback, options, "Анализируем выбранные категории...")

    def _update_progress(self, value: int, status: str):
        if self.root:
            self.root.after(0, self._apply_progress_update, value, status)

    def _apply_progress_update(self, value: int, status: str):
        self.progress.set(max(0, min(value, 100)) / 100)
        self.lbl_status.configure(text=status, text_color=self.TEXT)

    def set_busy(self, busy: bool, status: Optional[str] = None):
        if self.root:
            self.is_busy = busy
            self.root.after(0, self._apply_busy_state, busy, status)

    def _apply_busy_state(self, busy: bool, status: Optional[str]):
        self.is_busy = busy
        state = "disabled" if busy else "normal"
        for widget in self.control_widgets:
            try:
                widget.configure(state=state)
            except (tk.TclError, AttributeError):
                pass
        if not busy:
            self._update_developer_state()
        if status:
            self.lbl_status.configure(text=status, text_color=self.TEXT)
        self.ready_badge.configure(
            text="●  Выполняется" if busy else "●  Система готова",
            text_color=self.AMBER if busy else self.GREEN,
        )

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
            self.root.after(0, self._show_scan_results_window, title, summary, category_totals or {}, total_size)

    def update_dashboard(self, category_totals=None, total_size: int = 0, hint: str = ""):
        if self.root:
            self.root.after(0, self._apply_dashboard_update, category_totals or {}, total_size, hint)

    def _apply_dashboard_update(self, category_totals, total_size, hint):
        self.last_scan_total = total_size
        self.last_scan_categories = category_totals
        self.lbl_metric.configure(text=self._format_size(total_size))
        self.lbl_metric_hint.configure(text=hint or "текущий объём кэша")
        self._draw_donut(category_totals)
        self._render_summary_legend(category_totals)

    def _show_scan_results_window(self, title, summary, category_totals, total_size):
        self._apply_dashboard_update(category_totals, total_size, "можно безопасно освободить")
        self.show_page("overview")
        window = ctk.CTkToplevel(self.root, fg_color=self.BG)
        window.title(title)
        window.geometry("760x520")
        window.minsize(660, 480)
        window.transient(self.root)
        window.grab_set()
        shell = self._glass_card(window)
        shell.pack(fill="both", expand=True, padx=20, pady=20)
        shell.grid_columnconfigure(0, weight=1)
        shell.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(
            shell, text=f"Найдено {self._format_size(total_size)}", text_color=self.TEXT,
            font=ctk.CTkFont(family="Segoe UI", size=23, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=22, pady=(20, 12))
        text_box = ctk.CTkTextbox(
            shell, wrap="word", fg_color=self.SURFACE_ALT, border_width=1,
            border_color=self.BORDER_SOFT, corner_radius=14, text_color=self.TEXT,
            font=ctk.CTkFont(family="Segoe UI", size=12),
        )
        text_box.grid(row=1, column=0, sticky="nsew", padx=20, pady=4)
        text_box.insert("1.0", summary)
        text_box.configure(state="disabled")
        ctk.CTkButton(
            shell, text="Готово", command=window.destroy, width=150, height=42,
            corner_radius=12, fg_color=self.ACCENT, hover_color=self.ACCENT_HOVER,
            text_color="#090909", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
        ).grid(row=2, column=0, sticky="e", padx=20, pady=18)

    def reset_progress(self):
        if self.root:
            self.is_busy = False
            self.root.after(0, self._reset_progress_ui)

    def _reset_progress_ui(self):
        self.progress.set(0)
        self.lbl_status.configure(text="◈  Готово к безопасной очистке", text_color=self.MUTED)
        self._apply_busy_state(False, None)

    def _on_root_configure(self, event):
        if event.widget is self.root:
            self._apply_responsive_layout(event.width)

    def _apply_responsive_layout(self, width: int):
        mode = "compact" if width < 1020 else "desktop"
        if self._layout_mode == mode:
            return
        self._layout_mode = mode
        compact = mode == "compact"
        self.sidebar.configure(width=96 if compact else 238)
        if compact:
            self.brand_title.grid_remove()
            self.brand_subtitle.grid_remove()
            self.sidebar_status_text.pack_forget()
            self.action_hint.grid_remove()
        else:
            self.brand_title.grid()
            self.brand_subtitle.grid()
            if not self.sidebar_status_text.winfo_manager():
                self.sidebar_status_text.pack(side="left", pady=10)
            self.action_hint.grid()
        for name, button in self.nav_buttons.items():
            button.configure(
                text="" if compact else ("Бэкапы" if name == "backups" else self.nav_labels[name]),
                width=52 if compact else 176,
                anchor="center" if compact else "w",
            )

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        if size_bytes >= 1024 ** 3:
            return f"{size_bytes / 1024 ** 3:.2f} GB"
        if size_bytes >= 1024 ** 2:
            return f"{size_bytes / 1024 ** 2:.1f} MB"
        if size_bytes >= 1024:
            return f"{size_bytes / 1024:.1f} KB"
        return f"{size_bytes} B"
