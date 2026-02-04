
import sys
from PyQt6.QtWidgets import QApplication
from src.gui.main_window import MainWindow
from src.gui.startup_window import StartupWindow

if __name__ == '__main__':
    # Add the src directory to the python path
    sys.path.insert(0, './src')
    app = QApplication(sys.argv)
    
    startup = StartupWindow()
    if startup.exec() == StartupWindow.DialogCode.Accepted:
        main_win = MainWindow(planet_name=startup.planet_name)
        main_win.show()
        sys.exit(app.exec())
    else:
        sys.exit()
