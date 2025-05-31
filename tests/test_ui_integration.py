import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
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

def test_export_button_triggers_export(main_window, qtbot, monkeypatch):
    tab_widget = main_window.centralWidget()
    export_tab_index = 2  # "Export"
    tab_widget.setCurrentIndex(export_tab_index)
    qtbot.wait(100)

    export_tab = tab_widget.widget(export_tab_index)
    export_button = export_tab.btn_export

    called = {}
    class DummyWorker:
        def __init__(self, *a, **kw):
            called['init'] = True
        def moveToThread(self, thread): pass
        def run(self): called['run'] = True
        def deleteLater(self): pass
        finished = type('Signal', (), {'connect': lambda *a, **k: None})()
        error = type('Signal', (), {'connect': lambda *a, **k: None})()

    monkeypatch.setattr('kidscompass.ui.ExportWorker', DummyWorker)

    qtbot.mouseClick(export_button, Qt.LeftButton)
    qtbot.wait(100)

    assert called.get('init'), "ExportWorker was not instantiated"
    # Note: In real async, you may need to trigger thread start or signal manually
