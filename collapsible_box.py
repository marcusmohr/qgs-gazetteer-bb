from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtWidgets import *


class CollapsibleBox(QWidget):
    """Custom Box which is not implemented by QT"""

    def __init__(self, title="", parent=None):
        super(CollapsibleBox, self).__init__(parent)

        self.toggle_button = QToolButton(text=title, \
            checkable=True, checked=False)

        self.toggle_button.setStyleSheet("QToolButton { border: none; }")
        self.toggle_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

        self.toggle_button.setArrowType(Qt.RightArrow)
        self.toggle_button.pressed.connect(self.on_pressed)

        self.toggle_animation = QParallelAnimationGroup(self)

        self.content_area = QScrollArea(maximumHeight=0, minimumHeight=0)

        self.content_area.setSizePolicy(QSizePolicy.Expanding, \
            QSizePolicy.Fixed)

        self.content_area.setFrameShape(QFrame.NoFrame)

        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.toggle_button)
        layout.addWidget(self.content_area)

        self.toggle_animation.addAnimation(QPropertyAnimation \
            (self, b"minimumHeight"))
        self.toggle_animation.addAnimation(QPropertyAnimation \
            (self, b"maximumHeight"))
        self.toggle_animation.addAnimation(QPropertyAnimation\
            (self.content_area, b"maximumHeight"))


    @pyqtSlot()
    def on_pressed(self):
        checked = self.toggle_button.isChecked()

        self.toggle_button.setArrowType(Qt.DownArrow \
            if not checked else Qt.RightArrow)

        self.toggle_animation.setDirection(
            QAbstractAnimation.Forward
            if not checked
            else QAbstractAnimation.Backward
        )

        self.toggle_animation.start()


    def set_layout(self, layout):
        lay = self.content_area.layout()

        del lay

        layout.setContentsMargins(0, 0, 0, 0)
        self.content_area.setLayout(layout)

        collapsed_height = (self.sizeHint().height() - \
            self.content_area.maximumHeight())

        content_height = layout.sizeHint().height()

        for i in range(self.toggle_animation.animationCount()):
            animation = self.toggle_animation.animationAt(i)
            animation.setDuration(300)
            animation.setStartValue(collapsed_height)
            animation.setEndValue(collapsed_height + content_height)

        content_animation = self.toggle_animation.animationAt \
            (self.toggle_animation.animationCount() - 1)

        content_animation.setDuration(300)
        content_animation.setStartValue(0)
        content_animation.setEndValue(content_height)
