import sys
import json
import signal
import shutil
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QShortcut, QKeySequence
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QScrollArea
)
from app.tgju import get_prices

# مسیر پوشه نصب برنامه
BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = BASE_DIR / "config" / "markets.json"

# مسیر فایل تنظیمات در پوشه شخصی کاربر (برای رفع مشکل دسترسی در لینوکس)
CONFIG_FILE = Path.home() / ".liveflow_settings.json"

# اگر فایل تنظیمات کاربر وجود نداشت، فایل پیش‌فرض را کپی کن یا یک فایل جدید بساز
if not CONFIG_FILE.exists():
    try:
        if DEFAULT_CONFIG.exists():
            shutil.copy(DEFAULT_CONFIG, CONFIG_FILE)
        else:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump({"markets": [], "appearance": {}}, f)
    except Exception as e:
        print(f"Error creating config: {e}")

MARKET_SYMBOLS = {
    "sekee": "🪙", "nim": "🪙", "rob": "🪙", "geram18": "🟡", "geram24": "🟡", "ons": "🥇",
    "price_dollar_rl": "🇺🇸", "price_eur": "🇪🇺", "price_gbp": "🇬🇧", "price_aed": "🇦🇪", "price_try": "🇹🇷", "price_cny": "🇨🇳",
    "crypto-tether": "₮", "tether": "₮", "crypto-bitcoin": "₿", "crypto-ethereum": "Ξ", "crypto-bnb": "🟡", "crypto-solana": "🟣", "crypto-dogecoin": "🐕", "crypto-xrp": "✖",
    "oil_brent": "🛢️", "oil_wti": "🛢️", "gc30": "📈", "silver": "🥈"
}

def get_latin_unit(key, lang):
    if key in {"sekee", "nim", "rob", "geram18", "geram24", "price_dollar_rl", "price_eur", "price_gbp", "price_aed", "price_try", "price_cny", "crypto-tether", "tether"}:
        return "T" if lang == "en" else "تومان"
    elif "crypto" in key or key in {"ons", "silver", "oil_brent", "oil_wti"}:
        return "$"
    return ""

class WidgetWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.markets, self.prices, self.price_labels = [], {}, {}
        
        self.opacity = 210
        self.font_size = 13
        self.font_family = "Noto Sans"
        self.rows_visible = 6
        self.interval = 120
        self.language = "fa"
        self.hotkey_close = "Ctrl+Q"
        self.hotkey_hide = "Ctrl+H"

        self.load_config()
        self.setup_hotkeys()
        self.build_ui()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_prices)
        self.timer.start(self.interval * 1000)

    def load_config(self):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.markets = [m for m in data.get("markets", []) if m.get("enabled", False)]
            app_cfg = data.get("appearance", {})
            self.opacity = app_cfg.get("opacity", 210)
            self.font_size = app_cfg.get("font_size", 13)
            self.font_family = app_cfg.get("font_family", "Noto Sans")
            self.rows_visible = app_cfg.get("rows_visible", 6)
            self.interval = app_cfg.get("interval", 120)
            self.language = app_cfg.get("language", "fa")
            hot_cfg = data.get("hotkeys", {})
            self.hotkey_close = hot_cfg.get("close", "Ctrl+Q")
            self.hotkey_hide = hot_cfg.get("hide", "Ctrl+H")
        except Exception as e:
            print(f"Error loading config: {e}")
            self.markets = []

    def setup_hotkeys(self):
        QShortcut(QKeySequence(self.hotkey_close), self).activated.connect(QApplication.quit)
        QShortcut(QKeySequence(self.hotkey_hide), self).activated.connect(self.toggle_visibility)

    def toggle_visibility(self):
        self.hide() if self.isVisible() else self.show()

    def format_price(self, price, key):
        try:
            if isinstance(price, str):
                price = price.replace(',', '')
            
            value = float(price)
            if key in {"sekee", "nim", "rob", "geram18", "geram24", "price_dollar_rl", "price_eur", "price_gbp", "price_aed", "price_try", "price_cny", "crypto-tether", "tether"}:
                value = value / 10
            return f"{int(value):,}" if value.is_integer() else f"{value:,.2f}"
        except (TypeError, ValueError):
            return str(price)

    def update_prices(self):
        keys = [m.get("key") for m in self.markets]
        try: self.prices = get_prices(keys)
        except: pass

        for m in self.markets:
            key = m.get("key", "")
            if key not in self.price_labels: continue
            data = self.prices.get(key, {})
            price, direction = data.get("price"), data.get("direction", "")
            unit = get_latin_unit(key, self.language)

            price_text = f"{self.format_price(price, key)} {unit}" if price is not None else ("دریافت نشد" if self.language == "fa" else "N/A")
            self.price_labels[key].setText(price_text.strip())

            color = "#34d399" if direction == "high" else "#fb7185" if direction == "low" else "#f8fafc"
            self.price_labels[key].setStyleSheet(f"color: {color}; background: transparent; border: none; font-weight: bold;")

    def build_ui(self):
        try: self.prices = get_prices([m.get("key") for m in self.markets])
        except: self.prices = {}

        row_height = int(self.font_size * 1.5) + 14
        actual_rows = min(len(self.markets), self.rows_visible) if self.markets else 1
        self.setFixedSize(360, (actual_rows * row_height) + 50)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)
        
        panel = QFrame()
        panel.setAttribute(Qt.WA_StyledBackground, True)
        panel.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(15, 23, 42, {self.opacity});
                border: 1px solid rgba(255, 255, 255, 20);
                border-radius: 18px;
            }}
        """)
        outer.addWidget(panel)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 14, 16, 14)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollArea > QWidget > QWidget { background: transparent; }
            QScrollBar:vertical { width: 5px; background: transparent; }
            QScrollBar::handle:vertical { background: rgba(255, 255, 255, 40); border-radius: 2px; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
        """)

        scroll_widget = QWidget()
        scroll_widget.setStyleSheet("background: transparent; border: none;")
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(4, 0, 8, 0)
        scroll_layout.setSpacing(12)

        if not self.markets:
            empty = QLabel("هیچ ارزی انتخاب نشده" if self.language == "fa" else "No market selected")
            empty.setStyleSheet("color: #94a3b8; background: transparent; border: none;")
            empty.setAlignment(Qt.AlignCenter)
            scroll_layout.addWidget(empty)
        else:
            c_font = QFont(self.font_family, self.font_size)
            b_font = QFont(self.font_family, self.font_size, QFont.Bold)

            for m in self.markets:
                key, name = m.get("key", ""), m.get("name", "Unknown")
                data = self.prices.get(key, {})
                price, direction = data.get("price"), data.get("direction", "")
                
                price_text = f"{self.format_price(price, key)} {get_latin_unit(key, self.language)}" if price is not None else ("دریافت نشد" if self.language == "fa" else "N/A")
                sym = MARKET_SYMBOLS.get(key, "•")
                
                row = QWidget()
                row.setStyleSheet("background: transparent; border: none;")
                r_lay = QHBoxLayout(row)
                r_lay.setContentsMargins(0, 0, 0, 0)

                l_sym = QLabel(sym)
                l_sym.setFont(c_font)
                l_sym.setStyleSheet("background: transparent; border: none;")
                
                l_name = QLabel(name)
                l_name.setFont(c_font)
                l_name.setStyleSheet("color: #cbd5e1; background: transparent; border: none;")

                l_price = QLabel(price_text)
                l_price.setFont(b_font)
                
                self.price_labels[key] = l_price

                if self.language == "fa":
                    l_name.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    l_price.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                    r_lay.addWidget(l_price)
                    r_lay.addStretch()
                    r_lay.addWidget(l_name)
                    r_lay.addWidget(l_sym)
                else:
                    l_name.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                    l_price.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    r_lay.addWidget(l_sym)
                    r_lay.addWidget(l_name)
                    r_lay.addStretch()
                    r_lay.addWidget(l_price)

                color = "#34d399" if direction == "high" else "#fb7185" if direction == "low" else "#f8fafc"
                l_price.setStyleSheet(f"color: {color}; background: transparent; border: none;")
                scroll_layout.addWidget(row)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton: self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and hasattr(self, "drag_pos"): self.move(event.globalPosition().toPoint() - self.drag_pos)
        super().mouseMoveEvent(event)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app = QApplication(sys.argv)
    window = WidgetWindow()
    window.show()
    sys.exit(app.exec())
