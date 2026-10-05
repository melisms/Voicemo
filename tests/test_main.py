from app.ui.main_window import MainWindow


def test_main_window(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    assert window.windowTitle() == "Voicemo"
    assert window.width() == 980
    assert window.height() == 680