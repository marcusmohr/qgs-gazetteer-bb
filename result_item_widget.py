import sys
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtWidgets import *

class ResultItemWidget(QWidget):
    """Custom ListWidgetItem with specific layout."""

    def __init__(self, title, subtitle, parent=None):
        super(ResultItemWidget, self).__init__(parent)

        self.title = QLabel(title)
        self.subtitle = QLabel(subtitle)

        self.qv_box_layout = QVBoxLayout()
        self.qv_box_layout.addWidget(self.title)
        self.qv_box_layout.addWidget(self.subtitle)

        self.setLayout(self.qv_box_layout)

        self.subtitle.setStyleSheet('color: rgb(150, 150, 150);')
