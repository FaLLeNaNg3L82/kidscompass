import pytest
from PySide6.QtWidgets import QApplication
from kidscompass.ui import MainWindow

@pytest.fixture
def main_window(qtbot):
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    return window

def test_mainwindow_tabs_and_title(main_window, qtbot):
    assert main_window.windowTitle() == "KidsCompass"
    tab_widget = main_window.centralWidget()
    assert tab_widget.tabText(0) == "Einstellungen"
    assert tab_widget.tabText(1) == "Status"
    assert tab_widget.tabText(2) == "Export"
    assert tab_widget.tabText(3) == "Statistiken"
    # Switch to each tab and check it's visible
    for i in range(tab_widget.count()):
        tab_widget.setCurrentIndex(i)
        qtbot.wait(100)
        assert tab_widget.currentIndex() == i
