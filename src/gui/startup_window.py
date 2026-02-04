import sys
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QLineEdit, 
                             QPushButton, QCompleter, QMessageBox)
from PyQt6.QtCore import Qt

class StartupWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Select Planet")
        self.resize(300, 150)
        self.planet_name = ""

        layout = QVBoxLayout()
        self.setLayout(layout)

        layout.addWidget(QLabel("Enter Planet Name:"))
        
        self.name_input = QLineEdit()
        layout.addWidget(self.name_input)

        # Setup Auto-complete
        try:
            import superearth
            df = superearth.exoplanets(25,25)
            if 'pl_name' in df.columns:
                names = df['pl_name'].astype(str).tolist()
                completer = QCompleter(names)
                completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
                completer.setFilterMode(Qt.MatchFlag.MatchContains)
                self.name_input.setCompleter(completer)
        except ImportError:
            # Handle case where superearth is not installed
            pass 
        except Exception as e:
            print(f"Error loading planet names: {e}")

        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self.accept_name)
        layout.addWidget(self.ok_btn)

    def accept_name(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Input Error", "Please enter a planet name.")
            return
        self.planet_name = name
        self.accept()

