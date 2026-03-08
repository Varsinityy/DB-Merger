import sqlite3
import shutil
import os
import requests
import tempfile
import json
import customtkinter as ctk
from tkinter import filedialog, messagebox, simpledialog
from datetime import datetime
from PIL import Image, ImageTk
from io import BytesIO
import threading
import time

# Robust import for Windows-specific features
try:
    from ctypes import windll, c_int, byref, sizeof, c_void_p
except ImportError:
    windll = None

# --- Theme Configuration ---
ctk.set_appearance_mode("Dark")

# Color Palette - Dark Glassmorphism with Subtle Gradients
COLORS = {
    "bg_primary": "#09090b",
    "bg_secondary": "#0f0f12",
    "bg_glass": "#18181b",
    "bg_card": "#1c1c21",
    "border": "#27272a",
    "border_light": "#3f3f46",
    "accent_primary": "#6366f1",    # Indigo
    "accent_secondary": "#8b5cf6",  # Purple
    "accent_tertiary": "#06b6d4",   # Cyan
    "accent_success": "#10b981",    # Emerald
    "accent_warning": "#f59e0b",    # Amber
    "accent_danger": "#ef4444",     # Red
    "text_primary": "#fafafa",
    "text_secondary": "#a1a1aa",
    "text_muted": "#71717a",
}

class AnimatedButton(ctk.CTkButton):
    """Custom button with hover animations"""
    def __init__(self, *args, **kwargs):
        self.original_fg = kwargs.get('fg_color', COLORS["bg_card"])
        self.hover_fg = kwargs.pop('hover_color', COLORS["accent_primary"])
        super().__init__(*args, **kwargs)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        
    def _on_enter(self, event):
        self.configure(fg_color=self.hover_fg)
        
    def _on_leave(self, event):
        self.configure(fg_color=self.original_fg)


class GlassFrame(ctk.CTkFrame):
    """Frame with glassmorphism styling"""
    def __init__(self, master, **kwargs):
        kwargs.setdefault('fg_color', COLORS["bg_glass"])
        kwargs.setdefault('corner_radius', 16)
        kwargs.setdefault('border_width', 1)
        kwargs.setdefault('border_color', COLORS["border"])
        super().__init__(master, **kwargs)


class DropZone(ctk.CTkFrame):
    """Drag and drop zone for files with save preset capability"""
    def __init__(self, master, label_text, on_drop_callback, on_save_callback=None, **kwargs):
        super().__init__(master, **kwargs)
        self.on_drop = on_drop_callback
        self.on_save = on_save_callback
        self.original_label = label_text
        self.configure(
            fg_color=COLORS["bg_secondary"],
            corner_radius=12,
            border_width=2,
            border_color=COLORS["border"]
        )
        
        self.is_drag_over = False
        
        # Header for Save Button
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent", height=30)
        self.header_frame.pack(fill="x", padx=5, pady=5)
        
        if self.on_save:
            self.save_btn = ctk.CTkButton(
                self.header_frame,
                text="💾",
                width=30,
                height=30,
                fg_color="transparent",
                hover_color=COLORS["bg_card"],
                font=ctk.CTkFont(size=16),
                command=self._on_save_click
            )
            self.save_btn.pack(side="right")
            
        # Inner content
        self.inner_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.inner_frame.pack(expand=True, fill="both", padx=3, pady=(0, 3))
        
        # Icon
        self.icon_label = ctk.CTkLabel(
            self.inner_frame,
            text="📁",
            font=ctk.CTkFont(size=32),
            text_color=COLORS["text_muted"]
        )
        self.icon_label.pack(pady=(10, 5))
        
        # Label
        self.text_label = ctk.CTkLabel(
            self.inner_frame,
            text=label_text,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS["text_secondary"]
        )
        self.text_label.pack(pady=(0, 5))
        
        # Hint
        self.hint_label = ctk.CTkLabel(
            self.inner_frame,
            text="Click to browse",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_muted"]
        )
        self.hint_label.pack(pady=(0, 5))
        
        # Path entry
        self.path_entry = ctk.CTkEntry(
            self.inner_frame,
            placeholder_text="No file selected...",
            height=40,
            fg_color=COLORS["bg_primary"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            font=ctk.CTkFont(size=12)
        )
        self.path_entry.pack(fill="x", padx=20, pady=(10, 20))
        
        # Bind click events
        self.bind("<Button-1>", self._on_click)
        self.inner_frame.bind("<Button-1>", self._on_click)
        self.icon_label.bind("<Button-1>", self._on_click)
        self.text_label.bind("<Button-1>", self._on_click)
        self.hint_label.bind("<Button-1>", self._on_click)
        
        # Bind drag events (simulated with Enter/Leave for visual feedback)
        self.bind("<Enter>", self._on_hover_enter)
        self.bind("<Leave>", self._on_hover_leave)
        
    def _on_hover_enter(self, event):
        self.configure(border_color=COLORS["accent_primary"])
        self.icon_label.configure(text_color=COLORS["accent_primary"])
        
    def _on_hover_leave(self, event):
        if not self.get_path():
            self.configure(border_color=COLORS["border"])
            self.icon_label.configure(text_color=COLORS["text_muted"])
        
    def _on_click(self, event):
        path = filedialog.askopenfilename(filetypes=[("Database files", "*.slt"), ("All files", "*.*")])
        if path:
            self.set_path(path)
            if self.on_drop:
                self.on_drop(path)

    def _on_save_click(self):
        path = self.get_path()
        if path and os.path.isfile(path) and self.on_save:
            self.on_save(path)
        elif not path:
             messagebox.showwarning("No File", "Please select a file first to save it as a preset.")

    def set_path(self, path):
        self.path_entry.delete(0, "end")
        self.path_entry.insert(0, path)
        self.icon_label.configure(text="✅", text_color=COLORS["accent_success"])
        self.text_label.configure(text="File Selected", text_color=COLORS["accent_success"])
        self.configure(border_color=COLORS["accent_success"])
        
    def get_path(self):
        return self.path_entry.get().strip('"')
    
    def reset(self):
        self.path_entry.delete(0, "end")
        self.icon_label.configure(text="📁", text_color=COLORS["text_muted"])
        self.text_label.configure(text=self.original_label, text_color=COLORS["text_secondary"])
        self.configure(border_color=COLORS["border"])


class ProgressCard(ctk.CTkFrame):
    """Animated progress card for merge operations"""
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=COLORS["bg_glass"], corner_radius=16, border_width=1, border_color=COLORS["border"], **kwargs)
        
        # Status icon
        self.status_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.status_frame.pack(fill="x", padx=20, pady=(20, 10))
        
        self.status_icon = ctk.CTkLabel(
            self.status_frame,
            text="⏳",
            font=ctk.CTkFont(size=24)
        )
        self.status_icon.pack(side="left")
        
        self.status_text = ctk.CTkLabel(
            self.status_frame,
            text="Ready to merge",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLORS["text_primary"]
        )
        self.status_text.pack(side="left", padx=10)
        
        # Progress bar
        self.progress = ctk.CTkProgressBar(
            self,
            height=8,
            corner_radius=4,
            fg_color=COLORS["bg_secondary"],
            progress_color=COLORS["accent_primary"]
        )
        self.progress.pack(fill="x", padx=20, pady=10)
        self.progress.set(0)
        
        # Progress text
        self.progress_text = ctk.CTkLabel(
            self,
            text="0% Complete",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_muted"]
        )
        self.progress_text.pack(pady=(0, 15))
        
    def set_progress(self, value, text=""):
        self.after(0, lambda: self._update_ui_progress(value, text))
        
    def _update_ui_progress(self, value, text):
        self.progress.set(value)
        self.progress_text.configure(text=f"{int(value * 100)}% Complete" + (f" - {text}" if text else ""))
        
    def set_status(self, icon, text, color=None):
        self.after(0, lambda: self._update_ui_status(icon, text, color))

    def _update_ui_status(self, icon, text, color):
        self.status_icon.configure(text=icon)
        self.status_text.configure(text=text, text_color=color or COLORS["text_primary"])
        
    def reset(self):
        self.progress.set(0)
        self.progress_text.configure(text="0% Complete")
        self.status_icon.configure(text="⏳")
        self.status_text.configure(text="Ready to merge", text_color=COLORS["text_primary"])


class PresetCard(ctk.CTkFrame):
    """Individual preset card for quick merge"""
    def __init__(self, master, preset_name, preset_data, on_run, on_delete, **kwargs):
        super().__init__(master, fg_color=COLORS["bg_secondary"], corner_radius=12, **kwargs)
        self.preset_name = preset_name
        self.preset_data = preset_data
        
        # Main content row
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="x", padx=15, pady=12)
        
        # Icon
        icon_box = ctk.CTkFrame(content, fg_color=COLORS["accent_primary"], corner_radius=8, width=40, height=40)
        icon_box.pack(side="left", padx=(0, 12))
        icon_box.pack_propagate(False)
        
        icon = ctk.CTkLabel(
            icon_box,
            text="⚡",
            font=ctk.CTkFont(size=20),
            text_color="white"
        )
        icon.place(relx=0.5, rely=0.5, anchor="center")
        
        # Text info
        text_frame = ctk.CTkFrame(content, fg_color="transparent")
        text_frame.pack(side="left", fill="x", expand=True)
        
        name_label = ctk.CTkLabel(
            text_frame,
            text=preset_name,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLORS["text_primary"],
            anchor="w"
        )
        name_label.pack(anchor="w")
        
        # Show truncated paths
        master_name = os.path.basename(preset_data.get("master", "Unknown"))
        source_name = os.path.basename(preset_data.get("source", "Unknown"))
        path_label = ctk.CTkLabel(
            text_frame,
            text=f"Target: {master_name} | Source: {source_name}",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_muted"],
            anchor="w"
        )
        path_label.pack(anchor="w")
        
        # Buttons
        btn_frame = ctk.CTkFrame(content, fg_color="transparent")
        btn_frame.pack(side="right")
        
        run_btn = ctk.CTkButton(
            btn_frame,
            text="Load & Run",
            width=90,
            height=32,
            fg_color=COLORS["accent_success"],
            hover_color="#059669",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=lambda: on_run(preset_name, preset_data)
        )
        run_btn.pack(side="left", padx=5)
        
        del_btn = ctk.CTkButton(
            btn_frame,
            text="✕",
            width=32,
            height=32,
            fg_color=COLORS["bg_card"],
            hover_color=COLORS["accent_danger"],
            font=ctk.CTkFont(size=12),
            command=lambda: on_delete(preset_name)
        )
        del_btn.pack(side="left")


class GameDBCard(ctk.CTkFrame):
    """Individual game database preset card"""
    def __init__(self, master, db_name, db_path, on_select, on_delete, **kwargs):
        super().__init__(master, fg_color=COLORS["bg_secondary"], corner_radius=12, **kwargs)
        self.db_name = db_name
        self.db_path = db_path
        
        # Main content row
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="x", padx=15, pady=12)
        
        # Icon
        icon_box = ctk.CTkFrame(content, fg_color=COLORS["accent_tertiary"], corner_radius=8, width=40, height=40)
        icon_box.pack(side="left", padx=(0, 12))
        icon_box.pack_propagate(False)
        
        icon = ctk.CTkLabel(
            icon_box,
            text="🎮",
            font=ctk.CTkFont(size=20),
            text_color="white"
        )
        icon.place(relx=0.5, rely=0.5, anchor="center")
        
        # Text info
        text_frame = ctk.CTkFrame(content, fg_color="transparent")
        text_frame.pack(side="left", fill="x", expand=True)
        
        name_label = ctk.CTkLabel(
            text_frame,
            text=db_name,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLORS["text_primary"],
            anchor="w"
        )
        name_label.pack(anchor="w")
        
        file_label = ctk.CTkLabel(
            text_frame,
            text=os.path.basename(db_path),
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_muted"],
            anchor="w"
        )
        file_label.pack(anchor="w")
        
        # Buttons
        btn_frame = ctk.CTkFrame(content, fg_color="transparent")
        btn_frame.pack(side="right")
        
        select_btn = ctk.CTkButton(
            btn_frame,
            text="Use File",
            width=90,
            height=32,
            fg_color=COLORS["bg_card"],
            hover_color=COLORS["accent_primary"],
            font=ctk.CTkFont(size=12, weight="bold"),
            command=lambda: on_select(db_name, db_path)
        )
        select_btn.pack(side="left", padx=5)
        
        del_btn = ctk.CTkButton(
            btn_frame,
            text="✕",
            width=32,
            height=32,
            fg_color=COLORS["bg_card"],
            hover_color=COLORS["accent_danger"],
            font=ctk.CTkFont(size=12),
            command=lambda: on_delete(db_name)
        )
        del_btn.pack(side="left")


class ResizeGrip(ctk.CTkFrame):
    """Grip to resize window while maintaining aspect ratio"""
    def __init__(self, master, aspect_ratio=None, **kwargs):
        super().__init__(master, width=20, height=20, corner_radius=0, fg_color="transparent", **kwargs)
        self.master_window = master
        self.aspect_ratio = aspect_ratio
        
        # Fix cursor for Windows (se-resize causes TclError on some Windows builds)
        cursor = "size_nw_se"

        self.grip_label = ctk.CTkLabel(
            self, 
            text="◢", 
            font=ctk.CTkFont(size=20), 
            text_color=COLORS["text_muted"],
            cursor=cursor
        )
        self.grip_label.place(relx=1.0, rely=1.0, anchor="se")
        
        self.grip_label.bind("<B1-Motion>", self.resize)
        self.grip_label.bind("<Button-1>", self.start_resize)
        
    def start_resize(self, event):
        self.start_x = event.x_root
        self.start_y = event.y_root
        self.start_w = self.master_window.winfo_width()
        self.start_h = self.master_window.winfo_height()

    def resize(self, event):
        dx = event.x_root - self.start_x
        
        new_w = self.start_w + dx
        
        if self.aspect_ratio:
            new_h = int(new_w / self.aspect_ratio)
        else:
            dy = event.y_root - self.start_y
            new_h = self.start_h + dy
            
        # Enforce minimums (scaled from 800 width)
        if new_w < 800: new_w = 800
        if new_h < 560: new_h = 560
            
        self.master_window.geometry(f"{new_w}x{new_h}")


class VarsinityDBMerger(ctk.CTk):
    def __init__(self):
        # 1. FIX: Enable DPI Awareness immediately to prevent navbar stretching
        if windll:
            try:
                windll.shcore.SetProcessDpiAwareness(1)
            except Exception:
                pass

        super().__init__()

        # Init member variables to prevent startup crashes if loading fails
        self.logo_image = None
        self.logo_small = None
        self.header_banner = None
        self.banner_pil_image = None
        self.temp_icon_path = os.path.join(tempfile.gettempdir(), f"varsinity_icon_{os.getpid()}.ico")

        # Window Setup
        self.title("Varsinity's DB Merger")
        # 2. FIX: Reduced default size to fit smaller screens (was 1200x950)
        self.geometry("1000x700")
        self.configure(fg_color=COLORS["bg_primary"])
        # 2. FIX: Reduced minimum size (was 1000, 700)
        self.minsize(800, 600)
        
        # REMOVE DEFAULT TITLEBAR (Integrated Window)
        self.overrideredirect(True) 

        # --- APPLY ROUNDED CORNERS ---
        self.after(10, self.apply_rounded_corners)
        
        # Path to memory file
        self.config_file = os.path.join(tempfile.gettempdir(), "varsinity_config.json")
        
        # Presets storage
        self.presets = {}
        self.game_dbs = {}
        self.recent_files = []
        
        # Animation state
        self.animation_running = False
        self.current_page = "merger"

        # Grid Layout
        # Proportional layout to keep sidebar relative
        self.grid_rowconfigure(0, weight=0) # Titlebar fixed height
        self.grid_rowconfigure(1, weight=1) # Content expands
        
        # Sidebar vs Content ratio (approx 200px : 800px at 1000px width)
        # Reduced from 26% to fix "too wide" issue while maintaining relative scaling
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=80)

        # Set URLs
        self.icon_url = "https://codehs.com/uploads/24cd9d070606620795f9a393dafaa62a" # Taskbar & Titlebar Icon
        self.logo_url = "https://codehs.com/uploads/fd81d80c9192d13a66ec9620d278a1ce" # Main UI Logo
        self.banner_url = "https://codehs.com/uploads/62ebc28cf290a5af5f30c9a705221c93" # Header Banner
        
        # --- Custom Titlebar ---
        self.setup_titlebar()
        
        # --- Sidebar Navigation ---
        self.setup_sidebar()
        
        # --- Main View Container ---
        self.view_container = ctk.CTkFrame(self, fg_color="transparent")
        self.view_container.grid(row=1, column=1, sticky="nsew", padx=40, pady=40)
        self.view_container.grid_columnconfigure(0, weight=1)
        self.view_container.grid_rowconfigure(0, weight=1)

        # Initialize pages
        self.setup_merger_page()
        self.setup_quick_merge_page()
        self.setup_backup_page()
        
        # Load previous session data on startup
        self.load_session_memory()
        self.show_page("merger")

        # Center window on screen initially
        self.center_window()
        
        # Load assets safely in background
        self.after(100, self.load_assets_safe)
        
        # Fix taskbar icon presence after window creation
        self.after(200, self.force_taskbar_presence)
        
        # 3. FIX: Enable resizing via Grip with fixed Aspect Ratio (1000/700)
        self.resize_grip = ResizeGrip(self, aspect_ratio=1.428)
        self.resize_grip.place(relx=1.0, rely=1.0, anchor="se", x=-5, y=-5)

    def apply_rounded_corners(self):
        """Apply rounded corners using Windows DWM API"""
        if windll:
            try:
                # Find the window handle
                # We use the parent because CTk windows often use a shell window
                HWND = windll.user32.GetParent(self.winfo_id())
                
                # DWMWA_WINDOW_CORNER_PREFERENCE = 33
                # DWMWCP_ROUND = 2
                attribute = 33
                value = c_int(2) 
                windll.dwmapi.DwmSetWindowAttribute(HWND, attribute, byref(value), sizeof(value))
            except Exception as e:
                print(f"Rounding error: {e}")

    def load_assets_safe(self):
        """Loads icons and images without blocking startup"""
        # 1. Load Icon (Taskbar & Titlebar)
        try:
            response = requests.get(self.icon_url, timeout=3)
            if response.status_code == 200:
                img_data = response.content
                icon_img = Image.open(BytesIO(img_data))
                
                # Save as ICO for taskbar (unique filename to avoid locks)
                icon_img.save(self.temp_icon_path, format='ICO', sizes=[(32, 32), (64, 64), (128, 128)])
                
                # Set window icon (if window exists)
                try:
                    self.iconbitmap(self.temp_icon_path)
                except Exception:
                    pass
                
                # Create small icon for titlebar
                self.logo_small = ctk.CTkImage(light_image=icon_img, dark_image=icon_img, size=(20, 20))
                
                if hasattr(self, 'title_icon_label'):
                    self.title_icon_label.configure(image=self.logo_small, text="")
        except Exception as e:
            print(f"Icon load error: {e}")
            
        # 2. Load Main Logo (Sidebar)
        try:
            response = requests.get(self.logo_url, timeout=3)
            if response.status_code == 200:
                img_data = response.content
                logo_img = Image.open(BytesIO(img_data))
                
                # Create CTkImage for main logo
                target_width = 180
                orig_w, orig_h = logo_img.size
                ratio = orig_h / orig_w
                target_height = int(target_width * ratio)
                
                self.logo_image = ctk.CTkImage(light_image=logo_img, dark_image=logo_img, size=(target_width, target_height))
                
                # Update UI elements that use this
                if hasattr(self, 'logo_label'):
                    self.logo_label.configure(image=self.logo_image, text="")
                    
        except Exception as e:
            print(f"Logo load error: {e}")

        # 3. Load Header Banner
        try:
            response = requests.get(self.banner_url, timeout=3)
            if response.status_code == 200:
                img_data = response.content
                self.banner_pil_image = Image.open(BytesIO(img_data)) # FIX 2: Save PIL image for resizing
                
                # Initial size setting
                target_width = 700
                orig_w, orig_h = self.banner_pil_image.size
                ratio = orig_h / orig_w
                target_height = int(target_width * ratio)

                self.header_banner = ctk.CTkImage(light_image=self.banner_pil_image, dark_image=self.banner_pil_image, size=(target_width, target_height))
                
                if hasattr(self, 'header_label'):
                    self.header_label.configure(image=self.header_banner, text="")
        except Exception as e:
            print(f"Banner load error: {e}")

    def force_taskbar_presence(self):
        try:
            if not windll:
                return
                
            # Arbitrary App ID for taskbar grouping
            myappid = 'varsinity.dbmerger.tool.v2.3'
            windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
            
            # Force window style to show in taskbar
            hwnd = windll.user32.GetParent(self.winfo_id())
            # GWL_EXSTYLE = -20
            style = windll.user32.GetWindowLongW(hwnd, -20)
            style = style & ~0x00000080 # WS_EX_TOOLWINDOW
            style = style | 0x00040000  # WS_EX_APPWINDOW
            windll.user32.SetWindowLongW(hwnd, -20, style)
            
            # Re-apply icon to the native handle if file exists
            if os.path.exists(self.temp_icon_path):
                self.iconbitmap(self.temp_icon_path)
            
            # Refresh visibility
            self.withdraw()
            self.deiconify()
            self.focus_force()
        except Exception as e:
            print(f"Taskbar force error: {e}")

    def center_window(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')

    def setup_titlebar(self):
        self.titlebar = ctk.CTkFrame(self, fg_color=COLORS["bg_secondary"], height=40, corner_radius=0)
        self.titlebar.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.titlebar.pack_propagate(False) # Forces the 40px height
        self.titlebar.bind("<ButtonPress-1>", self.start_move)
        self.titlebar.bind("<B1-Motion>", self.do_move)

        # Left side - Logo and title
        left_frame = ctk.CTkFrame(self.titlebar, fg_color="transparent")
        left_frame.pack(side="left", padx=10, fill="y")
        left_frame.bind("<ButtonPress-1>", self.start_move)
        left_frame.bind("<B1-Motion>", self.do_move)
        
        self.title_icon_label = ctk.CTkLabel(left_frame, text="🔀", font=ctk.CTkFont(size=16))
        self.title_icon_label.pack(side="left", padx=(5, 5))
        self.title_icon_label.bind("<ButtonPress-1>", self.start_move)
        self.title_icon_label.bind("<B1-Motion>", self.do_move)
        
        title_label = ctk.CTkLabel(left_frame, text="Varsinity's DB Merger", font=ctk.CTkFont(size=12, weight="bold"), text_color=COLORS["text_primary"])
        title_label.pack(side="left", padx=5)
        title_label.bind("<ButtonPress-1>", self.start_move)
        title_label.bind("<B1-Motion>", self.do_move)
        
        # Right side - Window Controls
        close_btn = ctk.CTkButton(self.titlebar, text="✕", width=45, height=40, fg_color="transparent", hover_color=COLORS["accent_danger"], command=self.close_window, corner_radius=0)
        close_btn.pack(side="right")

        min_btn = ctk.CTkButton(self.titlebar, text="—", width=45, height=40, fg_color="transparent", hover_color=COLORS["bg_card"], command=self.minimize_window, corner_radius=0)
        min_btn.pack(side="right")

        # Center - Recent files quick access
        center_frame = ctk.CTkFrame(self.titlebar, fg_color="transparent")
        center_frame.pack(side="left", padx=20, fill="both", expand=True)
        center_frame.bind("<ButtonPress-1>", self.start_move)
        center_frame.bind("<B1-Motion>", self.do_move)
        
        recent_label = ctk.CTkLabel(center_frame, text="Recent:", font=ctk.CTkFont(size=11, weight="bold"), text_color=COLORS["text_muted"])
        recent_label.pack(side="left", padx=(0, 10))
        recent_label.bind("<ButtonPress-1>", self.start_move)
        recent_label.bind("<B1-Motion>", self.do_move)
        
        self.recent_buttons_frame = ctk.CTkFrame(center_frame, fg_color="transparent")
        self.recent_buttons_frame.pack(side="left", fill="x")
        self.recent_buttons_frame.bind("<ButtonPress-1>", self.start_move)
        self.recent_buttons_frame.bind("<B1-Motion>", self.do_move)

    # Window Drag Logic
    def start_move(self, event):
        self.x = event.x
        self.y = event.y

    def stop_move(self, event):
        self.x = None
        self.y = None

    def do_move(self, event):
        deltax = event.x - self.x
        deltay = event.y - self.y
        x = self.winfo_x() + deltax
        y = self.winfo_y() + deltay
        self.geometry(f"+{x}+{y}")

    def minimize_window(self):
        # 4. FIX: Enhanced minimize functionality using Windows API
        if windll:
            try:
                hwnd = windll.user32.GetParent(self.winfo_id())
                windll.user32.ShowWindow(hwnd, 6) # SW_MINIMIZE = 6
            except Exception:
                self.iconify()
        else:
            self.iconify()
        
    def close_window(self):
        self.quit()

    def update_recent_buttons(self):
        """Update recent files in titlebar"""
        for widget in self.recent_buttons_frame.winfo_children():
            widget.destroy()
        
        if not self.recent_files:
            empty_label = ctk.CTkLabel(
                self.recent_buttons_frame,
                text="No recent files",
                font=ctk.CTkFont(size=10),
                text_color=COLORS["text_muted"]
            )
            empty_label.pack(side="left", padx=5)
            empty_label.bind("<ButtonPress-1>", self.start_move)
            empty_label.bind("<B1-Motion>", self.do_move)
            return
        
        for recent_path in self.recent_files[:5]:
            filename = os.path.basename(recent_path)
            btn = ctk.CTkButton(
                self.recent_buttons_frame,
                text=filename,
                width=80,
                height=24,
                font=ctk.CTkFont(size=9),
                fg_color=COLORS["bg_card"],
                hover_color=COLORS["accent_primary"],
                command=lambda p=recent_path: self._load_recent_file(p)
            )
            btn.pack(side="left", padx=3)

    def _load_recent_file(self, path):
        """Load a recent file into master drop zone"""
        if os.path.isfile(path):
            self.master_drop_zone.set_path(path)
            self._on_master_selected(path)
            self.log(f"✓ Recent file loaded: {os.path.basename(path)}")
        else:
            messagebox.showerror("File Not Found", f"File not found:\n{path}")
            if path in self.recent_files:
                self.recent_files.remove(path)
                self.save_session_memory()
                self.update_recent_buttons()

    def setup_sidebar(self):
        """Setup the glassmorphism sidebar"""
        self.nav_frame = ctk.CTkFrame(
            self, 
            corner_radius=0, 
            fg_color=COLORS["bg_secondary"],
            border_width=0
        )
        self.nav_frame.grid(row=1, column=0, sticky="nsew")
        
        # Logo section
        self.logo_container = ctk.CTkFrame(
            self.nav_frame,
            fg_color="transparent",
            height=120
        )
        self.logo_container.pack(fill="x", pady=(30, 20))
        
        # Logo label (image will be set by load_assets_safe)
        self.logo_label = ctk.CTkLabel(
            self.logo_container, 
            text="VARSINITY", 
            font=ctk.CTkFont(size=28, weight="bold"), 
            text_color=COLORS["accent_primary"]
        )
        self.logo_label.pack(pady=30, padx=20)
        
        # Divider
        self.divider = ctk.CTkFrame(
            self.nav_frame,
            height=1,
            fg_color=COLORS["border"]
        )
        self.divider.pack(fill="x", padx=25, pady=10)
        
        # Navigation section label
        nav_label = ctk.CTkLabel(
            self.nav_frame,
            text="NAVIGATION",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=COLORS["text_muted"]
        )
        nav_label.pack(anchor="w", padx=30, pady=(15, 10))
        
        # Navigation buttons
        self.btn_merger = self.create_nav_button(
            "🔀  Merger Dashboard",
            lambda: self.animated_page_switch("merger"),
            active=True
        )
        self.btn_merger.pack(fill="x", padx=15, pady=5)
        
        self.btn_quick = self.create_nav_button(
            "⚡  Quick Merge Library",
            lambda: self.animated_page_switch("quick")
        )
        self.btn_quick.pack(fill="x", padx=15, pady=5)

        self.btn_backup = self.create_nav_button(
            "💾  Backup History",
            lambda: self.animated_page_switch("backup")
        )
        self.btn_backup.pack(fill="x", padx=15, pady=5)
        
        # FIX 1: Move "System Online" and Version to bottom using side="bottom" and pack BEFORE the spacer
        # This ensures they are always anchored to the bottom regardless of window height.
        
        # Version info
        version_label = ctk.CTkLabel(
            self.nav_frame,
            text="v0.9.5",
            font=ctk.CTkFont(size=10),
            text_color=COLORS["text_muted"]
        )
        version_label.pack(side="bottom", pady=(0, 20))

        # Bottom section - Status card
        self.status_card = GlassFrame(
            self.nav_frame,
            fg_color=COLORS["bg_glass"],
            corner_radius=12
        )
        self.status_card.pack(side="bottom", fill="x", padx=15, pady=15)
        
        status_inner = ctk.CTkFrame(self.status_card, fg_color="transparent")
        status_inner.pack(fill="x", padx=15, pady=15)
        
        self.status_dot = ctk.CTkLabel(
            status_inner, 
            text="●",
            font=ctk.CTkFont(size=14),
            text_color=COLORS["accent_success"]
        )
        self.status_dot.pack(side="left")
        
        self.status_text = ctk.CTkLabel(
            status_inner,
            text="System Online",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLORS["text_primary"]
        )
        self.status_text.pack(side="left", padx=8)

        # Spacer (now packed last, fills remaining space)
        spacer = ctk.CTkFrame(self.nav_frame, fg_color="transparent")
        spacer.pack(fill="both", expand=True)
        
    def create_nav_button(self, text, command, active=False):
        """Create a styled navigation button"""
        # FIX 4: Add bg_color to fix rendering artifacts (black backdrop on text)
        btn = ctk.CTkButton(
            self.nav_frame,
            text=text,
            anchor="w",
            height=48,
            corner_radius=10,
            font=ctk.CTkFont(size=13, weight="bold" if active else "normal"),
            fg_color=COLORS["accent_primary"] if active else COLORS["bg_secondary"],
            bg_color=COLORS["bg_secondary"], # Ensures smooth blending with sidebar background
            text_color=COLORS["text_primary"],
            hover_color=COLORS["accent_primary"] if not active else COLORS["accent_secondary"],
            command=command
        )
        return btn
        
    def animated_page_switch(self, page):
        """Animate page transition"""
        if self.animation_running or self.current_page == page:
            return
            
        self.animation_running = True
        self.current_page = page
        
        # Quick fade effect simulation
        self.view_container.configure(fg_color=COLORS["bg_primary"])
        self.after(50, lambda: self._complete_page_switch(page))
        
    def _complete_page_switch(self, page):
        self.show_page(page)
        self.view_container.configure(fg_color="transparent")
        self.animation_running = False

    def save_session_memory(self, path=None):
        """Saves the last used database path, presets, game DBs, and recent files"""
        try:
            data = {
                "presets": self.presets,
                "game_dbs": self.game_dbs,
                "recent_files": self.recent_files
            }
            if path:
                data["last_db"] = path
            elif os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    old_data = json.load(f)
                    data["last_db"] = old_data.get("last_db", "")
            
            with open(self.config_file, 'w') as f:
                json.dump(data, f, indent=2)
        except: pass

    def add_to_recent_files(self, path):
        """Add a file to recent files list (max 5)"""
        if path in self.recent_files:
            self.recent_files.remove(path)
        self.recent_files.insert(0, path)
        self.recent_files = self.recent_files[:5]
        self.save_session_memory()
        self.update_recent_buttons()

    def load_session_memory(self):
        """Reloads the last used database, presets, game DBs, and recent files"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    
                    # Load presets
                    self.presets = data.get("presets", {})
                    # Load game DBs
                    self.game_dbs = data.get("game_dbs", {})
                    
                    self.refresh_quick_merge_ui()
                    
                    # Load recent files
                    self.recent_files = data.get("recent_files", [])
                    self.update_recent_buttons()
                    
                    # Load last database
                    path = data.get("last_db", "")
                    if os.path.exists(path):
                        self.master_drop_zone.set_path(path)
                        self.refresh_backups()
                        self.log(f"✓ SESSION RESTORED: {os.path.basename(path)}")
            except: pass

    def load_header_banner(self):
        # Using a safer approach with try-except, but for now we skip dynamic banner to avoid startup lag
        # You can re-enable if desired by loading in load_assets_safe
        return None

    def show_page(self, page):
        # Hide all pages
        self.merger_page.pack_forget()
        self.quick_page.pack_forget()
        self.backup_page.pack_forget()
        
        # Reset all nav buttons (removed font weight change to improve smoothness)
        for btn in [self.btn_merger, self.btn_quick, self.btn_backup]:
            btn.configure(fg_color=COLORS["bg_secondary"])
        
        # Show selected page and highlight button
        if page == "merger":
            self.merger_page.pack(fill="both", expand=True)
            self.btn_merger.configure(fg_color=COLORS["accent_primary"])
        elif page == "quick":
            self.quick_page.pack(fill="both", expand=True)
            self.btn_quick.configure(fg_color=COLORS["accent_primary"])
            self.refresh_quick_merge_ui()
        else:
            self.backup_page.pack(fill="both", expand=True)
            self.btn_backup.configure(fg_color=COLORS["accent_primary"])
            self.refresh_backups()

    def setup_merger_page(self):
        self.merger_page = ctk.CTkScrollableFrame(
            self.view_container, 
            fg_color="transparent",
            scrollbar_button_color=COLORS["border"],
            scrollbar_button_hover_color=COLORS["accent_primary"]
        )
        
        # Header Section
        self.header_frame = ctk.CTkFrame(self.merger_page, fg_color="transparent")
        self.header_frame.pack(fill="x", pady=(0, 25))
        
        # FIX 2: Bind Configure event to resize image
        self.header_frame.bind("<Configure>", self.resize_header_image)
        
        # Initialize with text, will be replaced by image if loaded
        self.header_label = ctk.CTkLabel(
            self.header_frame, 
            text="Database Merger",
            font=ctk.CTkFont(family="Inter", size=42, weight="bold"),
            text_color=COLORS["text_primary"],
            anchor="w"
        )
        self.header_label.pack(anchor="w")
            
        subtitle = ctk.CTkLabel(
            self.header_frame,
            text="Seamlessly merge your game databases with advanced conflict resolution",
            font=ctk.CTkFont(size=14),
            text_color=COLORS["text_secondary"],
            anchor="w"
        )
        subtitle.pack(anchor="w", pady=(5, 0))
        
        # Drop zones container
        drop_container = ctk.CTkFrame(self.merger_page, fg_color="transparent")
        drop_container.pack(fill="x", pady=15)
        drop_container.grid_columnconfigure(0, weight=1)
        drop_container.grid_columnconfigure(1, weight=1)
        
        # Master database drop zone
        master_frame = GlassFrame(drop_container)
        master_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=5)
        
        master_label = ctk.CTkLabel(
            master_frame,
            text="TARGET DATABASE",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLORS["accent_tertiary"]
        )
        master_label.pack(pady=(20, 10), padx=20, anchor="w")
        
        self.master_drop_zone = DropZone(
            master_frame,
            label_text="Main Game Database",
            on_drop_callback=self._on_master_selected,
            on_save_callback=self._save_file_preset_callback
        )
        self.master_drop_zone.pack(fill="x", padx=15, pady=(0, 20))
        
        # Source database drop zone
        source_frame = GlassFrame(drop_container)
        source_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=5)
        
        source_label = ctk.CTkLabel(
            source_frame,
            text="SOURCE DATABASE",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLORS["accent_secondary"]
        )
        source_label.pack(pady=(20, 10), padx=20, anchor="w")
        
        self.source_drop_zone = DropZone(
            source_frame,
            label_text="Mod Database",
            on_drop_callback=self._on_source_selected,
            on_save_callback=self._save_file_preset_callback
        )
        self.source_drop_zone.pack(fill="x", padx=15, pady=(0, 20))
        
        # Options Card
        self.options_card = GlassFrame(self.merger_page)
        self.options_card.pack(fill="x", pady=15)
        
        options_header = ctk.CTkLabel(
            self.options_card,
            text="MERGE OPTIONS",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLORS["text_muted"]
        )
        options_header.pack(pady=(20, 15), padx=25, anchor="w")
        
        options_inner = ctk.CTkFrame(self.options_card, fg_color="transparent")
        options_inner.pack(fill="x", padx=25, pady=(0, 20))
        
        self.rims_var = ctk.BooleanVar()
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
        self.cb_rims.pack(side=ctk.LEFT)
        
        self.btn_why = ctk.CTkButton(
            options_inner, 
            text="ℹ️ Why?",
            width=70,
            height=28,
            font=ctk.CTkFont(size=11),
            fg_color="transparent",
            text_color=COLORS["text_muted"],
            hover_color=COLORS["bg_card"],
            command=lambda: messagebox.showinfo(
                "Rims & Tires Info", 
                "Keep this option unchecked if your original database uses a different sorting method for rims and tires.\n\nEnabling this will include wheel and tire table data in the merge operation."
            )
        )
        self.btn_why.pack(side=ctk.LEFT, padx=15)
        
        # Save as preset button
        self.btn_save_preset = ctk.CTkButton(
            options_inner,
            text="💾 Save Config",
            width=140,
            height=32,
            fg_color=COLORS["bg_card"],
            hover_color=COLORS["accent_secondary"],
            font=ctk.CTkFont(size=12),
            command=self.save_current_as_preset
        )
        self.btn_save_preset.pack(side=ctk.RIGHT)
        
        # Progress Card
        self.progress_card = ProgressCard(self.merger_page)
        self.progress_card.pack(fill="x", pady=15)
        
        # Merge Button
        self.btn_merge = ctk.CTkButton(
            self.merger_page,
            text="⚡  EXECUTE DATABASE MERGE",
            fg_color=COLORS["accent_primary"],
            hover_color=COLORS["accent_secondary"],
            height=60,
            corner_radius=12,
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=COLORS["text_primary"],
            command=self.run_merge
        )
        self.btn_merge.pack(fill="x", pady=20)
        
        # Log Area with header
        log_header = ctk.CTkFrame(self.merger_page, fg_color="transparent")
        log_header.pack(fill="x")
        
        log_title = ctk.CTkLabel(
            log_header,
            text="📋 OPERATION LOG",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLORS["text_muted"]
        )
        log_title.pack(anchor="w", pady=(0, 10))
        
        self.log_area = ctk.CTkTextbox(
            self.merger_page,
            fg_color=COLORS["bg_secondary"],
            border_width=1,
            border_color=COLORS["border"],
            text_color=COLORS["accent_tertiary"],
            font=("Consolas", 12),
            corner_radius=12,
            height=200
        )
        self.log_area.pack(fill="both", expand=True, pady=(0, 10))

    def resize_header_image(self, event):
        """FIX 2: Resize the header image maintaining aspect ratio based on available width"""
        if hasattr(self, 'banner_pil_image') and self.banner_pil_image:
            new_width = event.width
            if new_width < 100: return # Prevent too small resize
            
            orig_w, orig_h = self.banner_pil_image.size
            ratio = orig_h / orig_w
            new_height = int(new_width * ratio)
            
            # Update image
            self.header_banner = ctk.CTkImage(
                light_image=self.banner_pil_image, 
                dark_image=self.banner_pil_image, 
                size=(new_width, new_height)
            )
            self.header_label.configure(image=self.header_banner)

    def setup_quick_merge_page(self):
        """Setup the Combined Quick Merge & Library page"""
        self.quick_page = ctk.CTkScrollableFrame(
            self.view_container,
            fg_color="transparent",
            scrollbar_button_color=COLORS["border"],
            scrollbar_button_hover_color=COLORS["accent_primary"]
        )
        
        # Header
        header_frame = ctk.CTkFrame(self.quick_page, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 25))
        
        header = ctk.CTkLabel(
            header_frame,
            text="⚡ Quick Merge Library",
            font=ctk.CTkFont(size=36, weight="bold"),
            text_color=COLORS["text_primary"],
            anchor="w"
        )
        header.pack(anchor="w")
        
        subtitle = ctk.CTkLabel(
            header_frame,
            text="Manage saved merge configurations and favorite database files",
            font=ctk.CTkFont(size=14),
            text_color=COLORS["text_secondary"],
            anchor="w"
        )
        subtitle.pack(anchor="w", pady=(5, 0))
        
        # Unified container
        self.library_container = ctk.CTkFrame(self.quick_page, fg_color="transparent")
        self.library_container.pack(fill="both", expand=True)
        
        # Empty state
        self.empty_state_library = ctk.CTkFrame(self.library_container, fg_color=COLORS["bg_glass"], corner_radius=16)
        
        empty_inner = ctk.CTkFrame(self.empty_state_library, fg_color="transparent")
        empty_inner.pack(expand=True, pady=40)
        
        empty_icon = ctk.CTkLabel(
            empty_inner,
            text="📭",
            font=ctk.CTkFont(size=36)
        )
        empty_icon.pack()
        
        empty_text = ctk.CTkLabel(
            empty_inner,
            text="Library is empty",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLORS["text_secondary"]
        )
        empty_text.pack(pady=(10, 5))

    def setup_backup_page(self):
        self.backup_page = ctk.CTkFrame(self.view_container, fg_color="transparent")
        
        # Header
        header_frame = ctk.CTkFrame(self.backup_page, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 30))
        
        header = ctk.CTkLabel(
            header_frame, 
            text="💾 Backup History",
            font=ctk.CTkFont(size=36, weight="bold"),
            text_color=COLORS["text_primary"],
            anchor="w"
        )
        header.pack(anchor="w")
        
        subtitle = ctk.CTkLabel(
            header_frame,
            text="Restore or manage your database snapshots",
            font=ctk.CTkFont(size=14),
            text_color=COLORS["text_secondary"],
            anchor="w"
        )
        subtitle.pack(anchor="w", pady=(5, 0))
        
        # Main Card
        self.list_card = GlassFrame(self.backup_page)
        self.list_card.pack(fill="both", expand=True, pady=10)
        
        # Info section
        info_frame = ctk.CTkFrame(self.list_card, fg_color=COLORS["bg_secondary"], corner_radius=10)
        info_frame.pack(fill="x", padx=30, pady=(30, 20))
        
        info_inner = ctk.CTkFrame(info_frame, fg_color="transparent")
        info_inner.pack(fill="x", padx=20, pady=15)
        
        info_icon = ctk.CTkLabel(
            info_inner,
            text="ℹ️",
            font=ctk.CTkFont(size=16)
        )
        info_icon.pack(side="left")
        
        info_text = ctk.CTkLabel(
            info_inner,
            text="Backups are automatically created before each merge operation",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"]
        )
        info_text.pack(side="left", padx=10)
        
        # Selection section
        select_label = ctk.CTkLabel(
            self.list_card,
            text="SELECT BACKUP VERSION",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLORS["text_muted"]
        )
        select_label.pack(pady=(20, 10), padx=30, anchor="w")
        
        self.backup_list = ctk.CTkOptionMenu(
            self.list_card,
            values=["No Backups Found"],
            width=500,
            height=50,
            fg_color=COLORS["bg_secondary"],
            button_color=COLORS["accent_primary"],
            button_hover_color=COLORS["accent_secondary"],
            dropdown_fg_color=COLORS["bg_card"],
            dropdown_hover_color=COLORS["accent_primary"],
            font=ctk.CTkFont(size=13),
            corner_radius=10
        )
        self.backup_list.pack(pady=10, padx=30, anchor="w")
        
        # Action buttons
        self.btn_row = ctk.CTkFrame(self.list_card, fg_color="transparent")
        self.btn_row.pack(pady=40)
        
        self.btn_restore = ctk.CTkButton(
            self.btn_row,
            text="↩️  Restore Selected",
            fg_color=COLORS["accent_primary"],
            hover_color=COLORS["accent_secondary"],
            width=200,
            height=50,
            corner_radius=10,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.restore_selected
        )
        self.btn_restore.pack(side="left", padx=10)
        
        self.btn_delete = ctk.CTkButton(
            self.btn_row,
            text="🗑️  Delete Backup",
            fg_color=COLORS["accent_danger"],
            hover_color="#dc2626",
            width=200,
            height=50,
            corner_radius=10,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.delete_selected
        )
        self.btn_delete.pack(side="left", padx=10)
        
        # Stats section
        self.stats_frame = ctk.CTkFrame(self.list_card, fg_color="transparent")
        self.stats_frame.pack(fill="x", padx=30, pady=(20, 30))
        
        self.backup_count_label = ctk.CTkLabel(
            self.stats_frame,
            text="Total Backups: 0",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_muted"]
        )
        self.backup_count_label.pack(side="left")
        
    def _on_master_selected(self, path):
        """Callback when master database is selected"""
        self.add_to_recent_files(path)
        self.save_session_memory(path)
        self.refresh_backups()
        self.log(f"✓ Master database loaded: {os.path.basename(path)}")

    def _on_source_selected(self, path):
        """Callback when source database is selected"""
        self.add_to_recent_files(path)
        self.log(f"✓ Source database loaded: {os.path.basename(path)}")

    def _save_file_preset_callback(self, path):
        """Callback from DropZone save button"""
        self._add_game_db_logic(path)

    def log(self, message):
        # THREAD-SAFE UI UPDATE: Using after() to schedule GUI updates on main thread
        self.after(0, lambda: self._log_safe(message))

    def _log_safe(self, message):
        timestamp = datetime.now().strftime("[%H:%M:%S]")
        self.log_area.insert("end", f"{timestamp} {message}\n")
        self.log_area.see("end")

    def add_game_db_preset_manual(self):
        """Manually browse for a file to add as preset"""
        path = filedialog.askopenfilename(filetypes=[("Database files", "*.slt"), ("All files", "*.*")])
        if path:
            self._add_game_db_logic(path)

    def _add_game_db_logic(self, path):
        """Shared logic for adding a game DB preset"""
        if not os.path.isfile(path):
            messagebox.showerror("Invalid File", "Selected file does not exist.")
            return
        
        # Get custom name
        dialog = ctk.CTkInputDialog(
            text="Enter a name for this favorite:",
            title="Add Favorite Database"
        )
        db_name = dialog.get_input()
        
        if not db_name or not db_name.strip():
            return
            
        db_name = db_name.strip()
        
        # Check for duplicate
        if db_name in self.game_dbs:
            if not messagebox.askyesno("Overwrite?", f"Favorite '{db_name}' already exists. Overwrite?"):
                return
        
        # Save game DB
        self.game_dbs[db_name] = {
            "path": path,
            "added": datetime.now().isoformat()
        }
        
        self.save_session_memory()
        self.refresh_quick_merge_ui()
        self.log(f"✓ Favorite database saved: {db_name}")

    def refresh_quick_merge_ui(self):
        """Refresh unified library list"""
        
        for widget in self.library_container.winfo_children():
            if widget != self.empty_state_library:
                widget.destroy()
        
        items_count = 0
        
        # Add Presets (Pairs)
        if self.presets:
            header = ctk.CTkLabel(self.library_container, text="MERGE CONFIGURATIONS", font=ctk.CTkFont(size=12, weight="bold"), text_color=COLORS["text_muted"])
            header.pack(fill="x", pady=(10, 5), padx=5, anchor="w")
            
            for name, data in self.presets.items():
                items_count += 1
                card = PresetCard(
                    self.library_container,
                    preset_name=name,
                    preset_data=data,
                    on_run=self.run_preset,
                    on_delete=self.delete_preset
                )
                card.pack(fill="x", pady=5)
                
        # Add Files (Single)
        if self.game_dbs:
            header = ctk.CTkLabel(self.library_container, text="FAVORITE FILES", font=ctk.CTkFont(size=12, weight="bold"), text_color=COLORS["text_muted"])
            header.pack(fill="x", pady=(15, 5), padx=5, anchor="w")
            
            for name, data in self.game_dbs.items():
                items_count += 1
                card = GameDBCard(
                    self.library_container,
                    db_name=name,
                    db_path=data.get("path", ""),
                    on_select=self._select_game_db,
                    on_delete=self.delete_game_db
                )
                card.pack(fill="x", pady=5)

        if items_count == 0:
            self.empty_state_library.pack(fill="both", expand=True)
        else:
            self.empty_state_library.pack_forget()

    def _select_game_db(self, name, path):
        """Select a game database and show options"""
        if not os.path.isfile(path):
            messagebox.showerror("File Not Found", f"Database file not found:\n{path}")
            return
        
        # Create selection dialog
        dialog = ctk.CTkToplevel()
        dialog.title(f"Use '{name}' as...")
        dialog.geometry("400x200")
        dialog.configure(fg_color=COLORS["bg_primary"])
        dialog.attributes("-topmost", True)
        
        # Position near center of app
        x = self.winfo_x() + (self.winfo_width() // 2) - 200
        y = self.winfo_y() + (self.winfo_height() // 2) - 100
        dialog.geometry(f"+{x}+{y}")
        
        # Remove titlebar for dialog too to match style (optional, but keeping simple here)
        # dialog.overrideredirect(True) 
        
        label = ctk.CTkLabel(
            dialog,
            text=f"How would you like to use '{name}'?",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLORS["text_primary"]
        )
        label.pack(pady=20)
        
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=10)
        
        target_btn = ctk.CTkButton(
            btn_frame,
            text="📌 Use as Target",
            fg_color=COLORS["accent_tertiary"],
            hover_color=COLORS["accent_secondary"],
            height=40,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=lambda: [self.master_drop_zone.set_path(path), self._on_master_selected(path), dialog.destroy(), self.animated_page_switch("merger")]
        )
        target_btn.pack(side="left", padx=10, pady=10)
        
        source_btn = ctk.CTkButton(
            btn_frame,
            text="📦 Use as Source",
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["accent_secondary"],
            height=40,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=lambda: [self.source_drop_zone.set_path(path), self._on_source_selected(path), dialog.destroy(), self.animated_page_switch("merger")]
        )
        source_btn.pack(side="left", padx=10, pady=10)

    def delete_game_db(self, name):
        """Delete a game database preset"""
        if messagebox.askyesno("Delete Favorite", f"Delete favorite database '{name}'?"):
            del self.game_dbs[name]
            self.save_session_memory()
            self.refresh_quick_merge_ui()
            self.log(f"✓ Favorite deleted: {name}")

    def save_current_as_preset(self):
        """Save current configuration as a preset"""
        master = self.master_drop_zone.get_path()
        source = self.source_drop_zone.get_path()
        
        if not master or not source:
            messagebox.showwarning("Missing Files", "Please select both target and source databases first.")
            return
            
        if not os.path.isfile(master) or not os.path.isfile(source):
            messagebox.showerror("Invalid Files", "One or both selected files do not exist.")
            return
        
        # Create custom dialog
        dialog = ctk.CTkInputDialog(
            text="Enter a name for this config:",
            title="Save Configuration"
        )
        preset_name = dialog.get_input()
        
        if not preset_name or not preset_name.strip():
            return
            
        preset_name = preset_name.strip()
            
        # Check for duplicate
        if preset_name in self.presets:
            if not messagebox.askyesno("Overwrite?", f"Config '{preset_name}' already exists. Overwrite?"):
                return
        
        # Save preset
        self.presets[preset_name] = {
            "master": master,
            "source": source,
            "include_rims": self.rims_var.get(),
            "created": datetime.now().isoformat()
        }
        
        self.save_session_memory()
        self.refresh_quick_merge_ui()
        self.log(f"✓ Merge config saved: {preset_name}")
        messagebox.showinfo("Success", f"Config '{preset_name}' saved successfully!")
                
    def run_preset(self, name, data):
        """Run a saved preset"""
        master = data.get("master", "")
        source = data.get("source", "")
        include_rims = data.get("include_rims", False)
        
        # Validate files exist
        if not os.path.isfile(master):
            messagebox.showerror("File Not Found", f"Target database not found:\n{master}")
            return
        if not os.path.isfile(source):
            messagebox.showerror("File Not Found", f"Source database not found:\n{source}")
            return
            
        # Switch to merger page and populate
        self.master_drop_zone.set_path(master)
        self.source_drop_zone.set_path(source)
        self.rims_var.set(include_rims)
        
        self.animated_page_switch("merger")
        
        # Run merge after page switch
        self.after(200, self.run_merge)
        
    def delete_preset(self, name):
        """Delete a saved preset"""
        if messagebox.askyesno("Delete Config", f"Delete configuration '{name}'?"):
            del self.presets[name]
            self.save_session_memory()
            self.refresh_quick_merge_ui()

    def run_merge(self):
        master = self.master_drop_zone.get_path()
        source = self.source_drop_zone.get_path()
        
        if not os.path.isfile(master) or not os.path.isfile(source):
            messagebox.showerror("Error", "Please select valid database files!")
            return
            
        # Start merge in thread to keep UI responsive
        threading.Thread(target=self._execute_merge, args=(master, source), daemon=True).start()
        
    def _execute_merge(self, master, source):
        """Execute merge operation with advanced error reporting"""
        self.set_status("Processing", COLORS["accent_warning"])
        self.progress_card.set_status("🔄", "Preparing merge...", COLORS["accent_warning"])
        
        try:
            # --- NEW PRECISION CHECK: Header Validation ---
            for label, path in [("Target", master), ("Source", source)]:
                with open(path, 'rb') as f:
                    header = f.read(16)
                    if not header:
                        raise ValueError(f"The {label} file is empty (0 bytes).")
                    if header != b'SQLite format 3\x00':
                        # Check if it's a common modding file mistake
                        if b'BURGM' in header:
                            raise ValueError(f"The {label} file appears to be a compressed Game Archive, not a Database.")
                        raise ValueError(f"The {label} file is not a valid SQLite database (Header Mismatch).\n\nIt may be encrypted or corrupted.")

            # Step 1: Create backup
            self.progress_card.set_progress(0.1, "Creating backup...")
            timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = f"{master}_{timestamp_str}.bak"
            shutil.copy2(master, backup_path)
            self.log(f"✓ Backup created: {os.path.basename(backup_path)}")
            
            # Step 2: Connect to databases
            self.progress_card.set_progress(0.2, "Connecting...")
            conn = sqlite3.connect(master)
            cursor = conn.cursor()
            
            # Step 3: Attach with Specific Error Catching
            source_escaped = source.replace("'", "''")
            try:
                cursor.execute(f"ATTACH DATABASE '{source_escaped}' AS mod_db")
            except sqlite3.DatabaseError as e:
                if "file is not a database" in str(e).lower():
                    raise ValueError(f"SQLite cannot read the Source file.\n\nPossible reasons:\n1. The file is encrypted.\n2. The file is a different version (SQLCipher).\n3. The file is corrupted.")
                raise e
            
            self.log("✓ Databases connected and validated")
            
            # Step 4: Analyze Tables
            cursor.execute("SELECT name FROM mod_db.sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            if not tables:
                raise ValueError("Source database is empty (contains no tables to merge).")

            total_tables = len(tables)
            self.log(f"✓ Processing {total_tables} tables...")
            
            # Step 5: Merge tables
            count = 0
            for i, table in enumerate(tables):
                if table.startswith("sqlite_"): continue
                if not self.rims_var.get() and ("Wheel" in table or "Tire" in table): continue
                    
                progress = 0.3 + (0.6 * (i + 1) / total_tables)
                self.progress_card.set_progress(progress, f"Merging: {table}")
                
                cursor.execute(f"INSERT OR REPLACE INTO main.{table} SELECT * FROM mod_db.{table}")
                count += 1
                
            # Step 6: Finalize
            conn.commit()
            conn.close()
            
            self.progress_card.set_progress(1.0, "Complete!")
            self.progress_card.set_status("✅", f"Success! {count} tables merged", COLORS["accent_success"])
            self.log(f"✓ SUCCESS: {count} tables synced")
            self.after(0, lambda: messagebox.showinfo("Success", f"Merge Complete!\n{count} tables processed successfully."))
            
        except ValueError as ve:
            # Custom clean errors for the user
            self.progress_card.set_status("❌", "Validation Failed", COLORS["accent_danger"])
            self.log(f"✗ VALIDATION ERROR: {str(ve)}")
            self.after(0, lambda: messagebox.showerror("Database Validation Error", str(ve)))
        except Exception as e:
            # System errors
            self.progress_card.set_status("❌", "System Error", COLORS["accent_danger"])
            self.log(f"✗ SYSTEM ERROR: {str(e)}")
            self.after(0, lambda: messagebox.showerror("Merge Failed", f"A system error occurred:\n{str(e)}"))
            
        finally:
            self.after(0, lambda: self.set_status("System Online", COLORS["accent_success"]))

    def refresh_backups(self):
        # Use AFTER to ensure UI thread safety
        self.after(0, self._refresh_backups_safe)

    def _refresh_backups_safe(self):
        master_path = self.master_drop_zone.get_path()
        if not master_path or not os.path.exists(os.path.dirname(master_path)): 
            return
            
        directory = os.path.dirname(master_path)
        base_name = os.path.basename(master_path)
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

    def restore_selected(self):
        selection = self.backup_list.get()
        if selection == "No Backups Found": 
            return
            
        master_path = self.master_drop_zone.get_path()
        # Look for backup in the same folder as master DB
        backup_full_path = os.path.join(os.path.dirname(master_path), selection)
        
        if messagebox.askyesno("Confirm Restore", f"Are you sure you want to restore:\n\n{selection}\n\nThis will overwrite the current database."):
            self.set_status("Restoring", COLORS["accent_warning"])
            # Run restore in thread so UI doesn't freeze
            threading.Thread(target=self._execute_restore, args=(backup_full_path, master_path, selection), daemon=True).start()

    def _execute_restore(self, src, dst, name):
        try:
            shutil.copy2(src, dst)
            self.after(0, lambda: messagebox.showinfo("Success", "Database restored successfully!"))
            self.log(f"✓ RESTORED: {name}")
        except Exception as e:
            self.log(f"✗ RESTORE ERROR: {str(e)}")
            self.after(0, lambda: messagebox.showerror("Error", str(e)))
        finally:
            self.set_status("System Online", COLORS["accent_success"])

    def delete_selected(self):
        selection = self.backup_list.get()
        if selection == "No Backups Found": 
            return
            
        master_path = self.master_drop_zone.get_path()
        backup_full_path = os.path.join(os.path.dirname(master_path), selection)
        
        if messagebox.askyesno("Confirm Delete", f"Permanently delete this backup?\n\n{selection}\n\nThis action cannot be undone."):
            try:
                os.remove(backup_full_path)
                self.log(f"✓ Deleted: {selection}")
                self.refresh_backups()
            except Exception as e:
                self.log(f"✗ DELETE ERROR: {str(e)}")

    def set_status(self, status, color):
        """Update the status indicator (Thread-Safe)"""
        self.after(0, lambda: self._set_status_safe(status, color))

    def _set_status_safe(self, status, color):
        self.status_dot.configure(text_color=color)
        self.status_text.configure(text=status)

    def __del__(self):
        try:
            if hasattr(self, 'temp_icon_path') and os.path.exists(self.temp_icon_path):
                # Only delete if we own it (check logic) or just let OS handle temp files
                os.unlink(self.temp_icon_path)
        except: pass


if __name__ == "__main__":
    app = VarsinityDBMerger()
    app.mainloop()