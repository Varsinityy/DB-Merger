import sqlite3
import shutil
import os
import requests
import tempfile
import threading
import math
import time
import json
import sys
import queue
from PIL import Image, ImageTk
from io import BytesIO
import customtkinter as ctk
from tkinter import filedialog, messagebox
from datetime import datetime

def resourcePath(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.normpath(os.path.join(base_path, relative_path))

try:
    from ctypes import windll, c_int, byref, sizeof
except ImportError:
    windll = None

ctk.set_appearance_mode("Dark")

class DraggableMixin:
    def startMove(self, event):
        self.x = event.x
        self.y = event.y

    def doMove(self, event):
        x = self.winfo_x() + (event.x - self.x)
        y = self.winfo_y() + (event.y - self.y)
        self.geometry(f"+{x}+{y}")

COLORS = {
    "bg_primary":       "#09090b",
    "bg_content":       "#040405",
    "bg_secondary":     "#0f0f12",
    "bg_glass":         "#18181b",
    "bg_card":          "#1c1c21",
    "border":           "#27272a",
    "accent_primary":   "#6366f1",
    "accent_secondary": "#8b5cf6",
    "accent_success":   "#10b981",
    "accent_danger":    "#ef4444",
    "accent_warning":   "#f59e0b",
    "text_primary":     "#fafafa",
    "text_secondary":   "#a1a1aa",
    "text_muted":       "#71717a",
}

APP_VERSION = "1.1.0"

class GradientFrame(ctk.CTkCanvas):
    def __init__(self, master, color1, color2, **kwargs):
        super().__init__(master, highlightthickness=0, **kwargs)
        self.color1 = color1
        self.color2 = color2
        self.bind("<Configure>", self.drawGradient)

    def drawGradient(self, event=None):
        self.delete("gradient")
        width = self.winfo_width()
        height = self.winfo_height()
        limit = height
        for i in range(limit):
            nr = int(int(self.color1[1:3], 16) * (limit - i) / limit + int(self.color2[1:3], 16) * i / limit)
            ng = int(int(self.color1[3:5], 16) * (limit - i) / limit + int(self.color2[3:5], 16) * i / limit)
            nb = int(int(self.color1[5:7], 16) * (limit - i) / limit + int(self.color2[5:7], 16) * i / limit)
            color = f"#{nr:02x}{ng:02x}{nb:02x}"
            self.create_line(0, i, width, i, tags=("gradient",), fill=color)
        self.tag_lower("gradient")

class HorizontalGradientFrame(ctk.CTkCanvas):
    def __init__(self, master, color1, color2, **kwargs):
        super().__init__(master, highlightthickness=0, **kwargs)
        self.color1 = color1
        self.color2 = color2
        self.bind("<Configure>", self.drawGradient)

    def drawGradient(self, event=None):
        self.delete("gradient")
        width = self.winfo_width()
        height = self.winfo_height()
        if width <= 1 or height <= 1:
            return
        limit = width
        for i in range(limit):
            nr = int(int(self.color1[1:3], 16) * (limit - i) / limit + int(self.color2[1:3], 16) * i / limit)
            ng = int(int(self.color1[3:5], 16) * (limit - i) / limit + int(self.color2[3:5], 16) * i / limit)
            nb = int(int(self.color1[5:7], 16) * (limit - i) / limit + int(self.color2[5:7], 16) * i / limit)
            color = f"#{nr:02x}{ng:02x}{nb:02x}"
            self.create_line(i, 0, i, height, tags=("gradient",), fill=color)
        self.tag_lower("gradient")

class DropZone(ctk.CTkFrame):
    def __init__(self, master, label_text, app_ref, on_select_callback=None, **kwargs):
        super().__init__(master, **kwargs)
        self.app_ref = app_ref
        self.original_label = label_text
        self.on_select_callback = on_select_callback
        self.configure(
            fg_color=COLORS["bg_secondary"],
            corner_radius=12,
            border_width=2,
            border_color=COLORS["border"]
        )

        self.inner_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.inner_frame.pack(expand=True, fill="both", padx=3, pady=20)

        self.icon_label = ctk.CTkLabel(
            self.inner_frame,
            text="",
            image=self.app_ref.loadIcon("database.png", size=32)
        )
        self.icon_label.pack(pady=(10, 5))

        self.text_label = ctk.CTkLabel(
            self.inner_frame,
            text=label_text,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS["text_secondary"]
        )
        self.text_label.pack(pady=(0, 0))

        self.hint_label = ctk.CTkLabel(
            self.inner_frame,
            text="Click to browse",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_muted"]
        )
        self.hint_label.pack(pady=(2, 5))

        self.path_entry = ctk.CTkEntry(
            self.inner_frame,
            placeholder_text="No file selected...",
            height=40,
            fg_color=COLORS["bg_primary"],
            border_color=COLORS["border"],
            justify="center"
        )
        self.path_entry.pack(fill="x", padx=20, pady=(5, 20))

        for widget in [self, self.inner_frame, self.icon_label, self.text_label, self.hint_label]:
            widget.bind("<Button-1>", self.onClick)

    def onClick(self, event):
        path = filedialog.askopenfilename(
            filetypes=[("Database files", "*.slt"), ("All files", "*.*")]
        )
        if not path:
            return
        self.setPath(path)
        if self.on_select_callback:
            self.on_select_callback(path)

    def setPath(self, path):
        self.path_entry.delete(0, "end")
        self.path_entry.insert(0, path)
        self.configure(border_color=COLORS["accent_success"])
        self.icon_label.configure(image="", text="✅", text_color=COLORS["accent_success"])
        self.text_label.configure(text="File Selected", text_color=COLORS["accent_success"])

    def getPath(self):
        return self.path_entry.get().strip('"')

    def reset(self):
        self.path_entry.delete(0, "end")
        self.icon_label.configure(image=self.app_ref.loadIcon("database.png", size=32), text="")
        self.text_label.configure(text=self.original_label, text_color=COLORS["text_secondary"])
        self.configure(border_color=COLORS["border"])


class DBMerger(DraggableMixin, ctk.CTk):
    def __init__(self):
        if windll:
            try:
                windll.shcore.SetProcessDpiAwareness(1)
            except (AttributeError, OSError):
                pass

        super().__init__()

        self.title("Varsinity's DB Merger")
        self.geometry("900x750")
        self.configure(fg_color=COLORS["bg_primary"])
        self.overrideredirect(True)
        self.image_cache = {}

        self.ui_queue = queue.Queue()
        self.processUiQueue()

        self.update_idletasks()
        self.forceTaskbarPresence()
        self.after(10, self.applyRoundedCorners)

        self.config_file = os.path.join(os.path.expanduser("~"), "varsinity_db_merger.json")
        self.temp_icon_path = os.path.join(tempfile.gettempdir(), "varsinity_dbmerger_icon.ico")

        self.icon_url = "https://codehs.com/uploads/0da061a56c66f4e0b1a43b52f7341515" 
        self.logo_url = "https://codehs.com/uploads/fd81d80c9192d13a66ec9620d278a1ce" 

        if os.path.exists(self.temp_icon_path):
            try:
                self.iconbitmap(self.temp_icon_path)
            except (AttributeError, OSError):
                pass

        self.presets      = {}
        self.game_dbs     = {}
        self.recent_files = []
        self.is_merging   = False
        self.spinner_frame = 0
        self.total_merged  = 0

        self.animations_enabled = True
        self.default_rims_enabled = False

        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)

        self.setupTitlebar()
        self.setupSidebar()

        self.view_container = ctk.CTkFrame(self, fg_color=COLORS["bg_content"], corner_radius=15)
        self.view_container.grid(row=1, column=1, sticky="nsew", padx=25, pady=25)
        self.view_container.grid_columnconfigure(0, weight=1)
        self.view_container.grid_rowconfigure(0, weight=1)

        self.dashboard_page = ctk.CTkScrollableFrame(self.view_container, fg_color=COLORS["bg_primary"])
        self.merger_page  = ctk.CTkScrollableFrame(self.view_container, fg_color=COLORS["bg_primary"])
        self.library_page = ctk.CTkScrollableFrame(self.view_container, fg_color=COLORS["bg_primary"])
        self.backup_page  = ctk.CTkScrollableFrame(self.view_container, fg_color=COLORS["bg_primary"])
        self.settings_page = ctk.CTkScrollableFrame(self.view_container, fg_color=COLORS["bg_primary"])

        self.setupDashboardPage()
        self.setupMergerPage()
        self.setupLibraryPage()
        self.setupBackupPage()
        self.setupSettingsPage()

        self.current_frame = None
        self.loadConfig()
        self.showPage("dashboard")

        self.after(100, self.loadAssetsSafe)
        self.after(3000, self.checkForUpdates)

        self.attributes("-alpha", 0.0)
        self.animateOpen()

    def animateOpen(self, alpha=0.0):
        if alpha < 1.0:
            alpha += 0.1
            self.attributes("-alpha", alpha)
            self.after(10, lambda: self.animateOpen(alpha))

    def animateClose(self, alpha=1.0):
        if alpha > 0:
            alpha -= 0.1
            self.attributes("-alpha", alpha)
            self.after(10, lambda: self.animateClose(alpha))
        else:
            self.destroy()

    def animateMinimize(self, alpha=1.0):
        if alpha > 0:
            alpha -= 0.1
            self.attributes("-alpha", alpha)
            self.after(10, lambda: self.animateMinimize(alpha))
        else:
            if windll:
                hwnd = windll.user32.GetParent(self.winfo_id())
                windll.user32.ShowWindow(hwnd, 6)
            else:
                self.overrideredirect(False)
                self.iconify()
            self.bind("<FocusIn>", self.onRestore)

    def onRestore(self, event):
        self.unbind("<FocusIn>")
        if not windll:
            self.overrideredirect(True)
        self.animateOpen(0.0)

    def applyRoundedCorners(self):
        if windll:
            try:
                HWND = windll.user32.GetParent(self.winfo_id())
                windll.dwmapi.DwmSetWindowAttribute(HWND, 33, byref(c_int(2)), sizeof(c_int(2)))
            except (AttributeError, OSError):
                pass

    def forceTaskbarPresence(self):
        try:
            if not windll:
                return
            myappid = "varsinity.dbmerger.tool"
            windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
            hwnd = windll.user32.GetParent(self.winfo_id())
            style = windll.user32.GetWindowLongW(hwnd, -20)
            style = style & ~0x00000080
            style = style | 0x00040000
            windll.user32.SetWindowLongW(hwnd, -20, style)
            if os.path.exists(self.temp_icon_path):
                self.iconbitmap(self.temp_icon_path)
            self.withdraw()
            self.deiconify()
            self.focus_force()
        except (AttributeError, OSError):
            pass

    def loadAssetsSafe(self):
        try:
            response = requests.get(self.icon_url, timeout=3)
            if response.status_code == 200:
                img_data = response.content
                icon_img = Image.open(BytesIO(img_data))
                icon_img.save(self.temp_icon_path, format="ICO", sizes=[(32, 32), (64, 64)])
                try:
                    self.iconbitmap(self.temp_icon_path)
                except (AttributeError, OSError):
                    pass
                logo_small = ctk.CTkImage(light_image=icon_img, dark_image=icon_img, size=(20, 20))
                if hasattr(self, "title_icon_label"):
                    self.title_icon_label.configure(image=logo_small, text="")
        except (requests.RequestException, OSError, ValueError):
            pass

        try:
            response = requests.get(self.logo_url, timeout=3)
            if response.status_code == 200:
                img_data = response.content
                logo_img = Image.open(BytesIO(img_data))
                target_width = 158
                orig_w, orig_h = logo_img.size
                ratio = orig_h / orig_w
                target_height = int(target_width * ratio)
                logo_image = ctk.CTkImage(light_image=logo_img, dark_image=logo_img, size=(target_width, target_height))
                if hasattr(self, "logo_label"):
                    self.logo_label.configure(image=logo_image, text="")
        except (requests.RequestException, OSError, ValueError):
            pass

    def loadIcon(self, filename, size=20):
        if not hasattr(self, "app_icons"):
            self.app_icons = {}
            
        cache_key = f"{filename}_{size}"
        
        if cache_key in self.app_icons:
            return self.app_icons[cache_key]
            
        path = resourcePath(filename)
        if os.path.exists(path):
            try:
                img = Image.open(path).convert("RGBA")
                r, g, b, a = img.split()
                img = Image.new("RGBA", img.size, "white")
                img.putalpha(a)
                ctk_icon = ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
                self.app_icons[cache_key] = ctk_icon
                return ctk_icon
            except Exception as e:
                print(f"Failed to load icon {filename}: {e}")
        return None

    def setupTitlebar(self):
        self.titlebar = ctk.CTkFrame(self, fg_color=COLORS["bg_secondary"], height=40, corner_radius=0)
        self.titlebar.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.titlebar.grid_propagate(False)
        self.titlebar.bind("<ButtonPress-1>", self.startMove)
        self.titlebar.bind("<B1-Motion>", self.doMove)

        left_frame = ctk.CTkFrame(self.titlebar, fg_color="transparent")
        left_frame.pack(side="left", padx=10, fill="y")
        left_frame.bind("<ButtonPress-1>", self.startMove)
        left_frame.bind("<B1-Motion>", self.doMove)

        self.title_icon_label = ctk.CTkLabel(left_frame, text="🔀", font=ctk.CTkFont(size=16))
        self.title_icon_label.pack(side="left", padx=(5, 5))
        self.title_icon_label.bind("<ButtonPress-1>", self.startMove)
        self.title_icon_label.bind("<B1-Motion>", self.doMove)

        title_label = ctk.CTkLabel(
            left_frame,
            text="Varsinity's DB Merger",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLORS["text_primary"]
        )
        title_label.pack(side="left", padx=5)
        title_label.bind("<ButtonPress-1>", self.startMove)
        title_label.bind("<B1-Motion>", self.doMove)

        close_btn = ctk.CTkButton(
            self.titlebar, text="✕", width=45, height=40,
            fg_color="transparent", hover_color=COLORS["accent_danger"],
            command=self.animateClose, corner_radius=0
        )
        close_btn.pack(side="right")

        min_btn = ctk.CTkButton(
            self.titlebar, text="—", width=45, height=40,
            fg_color="transparent", hover_color=COLORS["bg_card"],
            command=self.animateMinimize, corner_radius=0
        )
        min_btn.pack(side="right")

    def setupSidebar(self):
        self.nav_frame = ctk.CTkFrame(self, corner_radius=0, fg_color=COLORS["bg_secondary"], width=200)
        self.nav_frame.grid(row=1, column=0, sticky="nsew")

        self.sidebar_gradient = GradientFrame(self.nav_frame, color1="#0f0f12", color2="#18181b")
        self.sidebar_gradient.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.tab_indicator = ctk.CTkFrame(self.nav_frame, width=4, height=40, corner_radius=2, fg_color=COLORS["accent_primary"])
        self.tab_gradient  = HorizontalGradientFrame(self.nav_frame, color1=COLORS["accent_primary"], color2=COLORS["bg_primary"])

        self.logo_container = ctk.CTkFrame(self.nav_frame, fg_color="transparent", height=80)
        self.logo_container.pack_propagate(False)
        self.logo_container.pack(fill="x", pady=(20, 10))

        self.logo_label = ctk.CTkLabel(
            self.logo_container,
            text="DB MERGER",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=COLORS["accent_primary"]
        )
        self.logo_label.pack(pady=25, padx=20)

        tab_style = {
            "anchor": "w",
            "height": 48,
            "fg_color": COLORS["bg_primary"],
            "hover_color": COLORS["border"],
            "corner_radius": 8,
            "font": ctk.CTkFont(size=13, weight="bold"),
            "border_width": 1,
            "border_color": COLORS["bg_primary"]
        }

        self.btn_dashboard = ctk.CTkButton(self.nav_frame, text=" Dashboard",      image=self.loadIcon("layout-dashboard.png"), command=lambda: self.showPage("dashboard"), **tab_style)
        self.btn_dashboard.pack(fill="x", padx=15, pady=3)

        self.btn_merger  = ctk.CTkButton(self.nav_frame, text=" Merger",        image=self.loadIcon("package-plus.png"),   command=lambda: self.showPage("merger"),  **tab_style)
        self.btn_merger.pack(fill="x", padx=15, pady=3)

        self.btn_library = ctk.CTkButton(self.nav_frame, text=" Quick Library", image=self.loadIcon("library.png"),           command=lambda: self.showPage("library"), **tab_style)
        self.btn_library.pack(fill="x", padx=15, pady=3)

        self.btn_backup  = ctk.CTkButton(self.nav_frame, text=" Backup History", image=self.loadIcon("history.png"),       command=lambda: self.showPage("backup"),  **tab_style)
        self.btn_backup.pack(fill="x", padx=15, pady=3)

        self.btn_settings = ctk.CTkButton(self.nav_frame, text=" Settings", image=self.loadIcon("settings.png"), command=lambda: self.showPage("settings"), **tab_style)
        self.btn_settings.pack(fill="x", padx=15, pady=3)

        self.footer = ctk.CTkFrame(self.nav_frame, fg_color="#18181b")
        self.footer.pack(side="bottom", fill="x", pady=20, padx=20)

        ver_container = ctk.CTkFrame(self.footer, fg_color="transparent")
        ver_container.pack(fill="x")

        self.status_dot = ctk.CTkLabel(ver_container, text="●", text_color=COLORS["accent_success"], font=ctk.CTkFont(size=14), fg_color="transparent")
        self.status_dot.pack(side="left")

        self.is_online = True
        self.animateStatusDot()

        self.status_text = ctk.CTkLabel(ver_container, text=" ONLINE", font=ctk.CTkFont(size=11, weight="bold"), text_color=COLORS["text_secondary"], fg_color="transparent")
        self.status_text.pack(side="left", padx=2)

        self.ver_label = ctk.CTkLabel(ver_container, text=f"v{APP_VERSION}", font=ctk.CTkFont(size=11), text_color=COLORS["text_muted"], fg_color="transparent")
        self.ver_label.pack(side="right")

        self.btn_update = ctk.CTkButton(
            self.footer,
            text=" Check for Updates",
            image=self.loadIcon("rss.png", size=14),
            font=ctk.CTkFont(size=10, weight="bold"),
            height=26,
            corner_radius=6,
            fg_color=COLORS["bg_primary"],
            hover_color=COLORS["border"],
            border_width=1,
            border_color=COLORS["text_muted"],
            command=lambda: self.checkForUpdates(manual=True)
        )
        self.btn_update.pack(fill="x", pady=(8, 0))

    def showPage(self, page_name):
        if getattr(self, "is_animating", False):
            return

        page_order = ["dashboard", "merger", "library", "backup", "settings"]

        if not hasattr(self, "current_page_name"):
            self.current_page_name = "dashboard"

        current_idx = page_order.index(self.current_page_name)
        target_idx  = page_order.index(page_name)
        direction   = 1 if target_idx >= current_idx else -1

        target_frame = None
        target_btn   = None

        if page_name == "dashboard":
            target_frame = self.dashboard_page
            target_btn   = self.btn_dashboard
            self.after(250, self.refreshDashboard)
        elif page_name == "merger":
            target_frame = self.merger_page
            target_btn   = self.btn_merger
        elif page_name == "library":
            target_frame = self.library_page
            target_btn   = self.btn_library
            self.after(250, self.refreshLibraryUi)
        elif page_name == "backup":
            target_frame = self.backup_page
            target_btn   = self.btn_backup
            self.after(250, self.refreshBackups)
        elif page_name == "settings":
            target_frame = self.settings_page
            target_btn   = self.btn_settings

        if getattr(self, "current_frame", None) == target_frame:
            return

        all_tabs = [
            getattr(self, "btn_dashboard", None), 
            getattr(self, "btn_merger", None), 
            getattr(self, "btn_library", None), 
            getattr(self, "btn_backup", None), 
            getattr(self, "btn_settings", None)
        ]
        
        for btn in all_tabs:
            if btn is not None:
                btn.configure(border_color=COLORS["bg_primary"])
                
        if target_btn:
            target_btn.configure(border_color=COLORS["text_muted"])

        self.is_animating = True
        self.animateIndicator(target_btn)

        if getattr(self, "animations_enabled", True):
            self.animateTransition(getattr(self, "current_frame", None), target_frame, direction)
        else:
            if getattr(self, "current_frame", None):
                self.current_frame.place_forget()
            target_frame.place(relx=0.0, rely=0.0, relwidth=1.0, relheight=1.0)
            self.is_animating = False

        self.current_page_name = page_name
        self.current_frame = target_frame

    def animateIndicator(self, target_widget, start_time=None, start_y=None, target_y=None):
        duration = 0.25
        if start_time is None:
            self.nav_frame.update_idletasks()
            if target_widget.winfo_y() <= 10:
                self.after(20, lambda: self.animateIndicator(target_widget, start_time, start_y, target_y))
                return
            target_y = target_widget.winfo_y() + 4
            if not self.tab_indicator.winfo_ismapped():
                self.tab_indicator.place(x=8, y=target_y)
                return
            start_y    = float(self.tab_indicator.place_info()["y"])
            start_time = time.time()

        elapsed  = time.time() - start_time
        progress = min(elapsed / duration, 1.0)
        ease     = 1 - (1 - progress) ** 3
        current_y = start_y + (target_y - start_y) * ease
        self.tab_indicator.place(x=8, y=current_y)
        if progress < 1.0:
            self.after(5, lambda: self.animateIndicator(target_widget, start_time, start_y, target_y))

    def animateTransition(self, old_frame, new_frame, direction=1, start_time=None):
        duration = 0.25
        if start_time is None:
            new_frame.place(relx=0.0, rely=1.0 * direction, relwidth=1.0, relheight=1.0)
            start_time = time.time()

        elapsed  = time.time() - start_time
        progress = min(elapsed / duration, 1.0)
        ease     = 1 - (1 - progress) ** 3

        if old_frame:
            old_frame.place(rely=-ease * direction)
        new_frame.place(rely=(1.0 - ease) * direction)

        if progress < 1.0:
            self.after(5, lambda: self.animateTransition(old_frame, new_frame, direction, start_time))
        else:
            if old_frame:
                old_frame.place_forget()
            new_frame.place(relx=0.0, rely=0.0, relwidth=1.0, relheight=1.0)
            self.is_animating = False

    def setupDashboardPage(self):
        header = ctk.CTkLabel(
            self.dashboard_page,
            text="Welcome back! ",
            image=self.loadIcon("hello.png", size=32),
            compound="right",
            font=ctk.CTkFont(family="Ubuntu", size=32, weight="bold"),
            text_color=COLORS["text_primary"]
        )
        header.pack(anchor="w", pady=(0, 20))

        stats_frame = ctk.CTkFrame(self.dashboard_page, fg_color="transparent")
        stats_frame.pack(fill="x", pady=(0, 20))
        stats_frame.grid_columnconfigure(0, weight=1)
        stats_frame.grid_columnconfigure(1, weight=1)

        stat_card = ctk.CTkFrame(stats_frame, fg_color=COLORS["bg_secondary"], corner_radius=12, border_width=1, border_color=COLORS["border"])
        stat_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        stat_inner = ctk.CTkFrame(stat_card, fg_color="transparent")
        stat_inner.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(stat_inner, text="Session Stats", font=ctk.CTkFont(weight="bold"), text_color=COLORS["text_secondary"]).pack(anchor="w", pady=(0, 10))

        sg = ctk.CTkFrame(stat_inner, fg_color="transparent")
        sg.pack(fill="x")
        sg.columnconfigure(1, weight=1)

        ctk.CTkLabel(sg, text="Saved Configs:", font=ctk.CTkFont(size=13)).grid(row=0, column=0, sticky="w", pady=2)
        self.dash_configs_label = ctk.CTkLabel(sg, text="0", font=ctk.CTkFont(size=13, weight="bold"), text_color=COLORS["accent_primary"])
        self.dash_configs_label.grid(row=0, column=1, sticky="e", pady=2)

        ctk.CTkLabel(sg, text="Favorite Files:", font=ctk.CTkFont(size=13)).grid(row=1, column=0, sticky="w", pady=2)
        self.dash_favs_label = ctk.CTkLabel(sg, text="0", font=ctk.CTkFont(size=13, weight="bold"), text_color=COLORS["accent_primary"])
        self.dash_favs_label.grid(row=1, column=1, sticky="e", pady=2)

        ctk.CTkLabel(sg, text="Total Merges Run:", font=ctk.CTkFont(size=13)).grid(row=2, column=0, sticky="w", pady=2)
        self.dash_merges_label = ctk.CTkLabel(sg, text="0", font=ctk.CTkFont(size=13, weight="bold"), text_color=COLORS["accent_primary"])
        self.dash_merges_label.grid(row=2, column=1, sticky="e", pady=2)

        health_card = ctk.CTkFrame(stats_frame, fg_color=COLORS["bg_secondary"], corner_radius=12, border_width=1, border_color=COLORS["border"])
        health_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        health_inner = ctk.CTkFrame(health_card, fg_color="transparent")
        health_inner.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(health_inner, text="Active Databases", font=ctk.CTkFont(weight="bold"), text_color=COLORS["text_secondary"]).pack(anchor="w", pady=(0, 10))

        hg = ctk.CTkFrame(health_inner, fg_color="transparent")
        hg.pack(fill="x")
        hg.columnconfigure(1, weight=1)

        ctk.CTkLabel(hg, text="Target:", font=ctk.CTkFont(size=13)).grid(row=0, column=0, sticky="w", pady=2)
        self.dash_target_label = ctk.CTkLabel(hg, text="None", font=ctk.CTkFont(size=13, weight="bold"), text_color=COLORS["text_muted"])
        self.dash_target_label.grid(row=0, column=1, sticky="e", pady=2)

        ctk.CTkLabel(hg, text="Source:", font=ctk.CTkFont(size=13)).grid(row=1, column=0, sticky="w", pady=2)
        self.dash_source_label = ctk.CTkLabel(hg, text="None", font=ctk.CTkFont(size=13, weight="bold"), text_color=COLORS["text_muted"])
        self.dash_source_label.grid(row=1, column=1, sticky="e", pady=2)

        ctk.CTkLabel(hg, text="Last Backup:", font=ctk.CTkFont(size=13)).grid(row=2, column=0, sticky="w", pady=2)
        self.dash_backup_label = ctk.CTkLabel(hg, text="—", font=ctk.CTkFont(size=13, weight="bold"), text_color=COLORS["text_muted"])
        self.dash_backup_label.grid(row=2, column=1, sticky="e", pady=2)

        guide_frame = ctk.CTkFrame(self.dashboard_page, fg_color="transparent")
        guide_frame.pack(fill="x", pady=(10, 20))

        ctk.CTkLabel(guide_frame, text="Getting Started", font=ctk.CTkFont(size=18, weight="bold"), text_color=COLORS["text_primary"]).pack(anchor="w", pady=(0, 10))

        guide_text = (
            "1. Go to 'Merger' and drop your Target (.slt) and Source (mod) databases into the drop zones.\n"
            "2. Choose whether to include Rim/Tire data, then hit EXECUTE DATABASE MERGE.\n"
            "3. A backup is automatically created before every merge, restore anytime from 'Backup History'.\n"
            "4. Save frequent merge pairs as configs in 'Quick Library' for easy reuse."
        )
        ctk.CTkLabel(guide_frame, text=guide_text, font=ctk.CTkFont(size=13), text_color=COLORS["text_secondary"], justify="left").pack(anchor="w", padx=(10, 0))

        ctk.CTkLabel(self.dashboard_page, text="Quick Actions", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w", pady=(10, 10))

        actions_frame = ctk.CTkFrame(self.dashboard_page, fg_color="transparent")
        actions_frame.pack(fill="x", pady=(0, 20))

        ctk.CTkButton(
            actions_frame,
            text=" Go to Merger",
            image=self.loadIcon("package-plus.png", size=18),
            height=48,
            fg_color=COLORS["accent_primary"],
            font=ctk.CTkFont(size=13, weight="bold"),
            command=lambda: self.showPage("merger")
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            actions_frame,
            text=" Open Library",
            image=self.loadIcon("library.png", size=18),
            height=48,
            fg_color=COLORS["bg_card"],
            hover_color=COLORS["accent_secondary"],
            font=ctk.CTkFont(size=13, weight="bold"),
            command=lambda: self.showPage("library")
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            actions_frame,
            text=" Backup History",
            image=self.loadIcon("history.png", size=18),
            height=48,
            fg_color=COLORS["bg_card"],
            hover_color=COLORS["accent_secondary"],
            font=ctk.CTkFont(size=13, weight="bold"),
            command=lambda: self.showPage("backup")
        ).pack(side="left")

        ctk.CTkLabel(
            self.dashboard_page,
            text=f"Recent Additions (v{APP_VERSION})",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(anchor="w", pady=(10, 10))

        changelog_frame = ctk.CTkFrame(self.dashboard_page, fg_color=COLORS["bg_secondary"], corner_radius=12, border_width=1, border_color=COLORS["border"])
        changelog_frame.pack(fill="x", pady=(0, 10))
        changelog_frame.grid_columnconfigure(1, weight=1)

        changes = [
            ("Revamped UI",            "Completely overhauled UI to match the Plate Compiler."),
            ("New Dashboard Page",     "Added the dashboard with session stats, active database info, quick actions, and a getting started guide."),
            ("New Settings Page",      "Added a settings page."),
            ("Auto Updater",           "Added a full auto update function, checks GitHub releases and installs the latest update."),
            ("Animated Transitions",   "Page switches now use the same (buggy) animation as the Plate Compiler, though it is toggleable in the settings."),
        ]

        for idx, (title, desc) in enumerate(changes):
            ctk.CTkLabel(changelog_frame, text=f"• {title}:", font=ctk.CTkFont(size=13, weight="bold"), text_color=COLORS["accent_primary"]).grid(row=idx, column=0, sticky="nw", padx=(15, 10), pady=8)
            ctk.CTkLabel(changelog_frame, text=desc, font=ctk.CTkFont(size=13), text_color=COLORS["text_secondary"], justify="left", wraplength=370).grid(row=idx, column=1, sticky="nw", padx=(0, 15), pady=8)

        ctk.CTkLabel(self.dashboard_page, text="Recent Files", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w", pady=(20, 10))
        self.dash_recent_list = ctk.CTkFrame(self.dashboard_page, fg_color="transparent")
        self.dash_recent_list.pack(fill="both", expand=True)

    def refreshDashboard(self):
        self.dash_configs_label.configure(text=str(len(self.presets)))
        self.dash_favs_label.configure(text=str(len(self.game_dbs)))
        self.dash_merges_label.configure(text=str(self.total_merged))

        master = self.master_drop_zone.getPath() if hasattr(self, "master_drop_zone") else ""
        source = self.source_drop_zone.getPath() if hasattr(self, "source_drop_zone") else ""

        self.dash_target_label.configure(
            text=os.path.basename(master) if master else "None",
            text_color=COLORS["accent_success"] if master else COLORS["text_muted"]
        )
        self.dash_source_label.configure(
            text=os.path.basename(source) if source else "None",
            text_color=COLORS["accent_success"] if source else COLORS["text_muted"]
        )

        last_bak = "—"
        if master and os.path.isfile(master):
            directory = os.path.dirname(master)
            base_name = os.path.basename(master)
            backups = sorted(
                [f for f in os.listdir(directory) if f.startswith(base_name) and f.endswith(".bak")],
                reverse=True
            )
            if backups:
                last_bak = backups[0]

        self.dash_backup_label.configure(
            text=last_bak if last_bak != "—" else "—",
            text_color=COLORS["accent_success"] if last_bak != "—" else COLORS["text_muted"]
        )

        for widget in self.dash_recent_list.winfo_children():
            widget.destroy()

        recent = self.recent_files[:5]
        if not recent:
            ctk.CTkLabel(self.dash_recent_list, text="No recent files yet.", text_color=COLORS["text_muted"]).pack(anchor="w", pady=10)
            return

        for path in recent:
            card = ctk.CTkFrame(self.dash_recent_list, fg_color=COLORS["bg_secondary"], corner_radius=8)
            card.pack(fill="x", pady=5, ipadx=15, ipady=10)

            exists = os.path.isfile(path)
            icon = "✅" if exists else "❌"
            color = COLORS["text_secondary"] if exists else COLORS["text_muted"]

            ctk.CTkLabel(card, text=icon, font=ctk.CTkFont(size=14)).pack(side="left", padx=(10, 0))
            ctk.CTkLabel(card, text=os.path.basename(path), text_color=color).pack(side="left", padx=10)
            ctk.CTkLabel(card, text=path, font=ctk.CTkFont(size=10), text_color=COLORS["text_muted"]).pack(side="left")

            if exists:
                ctk.CTkButton(
                    card,
                    text="Load as Target",
                    width=100,
                    height=28,
                    fg_color=COLORS["bg_card"],
                    hover_color=COLORS["accent_primary"],
                    font=ctk.CTkFont(size=11),
                    command=lambda p=path: [self.master_drop_zone.setPath(p), self.onMasterSelected(p), self.showPage("merger")]
                ).pack(side="right", padx=10)

    def checkForUpdates(self, manual=False):
        def SetStatus(online):
            self.is_online = online
            if hasattr(self, "status_text"):
                self.status_text.configure(text=" ONLINE" if online else " OFFLINE")

        def Task():
            try:
                import re
                import webbrowser

                api_url = "https://api.github.com/repos/Varsinityy/DB-Merger/releases/latest"
                response = requests.get(api_url, timeout=5)

                if response.status_code == 200:
                    self.after(0, lambda: SetStatus(True))
                    data = response.json()
                    latest_tag = data.get("tag_name", f"v{APP_VERSION}")

                    latest_nums  = [int(n) for n in re.findall(r'\d+', latest_tag)]
                    current_nums = [int(n) for n in re.findall(r'\d+', APP_VERSION)]

                    while len(latest_nums)  < 3: latest_nums.append(0)
                    while len(current_nums) < 3: current_nums.append(0)

                    latest_tuple  = tuple(latest_nums[:3])
                    current_tuple = tuple(current_nums[:3])

                    if latest_tuple > current_tuple:
                        def promptUpdate():
                            from PIL import ImageGrab, ImageFilter, ImageEnhance

                            x, y = self.winfo_rootx(), self.winfo_rooty()
                            w, h = self.winfo_width(), self.winfo_height()

                            try:
                                screen   = ImageGrab.grab(bbox=(x, y, x + w, y + h))
                                blurred  = screen.filter(ImageFilter.GaussianBlur(radius=6))
                                darkened = ImageEnhance.Brightness(blurred).enhance(0.6)
                                self.overlay_bg = ctk.CTkImage(light_image=darkened, dark_image=darkened, size=(w, h))
                            except Exception:
                                self.overlay_bg = None

                            overlay = ctk.CTkToplevel(self)
                            overlay.overrideredirect(True)
                            overlay.geometry(f"{w}x{h}+{x}+{y}")
                            overlay.transient(self)

                            if getattr(self, "overlay_bg", None):
                                bg_label = ctk.CTkLabel(overlay, image=self.overlay_bg, text="")
                                bg_label.pack(fill="both", expand=True)
                            else:
                                overlay.attributes("-alpha", 0.7)
                                overlay.configure(fg_color="#000000")

                            dialog = ctk.CTkToplevel(self)
                            dialog.overrideredirect(True)
                            dialog.configure(fg_color=COLORS["border"])

                            dw, dh = 420, 250
                            dx = x + (w // 2) - (dw // 2)
                            dy = y + (h // 2) - (dh // 2)
                            dialog.geometry(f"{dw}x{dh}+{dx}+{dy}")
                            dialog.transient(self)
                            dialog.grab_set()
                            dialog.focus_force()

                            if windll:
                                try:
                                    dialog.update()
                                    HWND = windll.user32.GetParent(dialog.winfo_id())
                                    windll.dwmapi.DwmSetWindowAttribute(HWND, 33, byref(c_int(2)), sizeof(c_int(2)))
                                except (AttributeError, OSError):
                                    pass

                            container = ctk.CTkFrame(dialog, fg_color=COLORS["bg_secondary"], corner_radius=0, border_width=0)
                            container.pack(fill="both", expand=True, padx=2, pady=2)

                            ctk.CTkLabel(container, text="✨ Update Available", font=ctk.CTkFont(size=24, weight="bold"), text_color=COLORS["text_primary"]).pack(pady=(30, 5))

                            badge = ctk.CTkFrame(container, fg_color=COLORS["accent_primary"], corner_radius=6)
                            badge.pack(pady=(0, 15))
                            ctk.CTkLabel(badge, text=f"Version {latest_tag}", font=ctk.CTkFont(size=12, weight="bold"), text_color="#ffffff").pack(padx=10, pady=2)

                            ctk.CTkLabel(container, text="Would you like to install it now?\nThe app will restart automatically.", font=ctk.CTkFont(size=14), text_color=COLORS["text_secondary"], justify="center").pack(pady=(0, 25))

                            btn_frame = ctk.CTkFrame(container, fg_color="transparent")
                            btn_frame.pack(fill="x", pady=(0, 20))

                            def onYes():
                                dialog.destroy()
                                overlay.destroy()
                                exe_url = None
                                for asset in data.get("assets", []):
                                    if asset.get("name", "").endswith(".exe"):
                                        exe_url = asset.get("browser_download_url")
                                        break
                                if exe_url:
                                    threading.Thread(target=self.executeAutoUpdate, args=(exe_url,), daemon=True).start()
                                else:
                                    messagebox.showerror("Error", "Could not find the .exe in the latest release.")

                            def onNo():
                                dialog.destroy()
                                overlay.destroy()

                            ctk.CTkButton(btn_frame, text="Not Now",       width=120, fg_color=COLORS["bg_card"],       hover_color=COLORS["border"],        command=onNo).pack(side="left",  expand=True, padx=(20, 10))
                            ctk.CTkButton(btn_frame, text="Install Update", width=120, fg_color=COLORS["accent_success"], hover_color="#059669",              command=onYes).pack(side="right", expand=True, padx=(10, 20))

                        self.after(0, promptUpdate)

                    elif manual:
                        self.after(0, lambda: messagebox.showinfo("Up to Date", "You are running the latest version."))
                else:
                    self.after(0, lambda: SetStatus(False))
                    if manual:
                        self.after(0, lambda: messagebox.showerror("Update Error", "Could not connect to GitHub."))
            except Exception as e:
                self.after(0, lambda: SetStatus(False))
                if manual:
                    self.after(0, lambda err=e: messagebox.showerror("Update Error", f"An error occurred: {err}"))

        threading.Thread(target=Task, daemon=True).start()

    def executeAutoUpdate(self, download_url):
        try:
            self.after(0, lambda: self.btn_update.configure(text="Preparing...", state="disabled"))

            if not getattr(sys, "frozen", False):
                self.after(0, lambda: messagebox.showinfo("Notice", "Auto-update only works when running the compiled .exe file."))
                self.after(0, lambda: self.btn_update.configure(text=" Check for Updates", state="normal"))
                return

            import subprocess

            current_exe = sys.executable
            base_dir    = os.path.dirname(current_exe)

            old_exe_name = f"DBMerger_old_{int(time.time())}.exe"
            old_exe      = os.path.join(base_dir, old_exe_name)
            new_exe      = os.path.join(base_dir, "DBMerger.exe")

            os.rename(current_exe, old_exe)

            self.after(0, lambda: self.btn_update.configure(text="Downloading 0%..."))

            response   = requests.get(download_url, stream=True, timeout=30)
            response.raise_for_status()

            total_size = int(response.headers.get("content-length", 0))
            downloaded = 0
            last_pct   = -1

            with open(new_exe, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            pct = int((downloaded / total_size) * 100)
                            if pct != last_pct and pct % 5 == 0:
                                self.after(0, lambda p=pct: self.btn_update.configure(text=f"Downloading {p}%..."))
                                last_pct = pct

            self.after(0, lambda: self.btn_update.configure(text="Installing..."))

            bat_path    = os.path.join(base_dir, "update_cleanup.bat")
            bat_content = (
                f"@echo off\n"
                f"timeout /t 3 /nobreak > NUL\n"
                f"del \"{old_exe_name}\"\n"
                f"explorer.exe \"{new_exe}\"\n"
                f"del \"%~f0\"\n"
            )
            with open(bat_path, "w") as f:
                f.write(bat_content)

            CREATE_NO_WINDOW = 0x08000000
            import subprocess
            subprocess.Popen(["cmd.exe", "/c", "update_cleanup.bat"], cwd=base_dir, creationflags=CREATE_NO_WINDOW)

            os._exit(0)

        except Exception as e:
            try:
                if "old_exe" in locals() and "current_exe" in locals():
                    if os.path.exists(old_exe) and not os.path.exists(current_exe):
                        os.rename(old_exe, current_exe)
            except Exception:
                pass
            self.after(0, lambda err=e: messagebox.showerror("Update Error", f"Failed to update:\n{err}"))
            self.after(0, lambda: self.btn_update.configure(text=" Check for Updates", state="normal"))

    def setupMergerPage(self):
        header = ctk.CTkLabel(
            self.merger_page,
            text="Database Merger",
            font=ctk.CTkFont(family="Ubuntu", size=32, weight="bold"),
            text_color=COLORS["text_primary"]
        )
        header.pack(anchor="w", pady=(0, 5))

        subtitle = ctk.CTkLabel(
            self.merger_page,
            text="Merge mod databases into your game database with automatic backup and conflict resolution.",
            font=ctk.CTkFont(size=13),
            text_color=COLORS["text_secondary"],
            wraplength=600,
            justify="left"
        )
        subtitle.pack(anchor="w", pady=(0, 20))

        drop_container = ctk.CTkFrame(self.merger_page, fg_color="transparent")
        drop_container.pack(fill="x", pady=(0, 15))
        drop_container.grid_columnconfigure(0, weight=1)
        drop_container.grid_columnconfigure(1, weight=1)

        self.master_drop_zone = DropZone(
            drop_container,
            "Target Database (.slt)",
            app_ref=self,
            on_select_callback=self.onMasterSelected
        )
        self.master_drop_zone.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=5)

        self.source_drop_zone = DropZone(
            drop_container,
            "Source / Mod Database (.slt)",
            app_ref=self,
            on_select_callback=self.onSourceSelected
        )
        self.source_drop_zone.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=5)

        options_frame = ctk.CTkFrame(
            self.merger_page,
            fg_color=COLORS["bg_secondary"],
            corner_radius=12,
            border_width=1,
            border_color=COLORS["border"]
        )
        options_frame.pack(fill="x", pady=(0, 15), ipadx=20, ipady=15)

        ctk.CTkLabel(
            options_frame,
            text="Merge Options",
            font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", padx=20, pady=(10, 5))

        options_inner = ctk.CTkFrame(options_frame, fg_color="transparent")
        options_inner.pack(fill="x", padx=20, pady=(0, 10))

        self.rims_var = ctk.BooleanVar(value=False)
        self.cb_rims = ctk.CTkCheckBox(
            options_inner,
            text="Include Rims and Tire Data",
            variable=self.rims_var,
            border_color=COLORS["accent_primary"],
            fg_color=COLORS["accent_primary"],
            hover_color=COLORS["accent_secondary"],
            font=ctk.CTkFont(size=13),
            text_color=COLORS["text_primary"]
        )
        self.cb_rims.pack(side="left")

        self.btn_why = ctk.CTkButton(
            options_inner,
            text="Why?",
            image=self.loadIcon("circle-question-mark.png", size=14),
            width=70,
            height=28,
            font=ctk.CTkFont(size=11),
            fg_color="transparent",
            text_color=COLORS["text_muted"],
            hover_color=COLORS["bg_card"],
            command=lambda: messagebox.showinfo(
                "Rims & Tires Info",
                "Keep this unchecked if your original database uses a different sorting for rims and tires.\n\nEnabling this includes wheel and tire table data in the merge. (Not Recommended)"
            )
        )
        self.btn_why.pack(side="left", padx=15)

        self.btn_save_preset = ctk.CTkButton(
            options_inner,
            text=" Save Config",
            image=self.loadIcon("save.png", size=16),
            width=140,
            height=32,
            fg_color=COLORS["bg_card"],
            hover_color=COLORS["accent_secondary"],
            font=ctk.CTkFont(size=12),
            command=self.saveCurrentAsPreset
        )
        self.btn_save_preset.pack(side="right")

        self.progress_frame = ctk.CTkFrame(
            self.merger_page,
            fg_color=COLORS["bg_secondary"],
            corner_radius=12,
            border_width=1,
            border_color=COLORS["border"]
        )
        self.progress_frame.pack(fill="x", pady=(0, 15))

        status_inner = ctk.CTkFrame(self.progress_frame, fg_color="transparent")
        status_inner.pack(fill="x", padx=20, pady=(15, 10))

        self.prog_status_icon = ctk.CTkLabel(status_inner, text="⏳", font=ctk.CTkFont(size=20))
        self.prog_status_icon.pack(side="left")

        self.prog_status_text = ctk.CTkLabel(
            status_inner,
            text="Ready to merge",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLORS["text_primary"]
        )
        self.prog_status_text.pack(side="left", padx=10)

        self.progress_bar = ctk.CTkProgressBar(
            self.progress_frame, height=8, corner_radius=4,
            fg_color=COLORS["bg_card"],
            progress_color=COLORS["accent_primary"]
        )
        self.progress_bar.pack(fill="x", padx=20, pady=5)
        self.progress_bar.set(0)

        self.progress_pct_label = ctk.CTkLabel(
            self.progress_frame,
            text="0% Complete",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_muted"]
        )
        self.progress_pct_label.pack(pady=(0, 15))

        self.btn_merge = ctk.CTkButton(
            self.merger_page,
            text=" EXECUTE DATABASE MERGE",
            image=self.loadIcon("package-plus.png", size=24),
            fg_color=COLORS["accent_primary"],
            height=60,
            width=0,
            font=ctk.CTkFont(size=16, weight="bold"),
            command=self.runMerge
        )
        self.btn_merge.pack(fill="x", pady=20)

        log_header = ctk.CTkFrame(self.merger_page, fg_color="transparent")
        log_header.pack(fill="x")
        ctk.CTkLabel(
            log_header,
            text="OPERATION LOG",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLORS["text_muted"]
        ).pack(anchor="w", pady=(0, 8))

        self.log_area = ctk.CTkTextbox(
            self.merger_page,
            fg_color=COLORS["bg_secondary"],
            text_color=COLORS["accent_secondary"],
            font=("Consolas", 12),
            height=150
        )
        self.log_area.pack(fill="both", expand=True)

    def onMasterSelected(self, path):
        self.addToRecentFiles(path)
        self.saveConfig(silent=True)
        self.log(f"✓ Target database loaded: {os.path.basename(path)}")

    def onSourceSelected(self, path):
        self.addToRecentFiles(path)
        self.log(f"✓ Source database loaded: {os.path.basename(path)}")

    def runMerge(self):
        master = self.master_drop_zone.getPath()
        source = self.source_drop_zone.getPath()

        if not os.path.isfile(master) or not os.path.isfile(source):
            messagebox.showerror("Error", "Please select valid database files for both Target and Source.")
            return

        self.is_merging = True
        self.spinner_frame = 0
        self.animateMergeButton()
        threading.Thread(target=self.executeMerge, args=(master, source), daemon=True).start()

    def executeMerge(self, master, source):
        def setProgress(val, text=""):
            self.after(0, lambda: self.updateProgress(val, text))

        def setStatus(icon, text, color=None):
            self.after(0, lambda: self.updateStatus(icon, text, color or COLORS["text_primary"]))

        try:
            for label, path in [("Target", master), ("Source", source)]:
                with open(path, "rb") as f:
                    header = f.read(16)
                if not header:
                    raise ValueError(f"The {label} file is empty (0 bytes).")
                if header != b"SQLite format 3\x00":
                    if b"BURGM" in header:
                        raise ValueError(f"The {label} file appears to be a compressed Game Archive, not a Database.")
                    raise ValueError(f"The {label} file is not a valid SQLite database.\n\nIt may be encrypted or corrupted.")

            setProgress(0.1, "Creating backup...")
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{master}_{timestamp_str}.bak"
            shutil.copy2(master, backup_path)
            self.log(f"✓ Backup created: {os.path.basename(backup_path)}")

            setProgress(0.2, "Connecting to databases...")
            conn   = sqlite3.connect(master)
            cursor = conn.cursor()

            source_escaped = source.replace("'", "''")
            try:
                cursor.execute(f"ATTACH DATABASE '{source_escaped}' AS mod_db")
            except sqlite3.DatabaseError as e:
                if "file is not a database" in str(e).lower():
                    raise ValueError("SQLite cannot read the Source file.\n\nIt may be encrypted or corrupted.")
                raise e

            self.log("✓ Databases connected and validated")

            cursor.execute("SELECT name FROM mod_db.sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]

            if not tables:
                raise ValueError("Source database contains no tables to merge.")

            total_tables = len(tables)
            self.log(f"✓ Processing {total_tables} tables...")

            count = 0
            for i, table in enumerate(tables):
                if table.startswith("sqlite_"):
                    continue
                if not self.rims_var.get() and ("Wheel" in table or "Tire" in table):
                    continue
                progress = 0.3 + (0.6 * (i + 1) / total_tables)
                setProgress(progress, f"Merging: {table}")
                cursor.execute(f"INSERT OR REPLACE INTO main.{table} SELECT * FROM mod_db.{table}")
                count += 1

            conn.commit()
            conn.close()

            setProgress(1.0, "Complete!")
            setStatus("✅", f"Success! {count} tables merged", COLORS["accent_success"])
            self.log(f"✓ SUCCESS: {count} tables synced")
            self.total_merged += 1
            self.saveConfig(silent=True)
            self.after(0, lambda: messagebox.showinfo("Success", f"Merge Complete!\n{count} tables processed successfully."))

        except ValueError as ve:
            setStatus("❌", "Validation Failed", COLORS["accent_danger"])
            self.log(f"✗ VALIDATION ERROR: {str(ve)}")
            self.after(0, lambda: messagebox.showerror("Validation Error", str(ve)))
        except Exception as e:
            setStatus("❌", "System Error", COLORS["accent_danger"])
            self.log(f"✗ SYSTEM ERROR: {str(e)}")
            self.after(0, lambda: messagebox.showerror("Merge Failed", f"A system error occurred:\n{str(e)}"))
        finally:
            self.is_merging = False
            self.after(250, self.refreshBackups)

    def updateProgress(self, value, text=""):
        self.progress_bar.set(value)
        self.progress_pct_label.configure(
            text=f"{int(value * 100)}% Complete" + (f" — {text}" if text else "")
        )

    def updateStatus(self, icon, text, color):
        self.prog_status_icon.configure(text=icon)
        self.prog_status_text.configure(text=text, text_color=color)

    def animateMergeButton(self):
        if not self.is_merging:
            self.btn_merge.configure(
                text=" EXECUTE DATABASE MERGE",
                image=self.loadIcon("package-plus.png", size=24),
                state="normal"
            )
            return
        frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.btn_merge.configure(
            text=f"{frames[self.spinner_frame % len(frames)]} MERGING... (Please wait)",
            state="disabled"
        )
        self.spinner_frame += 1
        self.after(100, self.animateMergeButton)

    def setupLibraryPage(self):
        header = ctk.CTkLabel(
            self.library_page,
            text="Quick Merge Library",
            font=ctk.CTkFont(family="Ubuntu", size=32, weight="bold"),
            text_color=COLORS["text_primary"]
        )
        header.pack(anchor="w", pady=(0, 5))

        ctk.CTkLabel(
            self.library_page,
            text="Manage saved merge configurations and favorite database files for one-click merging.",
            font=ctk.CTkFont(size=13),
            text_color=COLORS["text_secondary"],
            wraplength=600,
            justify="left"
        ).pack(anchor="w", pady=(0, 20))

        btn_row = ctk.CTkFrame(self.library_page, fg_color="transparent")
        btn_row.pack(fill="x", pady=(0, 15))

        ctk.CTkButton(
            btn_row,
            text=" Add Favorite File",
            image=self.loadIcon("star.png", size=16),
            height=40,
            fg_color=COLORS["bg_card"],
            hover_color=COLORS["accent_secondary"],
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.addGameDbManual
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            btn_row,
            text=" Save Current Config",
            image=self.loadIcon("save.png", size=16),
            height=40,
            fg_color=COLORS["accent_primary"],
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.saveCurrentAsPreset
        ).pack(side="left")

        self.library_list = ctk.CTkFrame(self.library_page, fg_color="transparent")
        self.library_list.pack(fill="both", expand=True)

        self.empty_state = ctk.CTkFrame(
            self.library_list,
            fg_color=COLORS["bg_secondary"],
            corner_radius=12,
            border_width=1,
            border_color=COLORS["border"]
        )
        empty_inner = ctk.CTkFrame(self.empty_state, fg_color="transparent")
        empty_inner.pack(expand=True, pady=40)
        
        ctk.CTkLabel(
            empty_inner, 
            text="", 
            image=self.loadIcon("libraryhigh.png", size=72)
        ).pack()
        
        ctk.CTkLabel(
            empty_inner,
            text="Library is empty",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLORS["text_secondary"]
        ).pack(pady=(10, 5))
        
        ctk.CTkLabel(
            empty_inner,
            text="Save a merge config or add a favorite file to get started.",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_muted"]
        ).pack()

    def refreshLibraryUi(self):
        for widget in self.library_list.winfo_children():
            if widget != self.empty_state:
                widget.destroy()

        count = 0

        if self.presets:
            ctk.CTkLabel(
                self.library_list,
                text="MERGE CONFIGURATIONS",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=COLORS["text_muted"]
            ).pack(anchor="w", pady=(10, 5))

            for name, data in self.presets.items():
                count += 1
                card = ctk.CTkFrame(
                    self.library_list,
                    fg_color=COLORS["bg_secondary"],
                    corner_radius=12,
                    border_width=1,
                    border_color=COLORS["border"]
                )
                card.pack(fill="x", pady=5)

                content = ctk.CTkFrame(card, fg_color="transparent")
                content.pack(fill="x", padx=15, pady=12)

                icon_box = ctk.CTkFrame(content, fg_color=COLORS["accent_primary"], corner_radius=8, width=40, height=40)
                icon_box.pack(side="left", padx=(0, 12))
                icon_box.pack_propagate(False)
                ctk.CTkLabel(icon_box, text="⚡", font=ctk.CTkFont(size=20), text_color="white").place(relx=0.5, rely=0.5, anchor="center")

                text_frame = ctk.CTkFrame(content, fg_color="transparent")
                text_frame.pack(side="left", fill="x", expand=True)
                ctk.CTkLabel(text_frame, text=name, font=ctk.CTkFont(size=14, weight="bold"), text_color=COLORS["text_primary"], anchor="w").pack(anchor="w")
                master_name = os.path.basename(data.get("master", "Unknown"))
                source_name = os.path.basename(data.get("source", "Unknown"))
                ctk.CTkLabel(text_frame, text=f"Target: {master_name}  |  Source: {source_name}", font=ctk.CTkFont(size=11), text_color=COLORS["text_muted"], anchor="w").pack(anchor="w")

                btn_frame = ctk.CTkFrame(content, fg_color="transparent")
                btn_frame.pack(side="right")
                ctk.CTkButton(btn_frame, text="Load & Run", width=90, height=32, fg_color=COLORS["accent_success"], hover_color="#059669", font=ctk.CTkFont(size=12, weight="bold"), command=lambda n=name, d=data: self.runPreset(n, d)).pack(side="left", padx=5)
                ctk.CTkButton(btn_frame, text="✕", width=32, height=32, fg_color=COLORS["bg_card"], hover_color=COLORS["accent_danger"], command=lambda n=name: self.deletePreset(n)).pack(side="left")

        if self.game_dbs:
            ctk.CTkLabel(
                self.library_list,
                text="FAVORITE FILES",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=COLORS["text_muted"]
            ).pack(anchor="w", pady=(15, 5))

            for name, data in self.game_dbs.items():
                count += 1
                db_path = data.get("path", "")
                card = ctk.CTkFrame(
                    self.library_list,
                    fg_color=COLORS["bg_secondary"],
                    corner_radius=12,
                    border_width=1,
                    border_color=COLORS["border"]
                )
                card.pack(fill="x", pady=5)

                content = ctk.CTkFrame(card, fg_color="transparent")
                content.pack(fill="x", padx=15, pady=12)

                icon_box = ctk.CTkFrame(content, fg_color=COLORS["accent_secondary"], corner_radius=8, width=40, height=40)
                icon_box.pack(side="left", padx=(0, 12))
                icon_box.pack_propagate(False)
                ctk.CTkLabel(icon_box, text="🗄️", font=ctk.CTkFont(size=18), text_color="white").place(relx=0.5, rely=0.5, anchor="center")

                text_frame = ctk.CTkFrame(content, fg_color="transparent")
                text_frame.pack(side="left", fill="x", expand=True)
                ctk.CTkLabel(text_frame, text=name, font=ctk.CTkFont(size=14, weight="bold"), text_color=COLORS["text_primary"], anchor="w").pack(anchor="w")
                ctk.CTkLabel(text_frame, text=os.path.basename(db_path), font=ctk.CTkFont(size=11), text_color=COLORS["text_muted"], anchor="w").pack(anchor="w")

                btn_frame = ctk.CTkFrame(content, fg_color="transparent")
                btn_frame.pack(side="right")
                ctk.CTkButton(btn_frame, text="Use File", width=90, height=32, fg_color=COLORS["bg_card"], hover_color=COLORS["accent_primary"], font=ctk.CTkFont(size=12, weight="bold"), command=lambda n=name, p=db_path: self.selectGameDb(n, p)).pack(side="left", padx=5)
                ctk.CTkButton(btn_frame, text="✕", width=32, height=32, fg_color=COLORS["bg_card"], hover_color=COLORS["accent_danger"], command=lambda n=name: self.deleteGameDb(n)).pack(side="left")

        if count == 0:
            self.empty_state.pack(fill="x", pady=10)
        else:
            self.empty_state.pack_forget()

    def addGameDbManual(self):
        path = filedialog.askopenfilename(filetypes=[("Database files", "*.slt"), ("All files", "*.*")])
        if path:
            self.addGameDbLogic(path)

    def addGameDbLogic(self, path):
        if not os.path.isfile(path):
            messagebox.showerror("Invalid File", "Selected file does not exist.")
            return
        dialog = ctk.CTkInputDialog(text="Enter a name for this favorite:", title="Add Favorite Database")
        db_name = dialog.get_input()
        if not db_name or not db_name.strip():
            return
        db_name = db_name.strip()
        if db_name in self.game_dbs:
            if not messagebox.askyesno("Overwrite?", f"Favorite '{db_name}' already exists. Overwrite?"):
                return
        self.game_dbs[db_name] = {"path": path, "added": datetime.now().isoformat()}
        self.saveConfig(silent=True)
        self.refreshLibraryUi()
        self.log(f"✓ Favorite saved: {db_name}")

    def selectGameDb(self, name, path):
        if not os.path.isfile(path):
            messagebox.showerror("File Not Found", f"Database file not found:\n{path}")
            return

        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Use '{name}' as...")
        dialog.geometry("400x200")
        dialog.configure(fg_color=COLORS["bg_primary"])
        dialog.attributes("-topmost", True)
        x = self.winfo_x() + (self.winfo_width() // 2) - 200
        y = self.winfo_y() + (self.winfo_height() // 2) - 100
        dialog.geometry(f"+{x}+{y}")

        ctk.CTkLabel(dialog, text=f"How would you like to use '{name}'?", font=ctk.CTkFont(size=14, weight="bold"), text_color=COLORS["text_primary"]).pack(pady=20)

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=10)

        ctk.CTkButton(btn_frame, text="📌 Use as Target", fg_color=COLORS["accent_secondary"], height=40, font=ctk.CTkFont(size=12, weight="bold"),
            command=lambda: [self.master_drop_zone.setPath(path), self.onMasterSelected(path), dialog.destroy(), self.showPage("merger")]
        ).pack(side="left", padx=10)

        ctk.CTkButton(btn_frame, text="📦 Use as Source", fg_color=COLORS["accent_secondary"], height=40, font=ctk.CTkFont(size=12, weight="bold"),
            command=lambda: [self.source_drop_zone.setPath(path), self.onSourceSelected(path), dialog.destroy(), self.showPage("merger")]
        ).pack(side="left", padx=10)

    def deleteGameDb(self, name):
        if messagebox.askyesno("Delete Favorite", f"Delete favorite '{name}'?"):
            del self.game_dbs[name]
            self.saveConfig(silent=True)
            self.refreshLibraryUi()
            self.log(f"✓ Favorite deleted: {name}")

    def saveCurrentAsPreset(self):
        master = self.master_drop_zone.getPath()
        source = self.source_drop_zone.getPath()
        if not master or not source:
            messagebox.showwarning("Missing Files", "Please select both Target and Source databases first.")
            return
        if not os.path.isfile(master) or not os.path.isfile(source):
            messagebox.showerror("Invalid Files", "One or both selected files do not exist.")
            return
        dialog = ctk.CTkInputDialog(text="Enter a name for this config:", title="Save Configuration")
        preset_name = dialog.get_input()
        if not preset_name or not preset_name.strip():
            return
        preset_name = preset_name.strip()
        if preset_name in self.presets:
            if not messagebox.askyesno("Overwrite?", f"Config '{preset_name}' already exists. Overwrite?"):
                return
        self.presets[preset_name] = {
            "master": master,
            "source": source,
            "include_rims": self.rims_var.get(),
            "created": datetime.now().isoformat()
        }
        self.saveConfig(silent=True)
        self.refreshLibraryUi()
        self.log(f"✓ Config saved: {preset_name}")
        messagebox.showinfo("Success", f"Config '{preset_name}' saved!")

    def runPreset(self, name, data):
        master = data.get("master", "")
        source = data.get("source", "")
        include_rims = data.get("include_rims", False)
        if not os.path.isfile(master):
            messagebox.showerror("File Not Found", f"Target database not found:\n{master}")
            return
        if not os.path.isfile(source):
            messagebox.showerror("File Not Found", f"Source database not found:\n{source}")
            return
        self.master_drop_zone.setPath(master)
        self.source_drop_zone.setPath(source)
        self.rims_var.set(include_rims)
        self.showPage("merger")
        self.after(300, self.runMerge)

    def deletePreset(self, name):
        if messagebox.askyesno("Delete Config", f"Delete configuration '{name}'?"):
            del self.presets[name]
            self.saveConfig(silent=True)
            self.refreshLibraryUi()

    def setupBackupPage(self):
        header = ctk.CTkLabel(
            self.backup_page,
            text="Backup History",
            font=ctk.CTkFont(family="Ubuntu", size=32, weight="bold"),
            text_color=COLORS["text_primary"]
        )
        header.pack(anchor="w", pady=(0, 5))

        ctk.CTkLabel(
            self.backup_page,
            text="Restore or delete database snapshots created automatically before each merge.",
            font=ctk.CTkFont(size=13),
            text_color=COLORS["text_secondary"],
            wraplength=600,
            justify="left"
        ).pack(anchor="w", pady=(0, 20))

        info_card = ctk.CTkFrame(
            self.backup_page,
            fg_color=COLORS["bg_secondary"],
            corner_radius=12,
            border_width=1,
            border_color=COLORS["border"]
        )
        info_card.pack(fill="x", pady=(0, 20))

        info_inner = ctk.CTkFrame(info_card, fg_color="transparent")
        info_inner.pack(fill="x", padx=20, pady=15)
        ctk.CTkLabel(info_inner, text="ℹ️", font=ctk.CTkFont(size=16)).pack(side="left")
        ctk.CTkLabel(
            info_inner,
            text="Backups are automatically created before each merge operation and stored alongside your Target database.",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"],
            wraplength=500,
            justify="left"
        ).pack(side="left", padx=10)

        list_card = ctk.CTkFrame(
            self.backup_page,
            fg_color=COLORS["bg_secondary"],
            corner_radius=12,
            border_width=1,
            border_color=COLORS["border"]
        )
        list_card.pack(fill="both", expand=True, pady=10)

        ctk.CTkLabel(
            list_card,
            text="SELECT BACKUP VERSION",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLORS["text_muted"]
        ).pack(pady=(20, 10), padx=20, anchor="w")

        self.backup_list = ctk.CTkOptionMenu(
            list_card,
            values=["No Backups Found"],
            width=500,
            height=50,
            fg_color=COLORS["bg_card"],
            button_color=COLORS["accent_primary"],
            button_hover_color=COLORS["accent_secondary"],
            dropdown_fg_color=COLORS["bg_card"],
            dropdown_hover_color=COLORS["accent_primary"],
            font=ctk.CTkFont(size=13),
            corner_radius=10
        )
        self.backup_list.pack(pady=10, padx=20, anchor="w")

        btn_row = ctk.CTkFrame(list_card, fg_color="transparent")
        btn_row.pack(pady=30)

        ctk.CTkButton(
            btn_row,
            text=" Restore Selected",
            image=self.loadIcon("undo.png", size=18),
            fg_color=COLORS["accent_primary"],
            hover_color=COLORS["accent_secondary"],
            width=180,
            height=50,
            corner_radius=10,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.restoreSelected
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            btn_row,
            text=" Delete Backup",
            image=self.loadIcon("trash.png", size=18),
            fg_color=COLORS["bg_card"],
            hover_color=COLORS["accent_danger"],
            width=180,
            height=50,
            corner_radius=10,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.deleteSelected
        ).pack(side="left", padx=10)

        self.backup_count_label = ctk.CTkLabel(
            list_card,
            text="Total Backups: 0",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_muted"]
        )
        self.backup_count_label.pack(pady=(10, 20))

    def refreshBackups(self):
        self.after(0, self.refreshBackupsSafe)

    def refreshBackupsSafe(self):
        master_path = self.master_drop_zone.getPath()
        if not master_path or not os.path.exists(os.path.dirname(master_path) or "."):
            return
        directory = os.path.dirname(master_path)
        base_name  = os.path.basename(master_path)
        backups = sorted(
            [f for f in os.listdir(directory) if f.startswith(base_name) and f.endswith(".bak")],
            reverse=True
        )
        if backups:
            self.backup_list.configure(values=backups)
            self.backup_list.set(backups[0])
            self.backup_count_label.configure(text=f"Total Backups: {len(backups)}")
        else:
            self.backup_list.configure(values=["No Backups Found"])
            self.backup_list.set("No Backups Found")
            self.backup_count_label.configure(text="Total Backups: 0")

    def restoreSelected(self):
        selection = self.backup_list.get()
        if selection == "No Backups Found":
            return
        master_path = self.master_drop_zone.getPath()
        backup_full = os.path.join(os.path.dirname(master_path), selection)
        if messagebox.askyesno("Confirm Restore", f"Restore:\n\n{selection}\n\nThis will overwrite the current database."):
            threading.Thread(target=self.executeRestore, args=(backup_full, master_path, selection), daemon=True).start()

    def executeRestore(self, src, dst, name):
        try:
            shutil.copy2(src, dst)
            self.log(f"✓ RESTORED: {name}")
            self.after(0, lambda: messagebox.showinfo("Success", "Database restored successfully!"))
        except Exception as e:
            self.log(f"✗ RESTORE ERROR: {str(e)}")
            self.after(0, lambda: messagebox.showerror("Error", str(e)))

    def deleteSelected(self):
        selection = self.backup_list.get()
        if selection == "No Backups Found":
            return
        master_path = self.master_drop_zone.getPath()
        backup_full = os.path.join(os.path.dirname(master_path), selection)
        if messagebox.askyesno("Confirm Delete", f"Permanently delete this backup?\n\n{selection}\n\nThis cannot be undone."):
            try:
                os.remove(backup_full)
                self.log(f"✓ Deleted: {selection}")
                self.refreshBackups()
            except Exception as e:
                self.log(f"✗ DELETE ERROR: {str(e)}")

    def setupSettingsPage(self):
        header = ctk.CTkLabel(
            self.settings_page,
            text="Settings",
            font=ctk.CTkFont(family="Ubuntu", size=32, weight="bold"),
            text_color=COLORS["text_primary"]
        )
        header.pack(anchor="w", pady=(0, 20))

        comp_frame = ctk.CTkFrame(self.settings_page, fg_color=COLORS["bg_secondary"], corner_radius=12, border_width=1, border_color=COLORS["border"])
        comp_frame.pack(fill="x", pady=(10, 0), ipady=5)

        self.anim_var = ctk.BooleanVar(value=getattr(self, "animations_enabled", True))
        anim_row = ctk.CTkFrame(comp_frame, fg_color="transparent")
        anim_row.pack(fill="x", padx=20, pady=(20, 10))
        
        self.animations_switch = ctk.CTkSwitch(
            anim_row, text="Enable Buggy Page Animations", variable=self.anim_var,
            command=self.toggleAnimations, button_color=COLORS["accent_primary"],
            font=ctk.CTkFont(size=13)
        )
        self.animations_switch.pack(side="left")

        self.rims_default_var = ctk.BooleanVar(value=getattr(self, "default_rims_enabled", False))
        rims_row = ctk.CTkFrame(comp_frame, fg_color="transparent")
        rims_row.pack(fill="x", padx=20, pady=(0, 20))
        
        self.rims_switch = ctk.CTkSwitch(
            rims_row, text="Default 'Include Rims/Tires' to ON", variable=self.rims_default_var,
            command=self.toggleRimsDefault, button_color=COLORS["accent_primary"],
            font=ctk.CTkFont(size=13)
        )
        self.rims_switch.pack(side="left")

        bottom_row = ctk.CTkFrame(self.settings_page, fg_color="transparent")
        bottom_row.pack(fill="x", pady=20)

        ctk.CTkButton(
            bottom_row, text=" Clear Recent Files", image=self.loadIcon("trash.png", size=16),
            fg_color=COLORS["bg_card"], hover_color=COLORS["accent_danger"], height=40,
            command=self.clearRecentFiles, font=ctk.CTkFont(size=12, weight="bold")
        ).pack(side="left")

        ctk.CTkButton(
            bottom_row, text=" Save Settings", image=self.loadIcon("save.png", size=16),
            fg_color=COLORS["accent_success"], height=40,
            command=self.saveConfig, font=ctk.CTkFont(size=12, weight="bold")
        ).pack(side="right")

    def toggleAnimations(self):
        self.animations_enabled = self.anim_var.get()
        self.saveConfig(silent=True)

    def toggleRimsDefault(self):
        self.default_rims_enabled = self.rims_default_var.get()
        if hasattr(self, "rims_var"):
            self.rims_var.set(self.default_rims_enabled)
        self.saveConfig(silent=True)

    def clearRecentFiles(self):
        self.recent_files = []
        self.saveConfig(silent=True)
        self.refreshDashboard()

    def saveConfig(self, silent=False):
        try:
            with open(self.config_file, "w") as f:
                json.dump({
                    "presets":       self.presets,
                    "game_dbs":      self.game_dbs,
                    "recent_files":  self.recent_files,
                    "total_merged":  getattr(self, "total_merged", 0),
                    "last_master":   self.master_drop_zone.getPath() if hasattr(self, "master_drop_zone") else "",
                    "animations_enabled": getattr(self, "animations_enabled", True),
                    "default_rims_enabled": getattr(self, "default_rims_enabled", False)
                }, f, indent=2)
            if not silent:
                messagebox.showinfo("Saved", "Settings saved!")
        except Exception as e:
            if not silent:
                messagebox.showerror("Error", f"Failed to save settings:\n{e}")

    def loadConfig(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r") as f:
                    data = json.load(f)
                self.presets       = data.get("presets", {})
                self.game_dbs      = data.get("game_dbs", {})
                self.recent_files  = data.get("recent_files", [])
                self.total_merged  = data.get("total_merged", 0)

                self.animations_enabled = data.get("animations_enabled", True)
                self.default_rims_enabled = data.get("default_rims_enabled", False)

                if hasattr(self, "anim_var"):
                    self.anim_var.set(self.animations_enabled)
                if hasattr(self, "rims_default_var"):
                    self.rims_default_var.set(self.default_rims_enabled)
                if hasattr(self, "rims_var"):
                    self.rims_var.set(self.default_rims_enabled)

                last_master = data.get("last_master", "")
                if last_master and os.path.exists(last_master):
                    self.master_drop_zone.setPath(last_master)
                    self.log(f"✓ Session restored: {os.path.basename(last_master)}")
            except Exception:
                pass

    def addToRecentFiles(self, path):
        if path in self.recent_files:
            self.recent_files.remove(path)
        self.recent_files.insert(0, path)
        self.recent_files = self.recent_files[:10]
        self.saveConfig(silent=True)

    def log(self, message):
        self.after(0, lambda: self.logSafe(message))

    def logSafe(self, message):
        timestamp = datetime.now().strftime("[%H:%M:%S]")
        self.log_area.insert("end", f"{timestamp} {message}\n")
        self.log_area.see("end")

    def animateStatusDot(self):
        t = time.time() * 2.5
        intensity = (math.sin(t) + 1) / 2
        if getattr(self, "is_online", True):
            r = int(22  + (16  - 22)  * intensity)
            g = int(56  + (185 - 56)  * intensity)
            b = int(47  + (129 - 47)  * intensity)
        else:
            r = int(30  + (239 - 30)  * intensity)
            g = int(15  + (68  - 15)  * intensity)
            b = int(15  + (68  - 15)  * intensity)
        try:
            if self.status_dot.winfo_exists():
                self.status_dot.configure(text_color=f"#{r:02x}{g:02x}{b:02x}")
                self.after(50, self.animateStatusDot)
        except Exception:
            pass

    def processUiQueue(self):
        try:
            while True:
                task = self.ui_queue.get_nowait()
                task()
                self.ui_queue.task_done()
        except queue.Empty:
            pass
        self.after(100, self.processUiQueue)


if __name__ == "__main__":
    app = DBMerger()
    app.mainloop()
