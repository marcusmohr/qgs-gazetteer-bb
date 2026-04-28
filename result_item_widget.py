from qgis.PyQt.QtWidgets import (
    QLabel,
    QVBoxLayout,
    QWidget,
)

class ResultItemWidget(QWidget):
    """Custom ListWidgetItem with specific layout."""

    def __init__(self, title, subtitle, parent=None):
        super().__init__(parent)

        self.title = QLabel(title)
        self.subtitle = QLabel(subtitle)

        layout = QVBoxLayout()
        layout.addWidget(self.title)
        layout.addWidget(self.subtitle)
        self.setLayout(layout)

        self.subtitle.setStyleSheet('color: rgb(150, 150, 150);')
