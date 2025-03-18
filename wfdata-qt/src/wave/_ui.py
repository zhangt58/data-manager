from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout,
    QLabel
)


class MyWindow(QMainWindow):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("A Simple Window with PySide6")

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Create a layout for the central widget
        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        # Add a label to the central widget
        label = QLabel("Hello, PySide6!")
        layout.addWidget(label)

