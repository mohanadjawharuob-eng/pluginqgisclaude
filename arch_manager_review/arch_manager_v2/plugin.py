import os
from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon
from .dock import ArchWindow

class ArchManagerPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.window = None
        self.action = None

    def initGui(self):
        _icon_path = os.path.join(os.path.dirname(__file__), 'logo.svg')
        _icon = QIcon(_icon_path) if os.path.exists(_icon_path) else QIcon()
        self.action = QAction(_icon, "Archaeological Manager", self.iface.mainWindow())
        self.action.triggered.connect(self.show_window)
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu("Archaeological Manager", self.action)

    def show_window(self):
        if self.window is None:
            self.window = ArchWindow(self.iface)
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()

    def unload(self):
        if self.action:
            self.iface.removeToolBarIcon(self.action)
            self.iface.removePluginMenu("Archaeological Manager", self.action)
        if self.window:
            self.window.close()
            self.window = None
