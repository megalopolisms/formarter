#!/usr/bin/env python3
"""
Formarter - Federal Court Document Formatter
Entry point for the application.
"""

import sys
from PyQt6.QtWidgets import QApplication
from src.app import MainWindow


def main():
    """Initialize and run the Formarter application."""
    app = QApplication(sys.argv)
    app.setApplicationName("Formarter")
    app.setOrganizationName("Megalopolisms")

    window = MainWindow()
    window.showMaximized()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
