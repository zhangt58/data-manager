from ._ui import MyWindow

__authors__ = "Tong Zhang"
__copyright__ = "(c) 2025, Facility for Rare Isotope Beams," \
                " Michigan State University"
__contact__ = "Tong Zhang <zhangt@frib.msu.edu>"
__version__ = "0.9.7"
__title__ = "DataManager: Manage the Accelerator Data"


def main():
    from PySide6.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    w = MyWindow()
    w.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
