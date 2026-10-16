# -*- coding: utf-8 -*-
"""
Al-Bonyan ERP - Mobile Android Application Main Entry Point.
Runs seamlessly on Android phones (as APK) and Desktop for testing.
"""
import os
import sys

# Ensure local module imports work smoothly
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(BASE_DIR)
for p in [BASE_DIR, PARENT_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

from kivy.app import App
from kivy.core.window import Window
from kivy.utils import platform

from mobile_app.api_client import MobileDataClient
from mobile_app.ui import MobileAppRoot, C_BG

# Set mobile portrait window dimensions on desktop preview
if platform not in ('android', 'ios'):
    Window.size = (390, 780)
    Window.clearcolor = C_BG


class AlBonyanMobileApp(App):
    title = "Al-Bonyan ERP Mobile"

    def build(self):
        self.client = MobileDataClient()
        return MobileAppRoot(self.client)


def main():
    AlBonyanMobileApp().run()


if __name__ == '__main__':
    main()
