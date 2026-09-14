import sys
import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
)

from app.tgju import get_prices


BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = BASE_DIR / "config" / "markets.json"

MARKET_SYMBOLS = {
    "sekee": "🪙",
    "geram18": "🟡",
    "price_dollar_rl": "🇺🇸",
    "price_eur": "🇪🇺",
    "price_gbp": "🇬🇧",
    "ons": "🥇",
    "crypto-tether": "₮",
    "crypto-bitcoin": "₿",
    "crypto-ethereum": "Ξ",
    "oil_brent": "🛢️",
    "gc30": "📈",
}


class WidgetWindow(QWidget):

    def __init__(self):
        super().__init__()

        self.setFixedSize(360, 800)

        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )

        self.setAttribute(
            Qt.WA_TranslucentBackground
        )

        self.markets = []
        self.prices = {}

        self.load_markets()
        self.build_ui()

    def load_markets(self):

        try:
            with open(
                CONFIG_FILE,
                "r",
                encoding="utf-8"
            ) as f:

                data = json.load(f)

            self.markets = [
                market
                for market in data.get(
                    "markets",
                    []
                )
                if market.get(
                    "enabled",
                    False
                )
            ]

        except Exception:
            self.markets = []

    def load_prices(self):

        keys = [
            market.get("key")
            for market in self.markets
        ]

        try:
            self.prices = get_prices(keys)

        except Exception:
            self.prices = {}

    def format_price(self, price):

        try:

            value = float(price)

            if value.is_integer():
                return f"{int(value):,}"

            return f"{value:,.2f}"

        except (TypeError, ValueError):

            return str(price)

    def build_ui(self):

        self.load_prices()

        outer_layout = QVBoxLayout(self)

        outer_layout.setContentsMargins(
            5,
            5,
            5,
            5
        )

        outer_layout.setSpacing(0)

        panel = QFrame()

        panel.setObjectName("panel")

        panel.setAttribute(
            Qt.WA_StyledBackground,
            True
        )

        panel.setStyleSheet("""
            QFrame#panel {
                background-color: rgba(20, 27, 37, 235);
                border: 1px solid rgba(120, 140, 165, 180);
                border-radius: 24px;
            }
        """)

        outer_layout.addWidget(panel)

        layout = QVBoxLayout(panel)

        layout.setContentsMargins(
            25,
            25,
            25,
            25
        )

        layout.setSpacing(8)

        title = QLabel("TGJU")

        title.setFont(
            QFont(
                "Noto Sans",
                20,
                QFont.Bold
            )
        )

        title.setStyleSheet("""
            QLabel {
                color: #ffffff;
                background: transparent;
            }
        """)

        layout.addWidget(title)

        subtitle = QLabel("Market Prices")

        subtitle.setStyleSheet("""
            QLabel {
                color: #9aa7b8;
                background: transparent;
                font-size: 12px;
            }
        """)

        layout.addWidget(subtitle)

        layout.addSpacing(12)

        if not self.markets:

            empty = QLabel(
                "No markets configured"
            )

            empty.setStyleSheet("""
                QLabel {
                    color: #ffffff;
                    background-color: transparent;
                    border: none;
                    font-size: 13px;
                }
            """)

            layout.addWidget(empty)

        else:

            for market in self.markets:

                key = market.get(
                    "key",
                    ""
                )

                name = market.get(
                    "name",
                    "Unknown"
                )

                unit = market.get(
                    "unit",
                    ""
                )

                data = self.prices.get(
                    key,
                    {}
                )

                price = data.get(
                    "price"
                )

                if price is not None:

                    price_text = self.format_price(
                        price
                    )

                    if unit:
                        price_text = (
                            f"{price_text} {unit}"
                        )

                else:

                    price_text = "دریافت نشد"

                symbol = MARKET_SYMBOLS.get(
                    key,
                    "•"
                )

                name_label = QLabel(
                    f"{symbol}  {name}"
                )

                price_label = QLabel(
                    price_text
                )

                name_label.setFont(
                    QFont(
                        "Noto Sans",
                        11
                    )
                )

                price_label.setFont(
                    QFont(
                        "Noto Sans",
                        8
                    )
                )

                name_label.setAlignment(
                    Qt.AlignRight
                    | Qt.AlignVCenter
                )

                price_label.setAlignment(
                    Qt.AlignLeft
                    | Qt.AlignVCenter
                )

                row = QWidget()

                row_layout = QHBoxLayout(
                    row
                )

                row_layout.setContentsMargins(
                    4,
                    6,
                    4,
                    6
                )

                row_layout.setSpacing(12)

                row_layout.addWidget(
                    price_label,
                    1
                )

                row_layout.addWidget(
                    name_label,
                    1
                )

                row.setStyleSheet("""
                    QWidget {
                        background: transparent;
                        border: none;
                    }

                    QLabel {
                        color: #ffffff;
                        background: transparent;
                        border: none;
                    }
                """)

                layout.addWidget(row)

        layout.addStretch()

    def keyPressEvent(
        self,
        event
    ):

        if event.key() == Qt.Key_Escape:

            self.close()

        else:

            super().keyPressEvent(
                event
            )


def main():

    app = QApplication(
        sys.argv
    )

    window = WidgetWindow()

    window.show()

    sys.exit(
        app.exec()
    )


if __name__ == "__main__":

    main()
