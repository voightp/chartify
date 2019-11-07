from PySide2.QtWebEngineWidgets import QWebEnginePage
from PySide2 import QtWebChannel

from esopie.controller.wv_controller import WVController


class MyPage(QWebEnginePage):
    def __init__(self):
        super().__init__()

    def javaScriptConsoleMessage(self, level, msg, line, source):
        print(f"JS >> {source} {line} {msg}")


class WebviewController:
    def __init__(self, model, web_view):
        self.wv = web_view
        page = MyPage()
        self.wv.setPage(page)

        self.bridge = WVController(parent, palette)
        self.channel = QtWebChannel.QWebChannel(self)
        self.channel.registerObject("bridge", self.bridge)

        self.wv.page().setWebChannel(self.channel)
        self.m = model
