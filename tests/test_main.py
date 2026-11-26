from PySide6.QtWidgets import QApplication

from app.main import MainWindow


def test_main_window(qtbot):
    window = MainWindow()

    qtbot.addWidget(window)

    assert window.windowTitle() == "Voicemo"
    assert window.width() == 980
    assert window.height() == 680