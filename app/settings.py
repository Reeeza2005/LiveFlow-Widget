import sys
import json
import webbrowser
from pathlib import Path
import requests

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor, QPainter, QFont, QKeySequence
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QStackedWidget,
    QSlider, QSpinBox, QFontComboBox, QTreeWidget, QTreeWidgetItem,
    QListWidget, QListWidgetItem, QAbstractItemView,
    QKeySequenceEdit, QMessageBox, QLineEdit, QComboBox, QCheckBox
)

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = BASE_DIR / "config" / "markets.json"
AUTOSTART_DIR = Path.home() / ".config" / "autostart"
DESKTOP_FILE = AUTOSTART_DIR / "liveflow-widget.desktop"

ALL_MARKETS = {
    "طلا و سکه": [("sekee", "سکه امامی"), ("nim", "نیم سکه"), ("rob", "ربع سکه"), ("geram18", "گرم ۱۸ عیار"), ("geram24", "گرم ۲۴ عیار"), ("ons", "انس جهانی طلا")],
    "ارزهای خارجی": [("price_dollar_rl", "دلار آمریکا"), ("price_eur", "یورو"), ("price_gbp", "پوند انگلیس"), ("price_aed", "درهم امارات"), ("price_try", "لیر ترکیه"), ("price_cny", "یوان چین")],
    "ارزهای دیجیتال": [("crypto-tether", "تتر"), ("tether", "تتر (لینک دوم)"), ("crypto-bitcoin", "بیت‌کوین"), ("crypto-ethereum", "اتریوم"), ("crypto-bnb", "بایننس کوین"), ("crypto-solana", "سولانا")],
    "بورس و انرژی": [("oil_brent", "نفت برنت"), ("gc30", "شاخص بورس"), ("silver", "انس نقره")]
}

class UpdateCheckerWorker(QThread):
    update_found = Signal(str, str)  # latest_version, release_url
    no_update = Signal()
    error_occurred = Signal()

    def __init__(self, current_version="1.0.0", automatic=True):
        super().__init__()
        self.current_version = current_version
        self.automatic = automatic

    def run(self):
        url = "https://api.github.com/repos/Reeeza2005/LiveFlow-Widget/releases/latest"
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                latest_version = data.get("tag_name", "").lstrip("v")
                release_url = data.get("html_url", "https://github.com/Reeeza2005/LiveFlow-Widget/releases")
                
                if latest_version and latest_version != self.current_version:
                    self.update_found.emit(latest_version, release_url)
                elif not self.automatic:
                    self.no_update.emit()
            elif not self.automatic:
                self.error_occurred.emit()
        except Exception:
            if not self.automatic:
                self.error_occurred.emit()

class SettingsWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(860, 660)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.config = {
            "markets": [],
            "appearance": {"opacity": 210, "font_size": 13, "font_family": "Noto Sans", "rows_visible": 6, "interval": 120, "language": "fa", "autostart": False},
            "hotkeys": {"close": "Ctrl+Q", "hide": "Ctrl+H", "settings": "Ctrl+Alt+S"}
        }
        self.load_config()
        self.build_ui()
        self.populate_markets()
        self.apply_live_preview()

        # بررسی خودکار به‌روزرسانی در پس‌زمینه هنگام اجرای تنظیمات
        self.auto_update_worker = UpdateCheckerWorker(current_version="1.0.0", automatic=True)
        self.auto_update_worker.update_found.connect(self.show_update_dialog)
        self.auto_update_worker.start()

    def load_config(self):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                self.config.update(json.load(f))
        except Exception:
            pass

    def apply_live_preview(self):
        font_name = self.combo_font.currentFont().family()
        font_size = self.spin_font.value()

        self.setStyleSheet(f"""
            QWidget {{ color: #f8fafc; font-family: '{font_name}'; }}
            QPushButton {{ border: none; border-radius: 8px; padding: 10px; color: #cbd5e1; background: transparent; font-size: 13px; }}
            QPushButton:hover {{ background: rgba(255,255,255,15); color: #fff; }}
            
            QLineEdit, QSpinBox, QFontComboBox {{ 
                background: rgba(15, 23, 42, 200); color: #fff; border: 1px solid rgba(255,255,255,20); 
                border-radius: 6px; padding: 6px; font-size: {font_size}px; 
            }}
            
            QComboBox {{
                background: rgba(15, 23, 42, 200); color: #fff; border: 1px solid rgba(255,255,255,20); 
                border-radius: 6px; padding: 6px; font-size: {font_size}px;
            }}
            QComboBox QAbstractItemView {{
                background: rgb(30, 41, 59); color: #fff; border: 1px solid rgba(255,255,255,20); 
                selection-background-color: #38bdf8;
            }}
            
            QTreeWidget, QListWidget {{ 
                background: rgba(15,23,42,150); border: 1px solid rgba(255,255,255,10); 
                border-radius: 8px; padding: 5px; font-size: {font_size}px; outline: none; 
            }}
            QTreeWidget::item, QListWidget::item {{ padding: 6px; border-radius: 4px; }}
            QTreeWidget::item:selected, QListWidget::item:selected {{ background: rgba(56,189,248,40); color: #fff; }}
            
            QSlider::groove:horizontal {{ background: #475569; height: 6px; border-radius: 3px; }}
            QSlider::handle:horizontal {{ background: #38bdf8; width: 14px; margin: -4px 0; border-radius: 7px; }}
            
            QKeySequenceEdit {{ background: rgba(15, 23, 42, 200); color: #38bdf8; border-radius: 6px; padding: 6px; }}
            QCheckBox {{ spacing: 8px; font-size: 13px; }}
            QCheckBox::indicator {{ width: 18px; height: 18px; border-radius: 4px; border: 1px solid rgba(255,255,255,30); background: rgba(15, 23, 42, 200); }}
            QCheckBox::indicator:checked {{ background: #38bdf8; border-color: #38bdf8; }}
        """)
        self.update()

    def handle_autostart(self, enable):
        try:
            if enable:
                AUTOSTART_DIR.mkdir(parents=True, exist_ok=True)
                python_path = sys.executable
                script_path = BASE_DIR / "app" / "widget.py"
                desktop_content = f"""[Desktop Entry]
Type=Application
Name=LiveFlow Widget
Exec={python_path} {script_path}
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
"""
                with open(DESKTOP_FILE, "w", encoding="utf-8") as f:
                    f.write(desktop_content)
            else:
                if DESKTOP_FILE.exists():
                    DESKTOP_FILE.unlink()
        except Exception as e:
            print(f"Autostart error: {e}")

    def save_config(self):
        try:
            saved_markets = [{"key": self.list_sel.item(i).data(Qt.UserRole), "name": self.list_sel.item(i).text(), "enabled": True} for i in range(self.list_sel.count())]
            self.config["markets"] = saved_markets
            
            is_autostart = self.chk_autostart.isChecked()
            self.handle_autostart(is_autostart)

            self.config["appearance"].update({
                "opacity": self.slider_opacity.value(),
                "font_size": self.spin_font.value(),
                "font_family": self.combo_font.currentFont().family(),
                "rows_visible": self.spin_rows.value(),
                "interval": self.spin_interval.value(),
                "language": self.combo_lang.currentData(),
                "autostart": is_autostart
            })
            self.config["hotkeys"].update({
                "close": self.hotkey_close.keySequence().toString(),
                "hide": self.hotkey_hide.keySequence().toString(),
                "settings": self.hotkey_settings.keySequence().toString()
            })

            CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            
            self.btn_save.setText("✅ ذخیره شد")
            self.btn_save.setStyleSheet("background: rgba(52,211,153,40); color: #34d399; font-weight: bold; padding: 10px;")
            return True
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"ذخیره نشد:\n{e}")
            return False

    def build_ui(self):
        main = QHBoxLayout(self)
        main.setContentsMargins(20, 20, 20, 20)
        
        # سایدبار
        sidebar = QVBoxLayout()
        title = QLabel("تنظیمات")
        title.setFont(QFont("Noto Sans", 18, QFont.Bold))
        sidebar.addWidget(title)
        sidebar.addSpacing(20)

        self.btn_markets = QPushButton("▦    بازارها و ارزها")
        self.btn_appearance = QPushButton("◐    ظاهر و شخصی‌سازی")
        self.btn_hotkeys = QPushButton("⌨    کلیدهای میانبر")
        
        for btn in [self.btn_markets, self.btn_appearance, self.btn_hotkeys]:
            btn.setCursor(Qt.PointingHandCursor)
            sidebar.addWidget(btn)
        
        sidebar.addStretch()

        # دکمه بررسی به‌روزرسانی دستی
        self.btn_update = QPushButton("🔄    بررسی به‌روزرسانی")
        self.btn_update.setStyleSheet("background: rgba(56,189,248,15); color: #38bdf8;")
        self.btn_update.clicked.connect(self.manual_check_updates)
        sidebar.addWidget(self.btn_update)

        self.btn_save = QPushButton("✓    ذخیره تنظیمات")
        self.btn_save.setStyleSheet("background: rgba(56,189,248,30); color: #38bdf8;")
        self.btn_save.clicked.connect(self.save_config)
        sidebar.addWidget(self.btn_save)

        btn_close = QPushButton("✕    خروج")
        btn_close.setStyleSheet("color: #fb7185;")
        btn_close.clicked.connect(QApplication.quit)
        sidebar.addWidget(btn_close)
        
        main.addLayout(sidebar, 1)

        self.stacked = QStackedWidget()
        main.addWidget(self.stacked, 3)

        # ====== تب بازارها ======
        page_markets = QWidget()
        layout_markets = QVBoxLayout(page_markets)
        layout_markets.setSpacing(10)
        
        h_lists = QHBoxLayout()
        v_avail = QVBoxLayout()
        v_avail.addWidget(QLabel("بازارهای آماده:"))
        self.tree_avail = QTreeWidget()
        self.tree_avail.setHeaderHidden(True)
        btn_add = QPushButton("اضافه به لیست ⮜")
        btn_add.setStyleSheet("background: rgba(56,189,248,20); color: #38bdf8;")
        btn_add.clicked.connect(self.add_market)
        v_avail.addWidget(self.tree_avail)
        v_avail.addWidget(btn_add)

        v_sel = QVBoxLayout()
        v_sel.addWidget(QLabel("لیست شما (جابجایی با ماوس):"))
        self.list_sel = QListWidget()
        self.list_sel.setDragDropMode(QAbstractItemView.InternalMove)
        btn_rem = QPushButton("حذف از لیست 🗑")
        btn_rem.setStyleSheet("background: rgba(251,113,133,20); color: #fb7185;")
        btn_rem.clicked.connect(self.remove_market)
        v_sel.addWidget(self.list_sel)
        v_sel.addWidget(btn_rem)

        h_lists.addLayout(v_avail)
        h_lists.addLayout(v_sel)
        layout_markets.addLayout(h_lists)

        custom_layout = QHBoxLayout()
        self.inp_api_key = QLineEdit()
        self.inp_api_key.setPlaceholderText("کلید (مثل usd_buy)")
        self.inp_api_name = QLineEdit()
        self.inp_api_name.setPlaceholderText("نام نمایشی")
        btn_custom = QPushButton("+ افزودن")
        btn_custom.setStyleSheet("background: rgba(52,211,153,20); color: #34d399;")
        btn_custom.clicked.connect(self.add_custom_market)
        custom_layout.addWidget(self.inp_api_key)
        custom_layout.addWidget(self.inp_api_name)
        custom_layout.addWidget(btn_custom)
        layout_markets.addLayout(custom_layout)
        self.stacked.addWidget(page_markets)

        # ====== تب ظاهر ======
        page_app = QWidget()
        layout_app = QVBoxLayout(page_app)
        layout_app.setSpacing(12)
        
        row_op = QHBoxLayout()
        self.slider_opacity = QSlider(Qt.Horizontal)
        self.slider_opacity.setRange(30, 255)
        self.slider_opacity.setValue(self.config["appearance"].get("opacity", 210))
        row_op.addWidget(QLabel("شفافیت ویجت:"))
        row_op.addWidget(self.slider_opacity)
        layout_app.addLayout(row_op)

        row_rows = QHBoxLayout()
        self.spin_rows = QSpinBox()
        self.spin_rows.setRange(1, 20)
        self.spin_rows.setValue(self.config["appearance"].get("rows_visible", 6))
        row_rows.addWidget(QLabel("تعداد ردیف نمایشی:"))
        row_rows.addWidget(self.spin_rows)
        row_rows.addStretch()
        layout_app.addLayout(row_rows)

        row_interval = QHBoxLayout()
        self.spin_interval = QSpinBox()
        self.spin_interval.setRange(10, 3600)
        self.spin_interval.setValue(self.config["appearance"].get("interval", 120))
        row_interval.addWidget(QLabel("آپدیت قیمت‌ها (ثانیه):"))
        row_interval.addWidget(self.spin_interval)
        row_interval.addStretch()
        layout_app.addLayout(row_interval)
        
        row_font_size = QHBoxLayout()
        self.spin_font = QSpinBox()
        self.spin_font.setRange(10, 26)
        self.spin_font.setValue(self.config["appearance"].get("font_size", 13))
        row_font_size.addWidget(QLabel("اندازه متن:"))
        row_font_size.addWidget(self.spin_font)
        row_font_size.addStretch()
        layout_app.addLayout(row_font_size)

        row_font_family = QHBoxLayout()
        self.combo_font = QFontComboBox()
        self.combo_font.setCurrentFont(QFont(self.config["appearance"].get("font_family", "Noto Sans")))
        row_font_family.addWidget(QLabel("نوع فونت:"))
        row_font_family.addWidget(self.combo_font)
        layout_app.addLayout(row_font_family)

        row_lang = QHBoxLayout()
        self.combo_lang = QComboBox()
        self.combo_lang.addItem("فارسی (Persian)", "fa")
        self.combo_lang.addItem("English", "en")
        idx = self.combo_lang.findData(self.config["appearance"].get("language", "fa"))
        self.combo_lang.setCurrentIndex(idx if idx >= 0 else 0)
        row_lang.addWidget(QLabel("زبان ویجت:"))
        row_lang.addWidget(self.combo_lang)
        layout_app.addLayout(row_lang)

        # چک‌باکس اجرای خودکار
        self.chk_autostart = QCheckBox("اجرای خودکار هنگام روشن شدن سیستم (Autostart)")
        self.chk_autostart.setChecked(self.config["appearance"].get("autostart", False))
        layout_app.addWidget(self.chk_autostart)

        layout_app.addStretch()
        self.stacked.addWidget(page_app)

        # ====== تب میانبرها ======
        page_hotkeys = QWidget()
        layout_keys = QVBoxLayout(page_hotkeys)
        
        layout_keys.addWidget(QLabel("بستن کامل برنامه:"))
        self.hotkey_close = QKeySequenceEdit(QKeySequence(self.config["hotkeys"].get("close", "Ctrl+Q")))
        layout_keys.addWidget(self.hotkey_close)
        
        layout_keys.addSpacing(15)
        
        layout_keys.addWidget(QLabel("مخفی / ظاهر کردن ویجت:"))
        self.hotkey_hide = QKeySequenceEdit(QKeySequence(self.config["hotkeys"].get("hide", "Ctrl+H")))
        layout_keys.addWidget(self.hotkey_hide)

        layout_keys.addSpacing(15)

        layout_keys.addWidget(QLabel("باز کردن پنل تنظیمات:"))
        self.hotkey_settings = QKeySequenceEdit(QKeySequence(self.config["hotkeys"].get("settings", "Ctrl+Alt+S")))
        layout_keys.addWidget(self.hotkey_settings)
        
        layout_keys.addStretch()
        self.stacked.addWidget(page_hotkeys)

        self.btn_markets.clicked.connect(lambda: self.switch_page(0, self.btn_markets))
        self.btn_appearance.clicked.connect(lambda: self.switch_page(1, self.btn_appearance))
        self.btn_hotkeys.clicked.connect(lambda: self.switch_page(2, self.btn_hotkeys))
        self.switch_page(0, self.btn_markets)

    def manual_check_updates(self):
        self.btn_update.setText("⏳ در حال بررسی...")
        self.btn_update.setEnabled(False)
        self.update_worker = UpdateCheckerWorker(current_version="1.0.0", automatic=False)
        self.update_worker.update_found.connect(self.on_update_found_manual)
        self.update_worker.no_update.connect(self.on_no_update_manual)
        self.update_worker.error_occurred.connect(self.on_error_manual)
        self.update_worker.start()

    def on_update_found_manual(self, latest_version, release_url):
        self.btn_update.setText("🔄    بررسی به‌روزرسانی")
        self.btn_update.setEnabled(True)
        self.show_update_dialog(latest_version, release_url)

    def on_no_update_manual(self):
        self.btn_update.setText("🔄    بررسی به‌روزرسانی")
        self.btn_update.setEnabled(True)
        QMessageBox.information(self, "بررسی به‌روزرسانی", "برنامه شما به‌روز است و از آخرین نسخه استفاده می‌کنید.")

    def on_error_manual(self):
        self.btn_update.setText("🔄    بررسی به‌روزرسانی")
        self.btn_update.setEnabled(True)
        QMessageBox.warning(self, "خطا", "خطا در اتصال به اینترنت برای بررسی به‌روزرسانی.")

    def show_update_dialog(self, latest_version, release_url):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("نسخه جدید موجود است")
        msg.setText(f"نسخه جدید ({latest_version}) برای LiveFlow Widget منتشر شده است!")
        msg.setInformativeText("آیا می‌خواهید برای دانلود به صفحه گیت‌هاب بروید؟")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        
        if msg.exec() == QMessageBox.Yes:
            webbrowser.open(release_url)

    def populate_markets(self):
        for cat, items in ALL_MARKETS.items():
            parent = QTreeWidgetItem(self.tree_avail)
            parent.setText(0, cat)
            for key, name in items:
                child = QTreeWidgetItem(parent)
                child.setText(0, name)
                child.setData(0, Qt.UserRole, key)
        self.tree_avail.expandAll()

        self.list_sel.clear()
        for m in self.config.get("markets", []):
            if m.get("enabled"):
                item = QListWidgetItem(m["name"])
                item.setData(Qt.UserRole, m["key"])
                self.list_sel.addItem(item)

    def add_market(self):
        selected = self.tree_avail.selectedItems()
        if not selected or selected[0].childCount() > 0: return
        key, name = selected[0].data(0, Qt.UserRole), selected[0].text(0)
        for i in range(self.list_sel.count()):
            if self.list_sel.item(i).data(Qt.UserRole) == key: return
        item = QListWidgetItem(name)
        item.setData(Qt.UserRole, key)
        self.list_sel.addItem(item)

    def add_custom_market(self):
        key = self.inp_api_key.text().strip()
        name = self.inp_api_name.text().strip()
        if key and name:
            item = QListWidgetItem(f"{name} (سفارشی)")
            item.setData(Qt.UserRole, key)
            self.list_sel.addItem(item)
            self.inp_api_key.clear()
            self.inp_api_name.clear()

    def remove_market(self):
        for item in self.list_sel.selectedItems():
            self.list_sel.takeItem(self.list_sel.row(item))

    def switch_page(self, index, active_btn):
        self.stacked.setCurrentIndex(index)
        for btn in [self.btn_markets, self.btn_appearance, self.btn_hotkeys]:
            btn.setStyleSheet("background: transparent; color: #cbd5e1;")
        active_btn.setStyleSheet("background: rgba(255,255,255,15); color: #fff;")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and hasattr(self, "drag_pos"):
            self.move(event.globalPosition().toPoint() - self.drag_pos)
        super().mouseMoveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(15, 23, 42, 240))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, 0, self.width(), self.height(), 20, 20)

if __name__ == "__main__":
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app = QApplication(sys.argv)
    w = SettingsWindow()
    w.show()
    sys.exit(app.exec())
