import sys
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QColor
from PySide6.QtWidgets import QApplication, QWidget


class TGJUWidget(QWidget):
    def __init__(self):
        super().__init__()

        self.setFixedSize(290, 390)

        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )

        # مهم: خود پنجره شفاف است
        self.setAttribute(Qt.WA_TranslucentBackground)

        screen = QApplication.primaryScreen().availableGeometry()

        x = screen.width() - self.width() - 25
        y = 70

        self.move(x, y)

    def paintEvent(self, event):
        painter = QPainter(self)

        painter.setRenderHint(QPainter.Antialiasing)

        # شیشه اصلی
        painter.setBrush(QColor(27, 34, 45, 235))
        painter.setPen(QColor(59, 70, 86, 255))

        painter.drawRoundedRect(
            8,
            5,
            self.width() - 16,
            self.height() - 13,
            22,
            22,
        )


def main():
    app = QApplication(sys.argv)

    widget = TGJUWidget()
    widget.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
