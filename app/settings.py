import os
import sys
import json
import urllib.request
import shutil
import subprocess
from pathlib import Path

from PySide6.QtCore import Qt, Signal, QThread, QObject
from PySide6.QtGui import QColor, QPainter, QFont, QKeySequence
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QStackedWidget,
    QSlider, QSpinBox, QFontComboBox, QTreeWidget, QTreeWidgetItem,
    QListWidget, QListWidgetItem, QAbstractItemView,
    QKeySequenceEdit, QMessageBox, QLineEdit, QComboBox, QCheckBox, QDialog, QProgressBar
)


# ============================================================
# مسیرها
# ============================================================

if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    # نسخه‌های AppImage / EXE / بسته‌های فریز شده
    BASE_DIR = Path(sys._MEIPASS)

    # تنظیمات کاربر باید خارج از بسته ذخیره شوند
    CONFIG_FILE = (
        Path.home()
        / ".config"
        / "liveflow-widget"
        / "markets.json"
    )
else:
    # حالت اجرای سورس
    BASE_DIR = Path(__file__).resolve().parent.parent
    CONFIG_FILE = BASE_DIR / "config" / "markets.json"


AUTOSTART_DIR = Path.home() / ".config" / "autostart"
DESKTOP_FILE = AUTOSTART_DIR / "liveflow-widget.desktop"


# ============================================================
# بازارها
# ============================================================

ALL_MARKETS = {
    "طلا و سکه": [
        ("sekee", "سکه امامی"),
        ("nim", "نیم سکه"),
        ("rob", "ربع سکه"),
        ("geram18", "گرم ۱۸ عیار"),
        ("geram24", "گرم ۲۴ عیار"),
        ("ons", "انس جهانی طلا")
    ],

    "ارزهای خارجی": [
        ("price_dollar_rl", "دلار آمریکا"),
        ("price_eur", "یورو"),
        ("price_gbp", "پوند انگلیس"),
        ("price_aed", "درهم امارات"),
        ("price_try", "لیر ترکیه"),
        ("price_cny", "یوان چین")
    ],

    "ارزهای دیجیتال": [
        ("crypto-tether", "تتر"),
        ("tether", "تتر (لینک دوم)"),
        ("crypto-bitcoin", "بیت‌کوین"),
        ("crypto-ethereum", "اتریوم"),
        ("crypto-bnb", "بایننس کوین"),
        ("crypto-solana", "سولانا")
    ],

    "بورس و انرژی": [
        ("oil_brent", "نفت برنت"),
        ("gc30", "شاخص بورس"),
        ("silver", "انس نقره")
    ]
}


# ============================================================
# Settings Window
# ============================================================

class UpdateProgressDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("LiveFlow Widget")
        self.setFixedSize(430, 150)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        self.label = QLabel("در حال دانلود بروزرسانی...")
        self.label.setStyleSheet("color: #e5e7eb; font-size: 14px;")
        layout.addWidget(self.label)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(True)
        self.progress.setStyleSheet("""
            QProgressBar {
                background: #1e293b;
                color: #e5e7eb;
                border: 1px solid #334155;
                border-radius: 7px;
                text-align: center;
                height: 22px;
            }
            QProgressBar::chunk {
                background: #38bdf8;
                border-radius: 6px;
            }
        """)
        layout.addWidget(self.progress)

        self.cancelled = False
        self.cancel_button = QPushButton("لغو")
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background: #1e293b;
                color: #e5e7eb;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 16px;
            }
            QPushButton:hover {
                background: #334155;
            }
        """)
        layout.addWidget(self.cancel_button, alignment=Qt.AlignRight)

        self.cancel_button.clicked.connect(self.cancel_download)
        self.setStyleSheet("QDialog { background: #0f172a; }")
    def cancel_download(self):
        self.cancelled = True
        self.reject()


class SettingsWindow(QWidget):

    # این سیگنال بعد از ذخیره موفق تنظیمات ارسال می‌شود
    # تا Widget اصلی بتواند تنظیمات را همان لحظه اعمال کند.
    settings_saved = Signal()

    def __init__(self):
        super().__init__()

        self.setFixedSize(860, 660)

        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )

        self.setAttribute(Qt.WA_TranslucentBackground)

        # ====================================================
        # تنظیمات پیش‌فرض
        # ====================================================

        self.config = {
            "markets": [],

            "appearance": {
                "opacity": 210,
                "font_size": 13,
                "font_family": "Noto Sans",
                "rows_visible": 6,
                "interval": 120,
                "language": "fa",
                "autostart": False
            },

            "hotkeys": {
                "close": "Ctrl+Q",
                "hide": "Ctrl+H",
                "settings": "Ctrl+Alt+S"
            }
        }

        self.load_config()
        self.build_ui()
        self.populate_markets()
        self.apply_live_preview()

    # ========================================================
    # Load Config
    # ========================================================

    def load_config(self):
        try:
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    loaded = json.load(f)

                if isinstance(loaded, dict):
                    # به‌صورت امن تنظیمات موجود را با پیش‌فرض‌ها ترکیب می‌کنیم
                    if "markets" in loaded:
                        self.config["markets"] = loaded["markets"]

                    if "appearance" in loaded and isinstance(
                        loaded["appearance"], dict
                    ):
                        self.config["appearance"].update(
                            loaded["appearance"]
                        )

                    if "hotkeys" in loaded and isinstance(
                        loaded["hotkeys"], dict
                    ):
                        self.config["hotkeys"].update(
                            loaded["hotkeys"]
                        )

        except Exception as e:
            print(f"Config load error: {e}")

    # ========================================================
    # Live Preview
    # ========================================================

    def apply_live_preview(self):
        font_name = self.combo_font.currentFont().family()
        font_size = self.spin_font.value()

        self.setStyleSheet(f"""
            QWidget {{
                color: #f8fafc;
                font-family: '{font_name}';
            }}

            QPushButton {{
                border: none;
                border-radius: 8px;
                padding: 10px;
                color: #cbd5e1;
                background: transparent;
                font-size: 13px;
            }}

            QPushButton:hover {{
                background: rgba(255,255,255,15);
                color: #fff;
            }}

            QLineEdit, QSpinBox, QFontComboBox {{
                background: rgba(15, 23, 42, 200);
                color: #fff;
                border: 1px solid rgba(255,255,255,20);
                border-radius: 6px;
                padding: 6px;
                font-size: {font_size}px;
            }}

            QComboBox {{
                background: rgba(15, 23, 42, 200);
                color: #fff;
                border: 1px solid rgba(255,255,255,20);
                border-radius: 6px;
                padding: 6px;
                font-size: {font_size}px;
            }}

            QComboBox QAbstractItemView {{
                background: rgb(30, 41, 59);
                color: #fff;
                border: 1px solid rgba(255,255,255,20);
                selection-background-color: #38bdf8;
            }}

            QTreeWidget, QListWidget {{
                background: rgba(15,23,42,150);
                border: 1px solid rgba(255,255,255,10);
                border-radius: 8px;
                padding: 5px;
                font-size: {font_size}px;
                outline: none;
            }}

            QTreeWidget::item, QListWidget::item {{
                padding: 6px;
                border-radius: 4px;
            }}

            QTreeWidget::item:selected,
            QListWidget::item:selected {{
                background: rgba(56,189,248,40);
                color: #fff;
            }}

            QSlider::groove:horizontal {{
                background: #475569;
                height: 6px;
                border-radius: 3px;
            }}

            QSlider::handle:horizontal {{
                background: #38bdf8;
                width: 14px;
                margin: -4px 0;
                border-radius: 7px;
            }}

            QKeySequenceEdit {{
                background: rgba(15, 23, 42, 200);
                color: #38bdf8;
                border-radius: 6px;
                padding: 6px;
            }}

            QCheckBox {{
                spacing: 8px;
                font-size: 13px;
            }}

            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid rgba(255,255,255,30);
                background: rgba(15, 23, 42, 200);
            }}

            QCheckBox::indicator:checked {{
                background: #38bdf8;
                border-color: #38bdf8;
            }}
        """)

        self.update()

    # ========================================================
    # Autostart
    # ========================================================

    def handle_autostart(self, enable):
        try:
            if enable:

                AUTOSTART_DIR.mkdir(
                    parents=True,
                    exist_ok=True
                )

                # در نسخه فریز شده:
                # خود executable را اجرا می‌کنیم.
                if getattr(sys, "frozen", False):
                    exec_line = f'"{sys.executable}"'

                else:
                    # در حالت سورس:
                    python_path = sys.executable
                    script_path = BASE_DIR / "app" / "widget.py"

                    exec_line = (
                        f'"{python_path}" "{script_path}"'
                    )

                desktop_content = f"""[Desktop Entry]
Type=Application
Name=LiveFlow Widget
Exec={exec_line}
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Terminal=false
"""

                with open(
                    DESKTOP_FILE,
                    "w",
                    encoding="utf-8"
                ) as f:
                    f.write(desktop_content)

            else:

                if DESKTOP_FILE.exists():
                    DESKTOP_FILE.unlink()

        except Exception as e:
            print(f"Autostart error: {e}")

    # ========================================================
    # Save Config
    # ========================================================

    def save_config(self):

        try:

            # ------------------------------------------------
            # بازارهای انتخاب‌شده
            # ------------------------------------------------

            saved_markets = []

            for i in range(self.list_sel.count()):

                item = self.list_sel.item(i)

                saved_markets.append({
                    "key": item.data(Qt.UserRole),
                    "name": item.text(),
                    "enabled": True
                })

            self.config["markets"] = saved_markets

            # ------------------------------------------------
            # Autostart
            # ------------------------------------------------

            is_autostart = self.chk_autostart.isChecked()

            self.handle_autostart(is_autostart)

            # ------------------------------------------------
            # Appearance
            # ------------------------------------------------

            self.config["appearance"].update({

                "opacity":
                    self.slider_opacity.value(),

                "font_size":
                    self.spin_font.value(),

                "font_family":
                    self.combo_font.currentFont().family(),

                "rows_visible":
                    self.spin_rows.value(),

                "interval":
                    self.spin_interval.value(),

                "language":
                    self.combo_lang.currentData(),

                "autostart":
                    is_autostart
            })

            # ------------------------------------------------
            # Hotkeys
            # ------------------------------------------------

            self.config["hotkeys"].update({

                "close":
                    self.hotkey_close
                    .keySequence()
                    .toString(),

                "hide":
                    self.hotkey_hide
                    .keySequence()
                    .toString(),

                "settings":
                    self.hotkey_settings
                    .keySequence()
                    .toString()
            })

            # ------------------------------------------------
            # ذخیره فایل
            # ------------------------------------------------

            CONFIG_FILE.parent.mkdir(
                parents=True,
                exist_ok=True
            )

            with open(
                CONFIG_FILE,
                "w",
                encoding="utf-8"
            ) as f:

                json.dump(
                    self.config,
                    f,
                    ensure_ascii=False,
                    indent=2
                )

            # ------------------------------------------------
            # نمایش موفقیت
            # ------------------------------------------------

            self.btn_save.setText("✅ ذخیره شد")

            self.btn_save.setStyleSheet(
                "background: rgba(52,211,153,40); "
                "color: #34d399; "
                "font-weight: bold; "
                "padding: 10px;"
            )

            # ------------------------------------------------
            # اطلاع به Widget اصلی
            # ------------------------------------------------

            self.settings_saved.emit()

            return True

        except Exception as e:

            QMessageBox.critical(
                self,
                "خطا",
                f"ذخیره نشد:\n{e}"
            )

            return False

    # ========================================================
    # Build UI
    # ========================================================

    def build_ui(self):

        main = QHBoxLayout(self)
        main.setContentsMargins(20, 20, 20, 20)

        # ----------------------------------------------------
        # Sidebar
        # ----------------------------------------------------

        sidebar = QVBoxLayout()

        title = QLabel("تنظیمات")

        title.setFont(
            QFont(
                "Noto Sans",
                18,
                QFont.Bold
            )
        )

        sidebar.addWidget(title)
        sidebar.addSpacing(20)

        self.btn_markets = QPushButton(
            "▦    بازارها و ارزها"
        )

        self.btn_appearance = QPushButton(
            "◐    ظاهر و شخصی‌سازی"
        )

        self.btn_hotkeys = QPushButton(
            "⌨    کلیدهای میانبر"
        )

        self.btn_about = QPushButton(
            "ⓘ    درباره برنامه"
        )

        for btn in [
            self.btn_markets,
            self.btn_appearance,
            self.btn_hotkeys,
            self.btn_about
        ]:

            btn.setCursor(
                Qt.PointingHandCursor
            )

            sidebar.addWidget(btn)

        sidebar.addStretch()

        # ----------------------------------------------------
        # Save button
        # ----------------------------------------------------

        self.btn_save = QPushButton(
            "✓    ذخیره تنظیمات"
        )

        self.btn_save.setStyleSheet(
            "background: rgba(56,189,248,30); "
            "color: #38bdf8;"
        )

        self.btn_save.clicked.connect(
            self.save_config
        )

        sidebar.addWidget(self.btn_save)

        # ----------------------------------------------------
        # Close
        # ----------------------------------------------------

        btn_close = QPushButton(
            "✕    خروج"
        )

        btn_close.setStyleSheet(
            "color: #fb7185;"
        )

        btn_close.clicked.connect(
            self.close
        )

        sidebar.addWidget(btn_close)

        main.addLayout(
            sidebar,
            1
        )

        # ----------------------------------------------------
        # Stacked pages
        # ----------------------------------------------------

        self.stacked = QStackedWidget()

        main.addWidget(
            self.stacked,
            3
        )

        # ====================================================
        # Markets page
        # ====================================================

        page_markets = QWidget()

        layout_markets = QVBoxLayout(
            page_markets
        )

        layout_markets.setSpacing(10)

        h_lists = QHBoxLayout()

        # ----------------------------------------------------
        # Available markets
        # ----------------------------------------------------

        v_avail = QVBoxLayout()

        v_avail.addWidget(
            QLabel("بازارهای آماده:")
        )

        self.tree_avail = QTreeWidget()

        self.tree_avail.setHeaderHidden(
            True
        )

        btn_add = QPushButton(
            "اضافه به لیست ⮜"
        )

        btn_add.setStyleSheet(
            "background: rgba(56,189,248,20); "
            "color: #38bdf8;"
        )

        btn_add.clicked.connect(
            self.add_market
        )

        v_avail.addWidget(
            self.tree_avail
        )

        v_avail.addWidget(
            btn_add
        )

        # ----------------------------------------------------
        # Selected markets
        # ----------------------------------------------------

        v_sel = QVBoxLayout()

        v_sel.addWidget(
            QLabel(
                "لیست شما (جابجایی با ماوس):"
            )
        )

        self.list_sel = QListWidget()

        self.list_sel.setDragDropMode(
            QAbstractItemView.InternalMove
        )

        btn_rem = QPushButton(
            "حذف از لیست 🗑"
        )

        btn_rem.setStyleSheet(
            "background: rgba(251,113,133,20); "
            "color: #fb7185;"
        )

        btn_rem.clicked.connect(
            self.remove_market
        )

        v_sel.addWidget(
            self.list_sel
        )

        v_sel.addWidget(
            btn_rem
        )

        h_lists.addLayout(
            v_avail
        )

        h_lists.addLayout(
            v_sel
        )

        layout_markets.addLayout(
            h_lists
        )

        # ----------------------------------------------------
        # Custom market
        # ----------------------------------------------------

        custom_layout = QHBoxLayout()

        self.inp_api_key = QLineEdit()

        self.inp_api_key.setPlaceholderText(
            "کلید (مثل usd_buy)"
        )

        self.inp_api_name = QLineEdit()

        self.inp_api_name.setPlaceholderText(
            "نام نمایشی"
        )

        btn_custom = QPushButton(
            "+ افزودن"
        )

        btn_custom.setStyleSheet(
            "background: rgba(52,211,153,20); "
            "color: #34d399;"
        )

        btn_custom.clicked.connect(
            self.add_custom_market
        )

        custom_layout.addWidget(
            self.inp_api_key
        )

        custom_layout.addWidget(
            self.inp_api_name
        )

        custom_layout.addWidget(
            btn_custom
        )

        layout_markets.addLayout(
            custom_layout
        )

        self.stacked.addWidget(
            page_markets
        )

        # ====================================================
        # Appearance page
        # ====================================================

        page_app = QWidget()

        layout_app = QVBoxLayout(
            page_app
        )

        layout_app.setSpacing(12)

        # ----------------------------------------------------
        # Opacity
        # ----------------------------------------------------

        row_op = QHBoxLayout()

        self.slider_opacity = QSlider(
            Qt.Horizontal
        )

        self.slider_opacity.setRange(
            30,
            255
        )

        self.slider_opacity.setValue(
            self.config["appearance"].get(
                "opacity",
                210
            )
        )

        row_op.addWidget(
            QLabel("شفافیت ویجت:")
        )

        row_op.addWidget(
            self.slider_opacity
        )

        layout_app.addLayout(
            row_op
        )

        # ----------------------------------------------------
        # Visible rows
        # ----------------------------------------------------

        row_rows = QHBoxLayout()

        self.spin_rows = QSpinBox()

        self.spin_rows.setRange(
            1,
            20
        )

        self.spin_rows.setValue(
            self.config["appearance"].get(
                "rows_visible",
                6
            )
        )

        row_rows.addWidget(
            QLabel("تعداد ردیف نمایشی:")
        )

        row_rows.addWidget(
            self.spin_rows
        )

        row_rows.addStretch()

        layout_app.addLayout(
            row_rows
        )

        # ----------------------------------------------------
        # Update interval
        # ----------------------------------------------------

        row_interval = QHBoxLayout()

        self.spin_interval = QSpinBox()

        self.spin_interval.setRange(
            10,
            3600
        )

        self.spin_interval.setValue(
            self.config["appearance"].get(
                "interval",
                120
            )
        )

        row_interval.addWidget(
            QLabel(
                "آپدیت قیمت‌ها (ثانیه):"
            )
        )

        row_interval.addWidget(
            self.spin_interval
        )

        row_interval.addStretch()

        layout_app.addLayout(
            row_interval
        )

        # ----------------------------------------------------
        # Font size
        # ----------------------------------------------------

        row_font_size = QHBoxLayout()

        self.spin_font = QSpinBox()

        self.spin_font.setRange(
            10,
            26
        )

        self.spin_font.setValue(
            self.config["appearance"].get(
                "font_size",
                13
            )
        )

        row_font_size.addWidget(
            QLabel("اندازه متن:")
        )

        row_font_size.addWidget(
            self.spin_font
        )

        row_font_size.addStretch()

        layout_app.addLayout(
            row_font_size
        )

        # ----------------------------------------------------
        # Font family
        # ----------------------------------------------------

        row_font_family = QHBoxLayout()

        self.combo_font = QFontComboBox()

        self.combo_font.setCurrentFont(
            QFont(
                self.config["appearance"].get(
                    "font_family",
                    "Noto Sans"
                )
            )
        )

        row_font_family.addWidget(
            QLabel("نوع فونت:")
        )

        row_font_family.addWidget(
            self.combo_font
        )

        layout_app.addLayout(
            row_font_family
        )

        # ----------------------------------------------------
        # Language
        # ----------------------------------------------------

        row_lang = QHBoxLayout()

        self.combo_lang = QComboBox()

        self.combo_lang.addItem(
            "فارسی (Persian)",
            "fa"
        )

        self.combo_lang.addItem(
            "English",
            "en"
        )

        idx = self.combo_lang.findData(
            self.config["appearance"].get(
                "language",
                "fa"
            )
        )

        self.combo_lang.setCurrentIndex(
            idx if idx >= 0 else 0
        )

        row_lang.addWidget(
            QLabel("زبان ویجت:")
        )

        row_lang.addWidget(
            self.combo_lang
        )

        layout_app.addLayout(
            row_lang
        )

        # ----------------------------------------------------
        # Autostart
        # ----------------------------------------------------

        self.chk_autostart = QCheckBox(
            "اجرای خودکار هنگام روشن شدن سیستم (Autostart)"
        )

        self.chk_autostart.setChecked(
            self.config["appearance"].get(
                "autostart",
                False
            )
        )

        layout_app.addWidget(
            self.chk_autostart
        )

        layout_app.addStretch()

        self.stacked.addWidget(
            page_app
        )

        # ====================================================
        # Hotkeys page
        # ====================================================

        page_hotkeys = QWidget()

        layout_keys = QVBoxLayout(
            page_hotkeys
        )

        # ----------------------------------------------------
        # Close
        # ----------------------------------------------------

        layout_keys.addWidget(
            QLabel("بستن کامل برنامه:")
        )

        self.hotkey_close = QKeySequenceEdit(
            QKeySequence(
                self.config["hotkeys"].get(
                    "close",
                    "Ctrl+Q"
                )
            )
        )

        layout_keys.addWidget(
            self.hotkey_close
        )

        layout_keys.addSpacing(15)

        # ----------------------------------------------------
        # Hide / Show
        # ----------------------------------------------------

        layout_keys.addWidget(
            QLabel(
                "مخفی / ظاهر کردن ویجت:"
            )
        )

        self.hotkey_hide = QKeySequenceEdit(
            QKeySequence(
                self.config["hotkeys"].get(
                    "hide",
                    "Ctrl+H"
                )
            )
        )

        layout_keys.addWidget(
            self.hotkey_hide
        )

        layout_keys.addSpacing(15)

        # ----------------------------------------------------
        # Settings
        # ----------------------------------------------------

        layout_keys.addWidget(
            QLabel(
                "باز کردن پنل تنظیمات:"
            )
        )

        self.hotkey_settings = QKeySequenceEdit(
            QKeySequence(
                self.config["hotkeys"].get(
                    "settings",
                    "Ctrl+Alt+S"
                )
            )
        )

        layout_keys.addWidget(
            self.hotkey_settings
        )

        layout_keys.addStretch()

        self.stacked.addWidget(
            page_hotkeys
        )

        # ====================================================
        # About page
        # ====================================================

        page_about = QWidget()
        layout_about = QVBoxLayout(page_about)
        layout_about.setSpacing(15)

        title_about = QLabel("LiveFlow Widget")
        title_about.setFont(QFont("Noto Sans", 24, QFont.Bold))
        layout_about.addWidget(title_about)

        version_file = BASE_DIR / "VERSION"; version = version_file.read_text(encoding="utf-8").strip() if version_file.exists() else "نامشخص"; version_about = QLabel(f"نسخه {version}")
        version_about.setStyleSheet("color: #38bdf8; font-size: 15px;")
        layout_about.addWidget(version_about)

        developer_about = QLabel("توسعه‌دهنده: Reza Moghani")
        developer_about.setStyleSheet("color: #cbd5e1; font-size: 14px;")
        layout_about.addWidget(developer_about)

        desc_about = QLabel(
            "ویجت نمایش زنده قیمت بازارها، ارزها، طلا و ارزهای دیجیتال."
        )
        desc_about.setWordWrap(True)
        desc_about.setStyleSheet("color: #cbd5e1; font-size: 14px;")
        layout_about.addWidget(desc_about)

        github_about = QLabel(
            '<a href="https://github.com/Reeeza2005/LiveFlow-Widget">'
            'صفحه پروژه در GitHub</a>'
        )
        github_about.setOpenExternalLinks(True)
        github_about.setStyleSheet("color: #38bdf8; font-size: 14px;")
        layout_about.addWidget(github_about)

        self.btn_update = QPushButton("🔄    بررسی بروزرسانی")
        self.btn_update.setStyleSheet("background: rgba(56,189,248,30); color: #38bdf8;")
        self.btn_update.clicked.connect(self.check_for_updates)
        layout_about.addWidget(self.btn_update)

        self.btn_install_update = QPushButton("⬇️    بروزرسانی برنامه")
        self.btn_install_update.setEnabled(False)
        self.btn_install_update.clicked.connect(self.install_update)
        self.btn_install_update.setStyleSheet("background: rgba(52,211,153,30); color: #34d399;")
        layout_about.addWidget(self.btn_install_update)

        self.update_status = QLabel("")
        self.update_status.setWordWrap(True)
        self.update_status.setStyleSheet("color: #cbd5e1; font-size: 13px;")
        layout_about.addWidget(self.update_status)

        layout_about.addStretch()

        self.stacked.addWidget(page_about)


        # ====================================================
        # Navigation
        # ====================================================

        self.btn_markets.clicked.connect(
            lambda:
            self.switch_page(
                0,
                self.btn_markets
            )
        )

        self.btn_appearance.clicked.connect(
            lambda:
            self.switch_page(
                1,
                self.btn_appearance
            )
        )

        self.btn_hotkeys.clicked.connect(
            lambda:
            self.switch_page(
                2,
                self.btn_hotkeys
            )
        )

        self.btn_about.clicked.connect(
            lambda:
            self.switch_page(
                3,
                self.btn_about
            )
        )

        self.switch_page(
            0,
            self.btn_markets
        )

    # ========================================================
    # Check for Updates
    # ========================================================

    def check_for_updates(self):
        self.btn_install_update.setEnabled(False)
        try:
            version_file = BASE_DIR / "VERSION"
            current = version_file.read_text(encoding="utf-8").strip()

            url = "https://api.github.com/repos/Reeeza2005/LiveFlow-Widget/releases/latest"
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "LiveFlow-Widget"}
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.load(response)

            latest = str(data.get("tag_name", "")).lstrip("v")

            if not latest:
                self.update_status.setText("نتوانستم نسخه جدید را پیدا کنم.")
                return

            def version_tuple(v):
                return tuple(int(x) for x in v.split(".")[:3])

            if version_tuple(latest) > version_tuple(current):
                self.update_status.setText(
                    f"بروزرسانی نسخه {latest} در دسترس است (نسخه فعلی: {current})"
                )
                self.btn_install_update.setEnabled(True)
            else:
                self.update_status.setText(
                    f"برنامه شما به‌روز است — نسخه {current}"
                )

        except Exception as e:
            self.update_status.setText(
                f"خطا در بررسی بروزرسانی: {e}"
            )

    def install_update(self):
        import platform
        import tempfile
        from PySide6.QtWidgets import QProgressDialog

        try:
            current_app = os.environ.get("APPIMAGE")
            if not current_app:
                self.update_status.setText("بروزرسانی خودکار فقط برای نسخه AppImage فعال است.")
                return
            version_file = BASE_DIR / "VERSION"
            current = version_file.read_text(encoding="utf-8").strip()

            url = "https://api.github.com/repos/Reeeza2005/LiveFlow-Widget/releases/latest"
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "LiveFlow-Widget"}
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.load(response)

            latest = str(data.get("tag_name", "")).lstrip("v")
            assets = data.get("assets", [])

            def version_tuple(v):
                return tuple(int(x) for x in v.split(".")[:3])

            if not latest or version_tuple(latest) <= version_tuple(current):
                self.update_status.setText(
                    f"برنامه شما به‌روز است — نسخه {current}"
                )
                self.btn_install_update.setEnabled(False)
                return

            system = platform.system()
            machine = platform.machine().lower()
            asset_name = None

            if system == "Linux":
                if machine in ("x86_64", "amd64"):
                    asset_name = f"LiveFlow-Widget-{latest}-x86_64.AppImage"
            elif system == "Windows":
                asset_name = f"LiveFlow-Widget-{latest}-Windows.exe"
            elif system == "Darwin":
                asset_name = f"LiveFlow-Widget-{latest}-macOS.dmg"

            asset = next(
                (item for item in assets if item.get("name") == asset_name),
                None
            )

            if not asset:
                self.update_status.setText(
                    f"فایل بروزرسانی مناسب برای {system} پیدا نشد."
                )
                return

            download_url = asset.get("browser_download_url")
            total = int(asset.get("size", 0))

            temp_dir = Path(tempfile.mkdtemp(prefix="liveflow-update-"))
            download_path = temp_dir / asset_name

            self.update_status.setText(
                f"در حال دانلود نسخه {latest} ..."
            )

            progress = UpdateProgressDialog(self)
            progress.show()
            QApplication.processEvents()

            req = urllib.request.Request(
                download_url,
                headers={"User-Agent": "LiveFlow-Widget"}
            )

            downloaded = 0
            with urllib.request.urlopen(req, timeout=30) as response, open(download_path, "wb") as output:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    output.write(chunk)
                    downloaded += len(chunk)

                    if total > 0:
                        percent = min(100, int(downloaded * 100 / total))
                        progress.progress.setValue(percent)
                        QApplication.processEvents()

                    if progress.cancelled:
                        output.close()
                        download_path.unlink(missing_ok=True)
                        temp_dir.rmdir()
                        progress.close()
                        self.update_status.setText("بروزرسانی لغو شد.")
                        return

            progress.progress.setValue(100)
            progress.close()

            self.update_status.setText(
                f"دانلود نسخه {latest} با موفقیت انجام شد."
            )
            self.btn_install_update.setEnabled(False)

            self._downloaded_update_path = download_path
            self._update_temp_dir = temp_dir
            self._update_latest_version = latest

            appdir = os.environ.get("APPDIR")
            if not appdir:
                self.update_status.setText("مسیر AppImage پیدا نشد.")
                return

            updater = Path(appdir) / "usr" / "bin" / "liveflow-updater"
            if not updater.exists():
                self.update_status.setText("فایل بروزرسانی داخل برنامه پیدا نشد.")
                return

            self.update_status.setText("در حال نصب بروزرسانی و راه‌اندازی مجدد...")
            QApplication.processEvents()

            updater_copy = Path(tempfile.mkdtemp(prefix="liveflow-updater-")) / "liveflow-updater"
            shutil.copy2(updater, updater_copy)
            os.chmod(updater_copy, 0o755)

            subprocess.Popen([
                str(updater_copy),
                current_app,
                str(download_path),
                str(temp_dir),
            ], start_new_session=True)

            QApplication.quit()

        except Exception as e:
            self.update_status.setText(
                f"خطا در دانلود بروزرسانی: {e}"
            )

    # ========================================================
    # Populate Markets
    # ========================================================

    def populate_markets(self):

        for cat, items in ALL_MARKETS.items():

            parent = QTreeWidgetItem(
                self.tree_avail
            )

            parent.setText(
                0,
                cat
            )

            for key, name in items:

                child = QTreeWidgetItem(
                    parent
                )

                child.setText(
                    0,
                    name
                )

                child.setData(
                    0,
                    Qt.UserRole,
                    key
                )

        self.tree_avail.expandAll()

        self.list_sel.clear()

        for m in self.config.get(
            "markets",
            []
        ):

            if m.get("enabled"):

                item = QListWidgetItem(
                    m["name"]
                )

                item.setData(
                    Qt.UserRole,
                    m["key"]
                )

                self.list_sel.addItem(
                    item
                )

    # ========================================================
    # Add Market
    # ========================================================

    def add_market(self):

        selected = (
            self.tree_avail.selectedItems()
        )

        if (
            not selected
            or selected[0].childCount() > 0
        ):
            return

        key = selected[0].data(
            0,
            Qt.UserRole
        )

        name = selected[0].text(0)

        for i in range(
            self.list_sel.count()
        ):

            if (
                self.list_sel.item(i)
                .data(Qt.UserRole)
                == key
            ):
                return

        item = QListWidgetItem(
            name
        )

        item.setData(
            Qt.UserRole,
            key
        )

        self.list_sel.addItem(
            item
        )

    # ========================================================
    # Add Custom Market
    # ========================================================

    def add_custom_market(self):

        key = (
            self.inp_api_key
            .text()
            .strip()
        )

        name = (
            self.inp_api_name
            .text()
            .strip()
        )

        if key and name:

            item = QListWidgetItem(
                f"{name} (سفارشی)"
            )

            item.setData(
                Qt.UserRole,
                key
            )

            self.list_sel.addItem(
                item
            )

            self.inp_api_key.clear()
            self.inp_api_name.clear()

    # ========================================================
    # Remove Market
    # ========================================================

    def remove_market(self):

        for item in self.list_sel.selectedItems():

            self.list_sel.takeItem(
                self.list_sel.row(item)
            )

    # ========================================================
    # Switch Page
    # ========================================================

    def switch_page(
        self,
        index,
        active_btn
    ):

        self.stacked.setCurrentIndex(
            index
        )

        for btn in [
            self.btn_markets,
            self.btn_appearance,
            self.btn_hotkeys,
            self.btn_about
        ]:

            btn.setStyleSheet(
                "background: transparent; "
                "color: #cbd5e1;"
            )

        active_btn.setStyleSheet(
            "background: rgba(255,255,255,15); "
            "color: #fff;"
        )

    # ========================================================
    # Window Drag
    # ========================================================

    def mousePressEvent(self, event):

        if event.button() == Qt.LeftButton:

            self.drag_pos = (
                event.globalPosition().toPoint()
                - self.frameGeometry().topLeft()
            )

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):

        if (
            event.buttons() & Qt.LeftButton
            and hasattr(self, "drag_pos")
        ):

            self.move(
                event.globalPosition().toPoint()
                - self.drag_pos
            )

        super().mouseMoveEvent(event)

    # ========================================================
    # Paint
    # ========================================================

    def paintEvent(self, event):

        painter = QPainter(self)

        painter.setRenderHint(
            QPainter.Antialiasing
        )

        painter.setBrush(
            QColor(
                15,
                23,
                42,
                240
            )
        )

        painter.setPen(
            Qt.NoPen
        )

        painter.drawRoundedRect(
            0,
            0,
            self.width(),
            self.height(),
            20,
            20
        )
