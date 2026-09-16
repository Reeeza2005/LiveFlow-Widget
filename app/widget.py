import sys
import json
import signal
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QShortcut, QKeySequence, QAction
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QScrollArea,
    QMenu,
)

from pynput import keyboard

from app.tgju import get_prices
from app.settings import SettingsWindow


# ============================================================
# مسیر تنظیمات
# ============================================================

if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):

    BASE_DIR = Path(sys._MEIPASS)

    CONFIG_FILE = (
        Path.home()
        / ".config"
        / "liveflow-widget"
        / "markets.json"
    )

else:

    BASE_DIR = Path(__file__).resolve().parent.parent

    CONFIG_FILE = (
        BASE_DIR
        / "config"
        / "markets.json"
    )


# ============================================================
# نماد بازارها
# ============================================================

MARKET_SYMBOLS = {

    "sekee": "🪙",
    "nim": "🪙",
    "rob": "🪙",
    "geram18": "🟡",
    "geram24": "🟡",
    "ons": "🥇",

    "price_dollar_rl": "🇺🇸",
    "price_eur": "🇪🇺",
    "price_gbp": "🇬🇧",
    "price_aed": "🇦🇪",
    "price_try": "🇹🇷",
    "price_cny": "🇨🇳",

    "crypto-tether": "₮",
    "tether": "₮",
    "crypto-bitcoin": "₿",
    "crypto-ethereum": "Ξ",
    "crypto-bnb": "🟡",
    "crypto-solana": "🟣",
    "crypto-dogecoin": "🐕",
    "crypto-xrp": "✖",

    "oil_brent": "🛢️",
    "oil_wti": "🛢️",
    "gc30": "📈",
    "silver": "🥈",
}


# ============================================================
# واحد قیمت
# ============================================================

def get_latin_unit(key, lang):

    if key in {
        "sekee",
        "nim",
        "rob",
        "geram18",
        "geram24",
        "price_dollar_rl",
        "price_eur",
        "price_gbp",
        "price_aed",
        "price_try",
        "price_cny",
        "crypto-tether",
        "tether",
    }:

        return "T"

    elif (
        "crypto" in key
        or key in {
            "ons",
            "silver",
            "oil_brent",
            "oil_wti",
        }
    ):

        return "$"

    return ""


# ============================================================
# Widget Window
# ============================================================

class WidgetWindow(QWidget):

    # --------------------------------------------------------
    # سیگنال Qt برای انتقال Hotkey از Thread مربوط به pynput
    # به Thread اصلی Qt
    # --------------------------------------------------------

    toggle_requested = Signal()

    # ========================================================
    # Init
    # ========================================================

    def __init__(self):

        super().__init__()

        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )

        self.setAttribute(
            Qt.WA_TranslucentBackground
        )

        # ----------------------------------------------------
        # داده‌ها
        # ----------------------------------------------------

        self.markets = []
        self.prices = {}
        self.price_labels = {}

        # ----------------------------------------------------
        # تنظیمات پیش‌فرض
        # ----------------------------------------------------

        self.opacity = 210
        self.font_size = 13
        self.font_family = "Noto Sans"
        self.rows_visible = 6
        self.interval = 120
        self.language = "fa"

        self.hotkey_close = "Ctrl+Q"
        self.hotkey_hide = "Ctrl+H"
        self.hotkey_settings = "Ctrl+Alt+S"

        # ----------------------------------------------------
        # Layout
        # ----------------------------------------------------

        self.outer_layout = None
        self.panel = None

        # ----------------------------------------------------
        # Shortcut references
        # ----------------------------------------------------

        self.shortcut_close = None
        self.shortcut_settings = None

        # ----------------------------------------------------
        # Host برای Shortcutهای Qt
        # ----------------------------------------------------

        self.shortcut_host = QWidget()

        self.shortcut_host.setWindowTitle(
            "LiveFlow Widget Hotkey Host"
        )

        # ----------------------------------------------------
        # اتصال Signal مربوط به Global Hotkey
        # ----------------------------------------------------

        self.toggle_requested.connect(
            self.toggle_visibility
        )

        # ----------------------------------------------------
        # Listener
        # ----------------------------------------------------

        self.hotkey_listener = None

        # ----------------------------------------------------
        # Load config
        # ----------------------------------------------------

        self.load_config()

        # ----------------------------------------------------
        # Build UI
        # ----------------------------------------------------

        self.build_ui()

        # ----------------------------------------------------
        # Setup Qt shortcuts
        # ----------------------------------------------------

        self.setup_hotkeys()

        # ----------------------------------------------------
        # Setup Global Ctrl+H
        # ----------------------------------------------------

        self.setup_global_hotkey()

        # ----------------------------------------------------
        # Timer
        # ----------------------------------------------------

        self.timer = QTimer(self)

        self.timer.timeout.connect(
            self.update_prices
        )

        self.timer.start(
            max(
                1,
                int(self.interval)
            ) * 1000
        )

    # ========================================================
    # Load Config
    # ========================================================

    def load_config(self):

        try:

            if not CONFIG_FILE.exists():

                self.markets = []

                return

            with open(
                CONFIG_FILE,
                "r",
                encoding="utf-8",
            ) as f:

                data = json.load(f)

            # ------------------------------------------------
            # Markets
            # ------------------------------------------------

            self.markets = [
                m
                for m in data.get(
                    "markets",
                    [],
                )
                if m.get(
                    "enabled",
                    False,
                )
            ]

            # ------------------------------------------------
            # Appearance
            # ------------------------------------------------

            app_cfg = data.get(
                "appearance",
                {},
            )

            self.opacity = app_cfg.get(
                "opacity",
                210,
            )

            self.font_size = app_cfg.get(
                "font_size",
                13,
            )

            self.font_family = app_cfg.get(
                "font_family",
                "Noto Sans",
            )

            self.rows_visible = app_cfg.get(
                "rows_visible",
                6,
            )

            self.interval = app_cfg.get(
                "interval",
                120,
            )

            self.language = app_cfg.get(
                "language",
                "fa",
            )

            # ------------------------------------------------
            # Hotkeys
            # ------------------------------------------------

            hot_cfg = data.get(
                "hotkeys",
                {},
            )

            self.hotkey_close = hot_cfg.get(
                "close",
                "Ctrl+Q",
            )

            self.hotkey_hide = hot_cfg.get(
                "hide",
                "Ctrl+H",
            )

            self.hotkey_settings = hot_cfg.get(
                "settings",
                "Ctrl+Alt+S",
            )

        except Exception as e:

            print(
                f"Config load error: {e}"
            )

            self.markets = []

    # ========================================================
    # Setup Qt Hotkeys
    # ========================================================

    def setup_hotkeys(self):

        # ----------------------------------------------------
        # حذف Shortcutهای قبلی
        # ----------------------------------------------------

        for shortcut_name in (
            "shortcut_close",
            "shortcut_settings",
        ):

            shortcut = getattr(
                self,
                shortcut_name,
                None,
            )

            if shortcut is not None:

                try:
                    shortcut.setEnabled(False)
                except Exception:
                    pass

                shortcut.deleteLater()

                setattr(
                    self,
                    shortcut_name,
                    None,
                )

        # ----------------------------------------------------
        # Ctrl+Q
        # ----------------------------------------------------

        if self.hotkey_close:

            self.shortcut_close = QShortcut(
                QKeySequence(
                    self.hotkey_close
                ),
                self.shortcut_host,
            )

            self.shortcut_close.setContext(
                Qt.ApplicationShortcut
            )

            self.shortcut_close.activated.connect(
                QApplication.quit
            )

        # ----------------------------------------------------
        # Settings
        # ----------------------------------------------------

        if self.hotkey_settings:

            self.shortcut_settings = QShortcut(
                QKeySequence(
                    self.hotkey_settings
                ),
                self.shortcut_host,
            )

            self.shortcut_settings.setContext(
                Qt.ApplicationShortcut
            )

            self.shortcut_settings.activated.connect(
                self.open_settings
            )

    # ========================================================
    # Global Hotkey
    # ========================================================

    def setup_global_hotkey(self):

        # ----------------------------------------------------
        # اگر Listener قبلی وجود دارد، متوقفش کن
        # ----------------------------------------------------

        if self.hotkey_listener is not None:

            try:
                self.hotkey_listener.stop()
            except Exception:
                pass

            self.hotkey_listener = None

        # ----------------------------------------------------
        # Ctrl+H
        #
        # این Hotkey مستقل از پنجره Qt است.
        # ----------------------------------------------------

        try:

            hotkeys = {
                "<ctrl>+h": self.on_global_toggle
            }

            self.hotkey_listener = (
                keyboard.GlobalHotKeys(
                    hotkeys
                )
            )

            self.hotkey_listener.daemon = True

            self.hotkey_listener.start()

            print(
                "Global hotkey Ctrl+H enabled"
            )

        except Exception as e:

            print(
                f"Global hotkey error: {e}"
            )

    # ========================================================
    # Global Hotkey Callback
    # ========================================================

    def on_global_toggle(self):

        # ----------------------------------------------------
        # این تابع توسط Thread مربوط به pynput اجرا می‌شود.
        #
        # مستقیماً UI را تغییر نمی‌دهیم.
        # فقط Signal می‌فرستیم تا Qt آن را در Thread اصلی
        # اجرا کند.
        # ----------------------------------------------------

        self.toggle_requested.emit()

    # ========================================================
    # Toggle Visibility
    # ========================================================

    def toggle_visibility(self):

        if self.isVisible():

            print(
                "LiveFlow Widget: HIDE"
            )

            self.hide()

        else:

            print(
                "LiveFlow Widget: SHOW"
            )

            self.show()

            self.raise_()

            self.activateWindow()

    # ========================================================
    # Apply Settings
    # ========================================================

    def apply_settings(self):

        was_visible = self.isVisible()

        # ----------------------------------------------------
        # Load
        # ----------------------------------------------------

        self.load_config()

        # ----------------------------------------------------
        # Timer
        # ----------------------------------------------------

        if hasattr(
            self,
            "timer",
        ):

            self.timer.setInterval(
                max(
                    1,
                    int(self.interval),
                ) * 1000
            )

        # ----------------------------------------------------
        # Qt Shortcutها
        # ----------------------------------------------------

        self.setup_hotkeys()

        # ----------------------------------------------------
        # Global Hotkey
        # ----------------------------------------------------

        self.setup_global_hotkey()

        # ----------------------------------------------------
        # UI
        # ----------------------------------------------------

        self.build_ui()

        # ----------------------------------------------------
        # Prices
        # ----------------------------------------------------

        self.update_prices()

        # ----------------------------------------------------
        # حفظ وضعیت نمایش
        # ----------------------------------------------------

        if was_visible:

            self.show()

            self.raise_()

            self.activateWindow()

    # ========================================================
    # Format Price
    # ========================================================

    def format_price(
        self,
        price,
        key,
    ):

        try:

            if isinstance(
                price,
                str,
            ):

                price = price.replace(
                    ",",
                    "",
                )

            value = float(price)

            if key in {
                "sekee",
                "nim",
                "rob",
                "geram18",
                "geram24",
                "price_dollar_rl",
                "price_eur",
                "price_gbp",
                "price_aed",
                "price_try",
                "price_cny",
                "crypto-tether",
                "tether",
            }:

                value = value / 10

            if value.is_integer():

                return f"{int(value):,}"

            return f"{value:,.2f}"

        except (
            TypeError,
            ValueError,
        ):

            return str(price)

    # ========================================================
    # Update Prices
    # ========================================================

    def update_prices(self):

        keys = [
            m.get("key")
            for m in self.markets
        ]

        try:

            self.prices = get_prices(
                keys
            )

        except Exception as e:

            print(
                f"Price update error: {e}"
            )

        # ----------------------------------------------------
        # Update labels
        # ----------------------------------------------------

        for m in self.markets:

            key = m.get(
                "key",
                "",
            )

            if key not in self.price_labels:

                continue

            data = self.prices.get(
                key,
                {},
            )

            price = data.get(
                "price"
            )

            direction = data.get(
                "direction",
                "",
            )

            unit = get_latin_unit(
                key,
                self.language,
            )

            if price is not None:

                price_text = (
                    f"{self.format_price(price, key)} "
                    f"{unit}"
                )

            else:

                price_text = (
                    "دریافت نشد"
                    if self.language == "fa"
                    else "N/A"
                )

            self.price_labels[
                key
            ].setText(
                price_text.strip()
            )

            if direction == "high":

                color = "#34d399"

            elif direction == "low":

                color = "#fb7185"

            else:

                color = "#f8fafc"

            self.price_labels[
                key
            ].setStyleSheet(
                f"""
                color: {color};
                background: transparent;
                border: none;
                font-weight: bold;
                """
            )

    # ========================================================
    # Clear Existing UI
    # ========================================================

    def clear_ui(self):

        if self.outer_layout is None:

            return

        while (
            self.outer_layout.count()
        ):

            item = self.outer_layout.takeAt(
                0
            )

            widget = item.widget()

            child_layout = item.layout()

            if widget is not None:

                widget.deleteLater()

            elif child_layout is not None:

                while child_layout.count():

                    child_item = (
                        child_layout.takeAt(0)
                    )

                    child_widget = (
                        child_item.widget()
                    )

                    if child_widget:

                        child_widget.deleteLater()

        self.panel = None

    # ========================================================
    # Build UI
    # ========================================================

    def build_ui(self):

        # ----------------------------------------------------
        # قیمت اولیه
        # ----------------------------------------------------

        try:

            self.prices = get_prices(
                [
                    m.get("key")
                    for m in self.markets
                ]
            )

        except Exception:

            self.prices = {}

        # ----------------------------------------------------
        # Layout
        # ----------------------------------------------------

        if self.outer_layout is None:

            self.outer_layout = QVBoxLayout(
                self
            )

            self.outer_layout.setContentsMargins(
                8,
                8,
                8,
                8,
            )

        else:

            self.clear_ui()

        # ----------------------------------------------------
        # Labels
        # ----------------------------------------------------

        self.price_labels = {}

        # ----------------------------------------------------
        # Size
        # ----------------------------------------------------

        row_height = (
            int(self.font_size * 1.5)
            + 14
        )

        actual_rows = (
            min(
                len(self.markets),
                self.rows_visible,
            )
            if self.markets
            else 1
        )

        self.setFixedSize(
            360,
            (actual_rows * row_height) + 50,
        )

        # ----------------------------------------------------
        # Panel
        # ----------------------------------------------------

        panel = QFrame()

        self.panel = panel

        panel.setAttribute(
            Qt.WA_StyledBackground,
            True,
        )

        panel.setStyleSheet(
            f"""
            QFrame {{
                background-color:
                    rgba(
                        15,
                        23,
                        42,
                        {self.opacity}
                    );

                border:
                    1px solid
                    rgba(255, 255, 255, 20);

                border-radius:
                    18px;
            }}
            """
        )

        self.outer_layout.addWidget(
            panel
        )

        # ----------------------------------------------------
        # Panel layout
        # ----------------------------------------------------

        layout = QVBoxLayout(
            panel
        )

        layout.setContentsMargins(
            16,
            14,
            16,
            14,
        )

        # ----------------------------------------------------
        # Scroll
        # ----------------------------------------------------

        scroll = QScrollArea()

        scroll.setWidgetResizable(
            True
        )

        scroll.setStyleSheet(
            """
            QScrollArea {
                background: transparent;
                border: none;
            }

            QScrollArea > QWidget > QWidget {
                background: transparent;
            }

            QScrollBar:vertical {
                width: 5px;
                background: transparent;
            }

            QScrollBar::handle:vertical {
                background:
                    rgba(
                        255,
                        255,
                        255,
                        40
                    );

                border-radius: 2px;
            }

            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: none;
            }
            """
        )

        # ----------------------------------------------------
        # Scroll widget
        # ----------------------------------------------------

        scroll_widget = QWidget()

        scroll_widget.setStyleSheet(
            """
            background: transparent;
            border: none;
            """
        )

        scroll_layout = QVBoxLayout(
            scroll_widget
        )

        scroll_layout.setContentsMargins(
            4,
            0,
            8,
            0,
        )

        scroll_layout.setSpacing(
            12
        )

        # ----------------------------------------------------
        # No markets
        # ----------------------------------------------------

        if not self.markets:

            empty = QLabel(
                "هیچ ارزی انتخاب نشده"
                if self.language == "fa"
                else "No market selected"
            )

            empty.setStyleSheet(
                """
                color: #94a3b8;
                background: transparent;
                border: none;
                """
            )

            empty.setAlignment(
                Qt.AlignCenter
            )

            scroll_layout.addWidget(
                empty
            )

        # ----------------------------------------------------
        # Markets
        # ----------------------------------------------------

        else:

            c_font = QFont(
                self.font_family,
                self.font_size,
            )

            b_font = QFont(
                self.font_family,
                self.font_size,
                QFont.Bold,
            )

            for m in self.markets:

                key = m.get(
                    "key",
                    "",
                )

                name = m.get(
                    "name",
                    "Unknown",
                )

                data = self.prices.get(
                    key,
                    {},
                )

                price = data.get(
                    "price"
                )

                direction = data.get(
                    "direction",
                    "",
                )

                # --------------------------------------------
                # Price
                # --------------------------------------------

                if price is not None:

                    price_text = (
                        f"{self.format_price(price, key)} "
                        f"{get_latin_unit(key, self.language)}"
                    )

                else:

                    price_text = (
                        "دریافت نشد"
                        if self.language == "fa"
                        else "N/A"
                    )

                # --------------------------------------------
                # Symbol
                # --------------------------------------------

                sym = MARKET_SYMBOLS.get(
                    key,
                    "•",
                )

                # --------------------------------------------
                # Row
                # --------------------------------------------

                row = QWidget()

                row.setStyleSheet(
                    """
                    background: transparent;
                    border: none;
                    """
                )

                r_lay = QHBoxLayout(
                    row
                )

                r_lay.setContentsMargins(
                    0,
                    0,
                    0,
                    0,
                )

                # --------------------------------------------
                # Symbol
                # --------------------------------------------

                l_sym = QLabel(
                    sym
                )

                l_sym.setFont(
                    c_font
                )

                l_sym.setStyleSheet(
                    """
                    background: transparent;
                    border: none;
                    """
                )

                # --------------------------------------------
                # Name
                # --------------------------------------------

                l_name = QLabel(
                    name
                )

                l_name.setFont(
                    c_font
                )

                l_name.setStyleSheet(
                    """
                    color: #cbd5e1;
                    background: transparent;
                    border: none;
                    """
                )

                # --------------------------------------------
                # Price
                # --------------------------------------------

                l_price = QLabel(
                    price_text
                )

                l_price.setFont(
                    b_font
                )

                self.price_labels[
                    key
                ] = l_price

                # --------------------------------------------
                # Language
                # --------------------------------------------

                if self.language == "fa":

                    l_name.setAlignment(
                        Qt.AlignRight
                        | Qt.AlignVCenter
                    )

                    l_price.setAlignment(
                        Qt.AlignLeft
                        | Qt.AlignVCenter
                    )

                    r_lay.addWidget(
                        l_price
                    )

                    r_lay.addStretch()

                    r_lay.addWidget(
                        l_name
                    )

                    r_lay.addWidget(
                        l_sym
                    )

                else:

                    l_name.setAlignment(
                        Qt.AlignLeft
                        | Qt.AlignVCenter
                    )

                    l_price.setAlignment(
                        Qt.AlignRight
                        | Qt.AlignVCenter
                    )

                    r_lay.addWidget(
                        l_sym
                    )

                    r_lay.addWidget(
                        l_name
                    )

                    r_lay.addStretch()

                    r_lay.addWidget(
                        l_price
                    )

                # --------------------------------------------
                # Price color
                # --------------------------------------------

                if direction == "high":

                    color = "#34d399"

                elif direction == "low":

                    color = "#fb7185"

                else:

                    color = "#f8fafc"

                l_price.setStyleSheet(
                    f"""
                    color: {color};
                    background: transparent;
                    border: none;
                    """
                )

                scroll_layout.addWidget(
                    row
                )

        # ----------------------------------------------------
        # Stretch
        # ----------------------------------------------------

        scroll_layout.addStretch()

        scroll.setWidget(
            scroll_widget
        )

        layout.addWidget(
            scroll
        )

    # ========================================================
    # Context Menu
    # ========================================================

    def contextMenuEvent(
        self,
        event,
    ):

        menu = QMenu(
            self
        )

        menu.setStyleSheet(
            """
            QMenu {
                background-color: #0f172a;
                color: #f8fafc;
                border:
                    1px solid
                    rgba(255, 255, 255, 30);
                border-radius: 10px;
                padding: 6px;
            }

            QMenu::item {
                padding: 6px 20px;
                border-radius: 6px;
            }

            QMenu::item:selected {
                background-color: #3b82f6;
                color: white;
            }
            """
        )

        # ----------------------------------------------------
        # Settings
        # ----------------------------------------------------

        settings_action = QAction(
            "⚙️ تنظیمات",
            self
        )

        settings_action.triggered.connect(
            self.open_settings
        )

        menu.addAction(
            settings_action
        )

        menu.addSeparator()

        # ----------------------------------------------------
        # Quit
        # ----------------------------------------------------

        quit_action = QAction(
            "❌ خروج",
            self
        )

        quit_action.triggered.connect(
            QApplication.quit
        )

        menu.addAction(
            quit_action
        )

        menu.exec(
            event.globalPos()
        )

    # ========================================================
    # Open Settings
    # ========================================================

    def open_settings(self):

        if (
            not hasattr(
                self,
                "settings_win",
            )
            or not self.settings_win.isVisible()
        ):

            self.settings_win = SettingsWindow()

            self.settings_win.settings_saved.connect(
                self.apply_settings
            )

            self.settings_win.show()

        else:

            self.settings_win.raise_()

            self.settings_win.activateWindow()

    # ========================================================
    # Mouse Drag
    # ========================================================

    def mousePressEvent(
        self,
        event,
    ):

        if event.button() == Qt.LeftButton:

            self.drag_pos = (
                event.globalPosition().toPoint()
                - self.frameGeometry().topLeft()
            )

        super().mousePressEvent(
            event
        )

    # ========================================================
    # Mouse Move
    # ========================================================

    def mouseMoveEvent(
        self,
        event,
    ):

        if (
            event.buttons()
            & Qt.LeftButton
            and hasattr(
                self,
                "drag_pos",
            )
        ):

            self.move(
                event.globalPosition().toPoint()
                - self.drag_pos
            )

        super().mouseMoveEvent(
            event
        )

    # ========================================================
    # Close Event
    # ========================================================

    def closeEvent(self, event):

        # ----------------------------------------------------
        # توقف Global Hotkey Listener
        # ----------------------------------------------------

        if self.hotkey_listener is not None:

            try:
                self.hotkey_listener.stop()
            except Exception:
                pass

            self.hotkey_listener = None

        super().closeEvent(
            event
        )


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":

    signal.signal(
        signal.SIGINT,
        signal.SIG_DFL
    )

    app = QApplication(
        sys.argv
    )

    window = WidgetWindow()

    window.show()

    sys.exit(
        app.exec()
    )
