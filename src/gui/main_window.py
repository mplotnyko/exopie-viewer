import sys
import pandas as pd
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from src.gui.workers import Worker # Uncomment when running with your file structure

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QFormLayout, QLineEdit, QPushButton, QComboBox, QTabWidget, QCheckBox,
    QTableView, QTextBrowser, QLabel, QDoubleSpinBox, QSpinBox, QMessageBox, 
    QGroupBox, QToolButton, QSizePolicy
)
from PyQt6.QtGui import QDoubleValidator, QFont
from PyQt6.QtCore import QObject, QThread, pyqtSignal, QAbstractTableModel, Qt, QSize

class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super(MplCanvas, self).__init__(fig)
        self.setParent(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.updateGeometry()

class PandasModel(QAbstractTableModel):
    def __init__(self, data):
        super().__init__()
        self._data = data

    def rowCount(self, parent=None):
        return self._data.shape[0]

    def columnCount(self, parent=None):
        return self._data.shape[1]

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if index.isValid() and role == Qt.ItemDataRole.DisplayRole:
            return str(self._data.iloc[index.row(), index.column()])
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return str(self._data.columns[section])
            return str(self._data.index[section])
        return None

class ScientificIntInput(QLineEdit):
    def __init__(self, default_value=50000,decimals=0, parent=None):
        super().__init__(str(default_value), parent)
        self.decimals = decimals
        # Allow scientific notation like 1e5
        validator = QDoubleValidator(self)
        validator.setNotation(QDoubleValidator.Notation.ScientificNotation)
        self.setValidator(validator)

    def value(self):
        try:
            res = float(self.text())
            if res<0:
                raise ValueError("Negative value not allowed")
            if self.decimals > 0:
                return res
            else:
                # Convert scientific notation to int
                return max(1,int(res))
        except (ValueError, TypeError):
            return 0

class UncertaintyInput(QWidget):
    """Widget for Value ^[+Upper] _[-Lower]"""
    def __init__(self, default_val, default_unc, decimals=3):
        super().__init__()
        layout = QHBoxLayout()
        layout.setContentsMargins(0,0,0,0)
        
        self.val_input = ScientificIntInput(default_value=default_val, decimals=decimals)
        self.up_input = ScientificIntInput(default_value=default_unc, decimals=decimals)
        self.low_input = ScientificIntInput(default_value=default_unc, decimals=decimals)
        
        layout.addWidget(QLabel("["))
        layout.addWidget(self.val_input)
        layout.addWidget(QLabel("]"))
        
        layout.addWidget(QLabel("^[+"))
        layout.addWidget(self.up_input)
        layout.addWidget(QLabel("]"))
        
        layout.addWidget(QLabel("_[-"))
        layout.addWidget(self.low_input)
        layout.addWidget(QLabel("]"))
        
        self.setLayout(layout)

    def get_values(self):
        return self.val_input.value(), self.up_input.value(), self.low_input.value()

class MainWindow(QMainWindow):
    def __init__(self,planet_name=None):
        super().__init__()
        self.planet_name = planet_name

        self.setWindowTitle("ExoPie - ExoPlanet Interior Modeling")
        self.setGeometry(100, 100, 1200, 800)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)

        # Input panel with a larger global font for all its children
        input_panel = QWidget()
        input_panel.setFont(QFont("Arial", 11)) 
        input_layout = QVBoxLayout(input_panel)
        main_layout.addWidget(input_panel)

        output_panel = QTabWidget()
        main_layout.addWidget(output_panel, 1)

        # -- Form Layout with increased spacing --
        form_layout = QFormLayout()
        form_layout.setVerticalSpacing(20)      # Space between rows
        form_layout.setHorizontalSpacing(20)    # Space between label and input
        form_layout.setContentsMargins(10, 20, 10, 20) # Outer padding

        form_layout.addRow(QLabel(f"Planet: {self.planet_name}"))

        # Purely Rocky Checkbox
        self.rocky_checkbox = QCheckBox("Purely Rocky Planet")
        self.rocky_checkbox.toggled.connect(self.toggle_rocky_mode)
        form_layout.addRow(self.rocky_checkbox)

        # Planet Type Dropdown (Hidden if purely rocky)
        self.planet_type = QComboBox()
        self.planet_type.addItems(["Rocky", "Water", "Envelope"])
        self.planet_type.activated.connect(self.handle_selection)
        self.lbl_planet_type = QLabel("Planet Type:")
        form_layout.addRow(self.lbl_planet_type, self.planet_type)

        # Numerical inputs
        self.mass_input_widget = UncertaintyInput(5.0, 0.5)
        form_layout.addRow(QLabel("Mass (M_earth):"), self.mass_input_widget)

        self.radius_input_widget = UncertaintyInput(1.5, 0.1)
        form_layout.addRow(QLabel("Radius (R_earth):"), self.radius_input_widget)

        self.teq_input_widget = UncertaintyInput(300, 50, decimals=0)
        self.lbl_teq = QLabel("Teq (K):")
        form_layout.addRow(self.lbl_teq, self.teq_input_widget)

        self.run_button = QPushButton("Run Simulation")
        self.run_button.setMinimumHeight(40) # Larger button

        input_layout.addLayout(form_layout)
        
        # Advanced Options
        self.advanced_btn = QToolButton()
        self.advanced_btn.setText("Advanced Options ▼")
        self.advanced_btn.setCheckable(True)
        self.advanced_btn.setChecked(False)
        self.advanced_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.advanced_btn.clicked.connect(self.toggle_advanced)
        input_layout.addWidget(self.advanced_btn)

        self.advanced_group = QGroupBox()
        self.advanced_group.setVisible(False)
        adv_layout = QFormLayout(self.advanced_group)
        
        self.n_samples_input = ScientificIntInput(default_value=50000)
        adv_layout.addRow("N Samples:", self.n_samples_input)

        # xSi
        self.xsi_layout = QHBoxLayout()
        self.xsi_type = QComboBox()
        self.xsi_type.addItems(["Uniform"]) # Backend mainly supports uniform for xSi kwarg
        self.xsi_min = ScientificIntInput(0.0, decimals=2)
        self.xsi_max = ScientificIntInput(0.2, decimals=2)
        self.xsi_layout.addWidget(self.xsi_type)
        self.xsi_layout.addWidget(QLabel("["))
        self.xsi_layout.addWidget(self.xsi_min)
        self.xsi_layout.addWidget(self.xsi_max)
        self.xsi_layout.addWidget(QLabel("]"))
        adv_layout.addRow("xSi:", self.xsi_layout)

        # xFe
        self.xfe_layout = QHBoxLayout()
        self.xfe_type = QComboBox()
        self.xfe_type.addItems(["Uniform"])
        self.xfe_min = ScientificIntInput(0.0, decimals=2)
        self.xfe_max = ScientificIntInput(0.2, decimals=2)
        self.xfe_layout.addWidget(self.xfe_type)
        self.xfe_layout.addWidget(QLabel("["))
        self.xfe_layout.addWidget(self.xfe_min)
        self.xfe_layout.addWidget(self.xfe_max)
        self.xfe_layout.addWidget(QLabel("]"))
        adv_layout.addRow("xFe:", self.xfe_layout)

        # Stellar Values
        self.stellar_check = QCheckBox("Use Stellar Values")
        self.stellar_check.toggled.connect(self.toggle_stellar)
        adv_layout.addRow(self.stellar_check)

        self.stellar_container = QWidget()
        self.stellar_container.setVisible(False)
        stellar_layout = QFormLayout(self.stellar_container)
        self.fe_h = ScientificIntInput(0.0, decimals=2)
        self.mg_h = ScientificIntInput(0.0, decimals=2)
        self.si_h = ScientificIntInput(0.0, decimals=2)
        self.ratio_input = QLineEdit("Fe/Si,Fe/Mg,Mg/Si")
        stellar_layout.addRow("Fe/H:", self.fe_h)
        stellar_layout.addRow("Mg/H:", self.mg_h)
        stellar_layout.addRow("Si/H:", self.si_h)
        stellar_layout.addRow("Ratio:", self.ratio_input)
        adv_layout.addRow(self.stellar_container)

        input_layout.addWidget(self.advanced_group)
        input_layout.addWidget(self.run_button)
        input_layout.addStretch()

        # Output Widgets
        self.results_table = QTableView()
        self.corner_plot = MplCanvas(self)
        self.mr_diagram = MplCanvas(self)
        self.explainer_text = QTextBrowser()

        # Corner plot tab layout to ensure resizing
        corner_widget = QWidget()
        corner_layout = QVBoxLayout(corner_widget)
        corner_layout.addWidget(self.corner_plot)
        
        output_panel.addTab(self.explainer_text, "Explainer")
        output_panel.addTab(self.mr_diagram, "M-R Diagram")
        output_panel.addTab(corner_widget, "Corner Plot")
        output_panel.addTab(self.results_table, "Results")

        self.run_button.clicked.connect(self.run_model)
        self.plot_mr_diagram_base()

    def toggle_rocky_mode(self, checked):
        if checked:
            self.planet_type.setCurrentText("Rocky")
            self.planet_type.setVisible(False)
            self.lbl_planet_type.setVisible(False)
            self.teq_input_widget.setVisible(False)
            self.lbl_teq.setVisible(False)
        else:
            self.planet_type.setVisible(True)
            self.lbl_planet_type.setVisible(True)
            self.teq_input_widget.setVisible(True)
            self.lbl_teq.setVisible(True)

    def toggle_advanced(self):
        is_visible = self.advanced_group.isVisible()
        self.advanced_group.setVisible(not is_visible)
        arrow = "▼" if not is_visible else "▲"
        self.advanced_btn.setText(f"Advanced Options {arrow}")

    def toggle_stellar(self, checked):
        self.stellar_container.setVisible(checked)

    def handle_selection(self):
        """WSL Fix: Manual popup management and focus return."""
        self.planet_type.hidePopup()
        self.setFocus()

    def plot_mr_diagram_base(self):
        try:
            # self.mr_data = pd.read_csv('testing/H2.csv')
            self.mr_diagram.axes.clear()
            # import superearth
            # self.mr_diagram.axes.scatter(self.mr_data['M'], self.mr_data['Rmean'], alpha=0.5, label='Known Exoplanets')
            self.mr_diagram.axes.set_xlabel("Mass (M_earth)")
            self.mr_diagram.axes.set_ylabel("Radius (R_earth)")
            self.mr_diagram.axes.set_xscale('log')
            self.mr_diagram.axes.set_yscale('log')
            self.mr_diagram.axes.legend()
            self.mr_diagram.draw()
        except FileNotFoundError:
            self.mr_diagram.axes.text(0.5, 0.5, 'H2.csv not found', ha='center', va='center')
            self.mr_diagram.draw()

    def run_model(self):
        self.run_button.setEnabled(False)
        self.run_button.setText("Running...")

        # Get parameters from GUI
        planet_type = "Rocky" if self.rocky_checkbox.isChecked() else self.planet_type.currentText()
        
        mass, mass_up, mass_low = self.mass_input_widget.get_values()
        radius, rad_up, rad_low = self.radius_input_widget.get_values()
        teq, teq_up, teq_low = self.teq_input_widget.get_values()
        
        n_samples = self.n_samples_input.value()

        # Advanced params
        xSi = [self.xsi_min.value(), self.xsi_max.value()]
        xFe = [self.xfe_min.value(), self.xfe_max.value()]
        
        star = None
        ratio = None
        if self.stellar_check.isChecked():
            star = [self.fe_h.value(), self.mg_h.value(), self.si_h.value()]
            ratio = self.ratio_input.text()

        # Create worker and thread
        self.thread = QThread()
        self.worker = Worker(
            planet_type, mass, [mass_up, mass_low], radius, [rad_up, rad_low], 
            n_samples, teq, [teq_up, teq_low], xSi, xFe, star, ratio
        )
        self.worker.moveToThread(self.thread)

        # Connect signals and slots
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_run_finished)
        self.worker.error.connect(self.show_error)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        # Start the thread
        self.thread.start()

    def on_run_finished(self, result):
        self.run_button.setEnabled(True)
        self.run_button.setText("Run")
        
        # Update results table
        results_data = {}
        for param in result._save_parameters:
            if hasattr(result, param):
                results_data[param] = getattr(result, param)
        
        df = pd.DataFrame(results_data)
        self.results_table.setModel(PandasModel(df.describe().transpose()))

        # Update corner plot
        self.corner_plot.figure.clear()
        if hasattr(result, 'corner'):
            self.corner_plot.figure = result.corner()[0]
            self.corner_plot.draw()
        else:
            ax = self.corner_plot.figure.add_subplot(111)
            ax.text(0.5, 0.5, 'Corner plot not available for this model.',
                    horizontalalignment='center', verticalalignment='center')
            self.corner_plot.draw()

        # Update M-R diagram
        self.plot_mr_diagram_base() # Redraw base plot
        mass = self.mass_input.value()
        radius = self.radius_input.value()
        mass_unc = self.mass_unc_input.value()
        radius_unc = self.radius_unc_input.value()
        self.mr_diagram.axes.errorbar(mass, radius, xerr=mass_unc, yerr=radius_unc, fmt='o', color='red', label='Your Planet')
        self.mr_diagram.axes.legend()
        self.mr_diagram.draw()

        # Update explainer tab
        self.update_explainer(result, df.describe())

    def update_explainer(self, result, describe_df):
        planet_type = result.type
        
        text = f"<h1>{planet_type.capitalize()} Planet Results</h1>"
        text += f"<p><b>Input Parameters:</b></p>"
        text += f"<ul>"
        text += f"<li>Mass: {self.mass_input.value()} +/- {self.mass_unc_input.value()} M_earth</li>"
        text += f"<li>Radius: {self.radius_input.value()} +/- {self.radius_unc_input.value()} R_earth</li>"
        if planet_type == 'envelope':
            text += f"<li>Teq: {self.teq_input.value()} +/- {self.teq_unc_input.value()} K</li>"
        text += f"</ul>"

        text += f"<p><b>Results:</b></p>"
        
        explainer_map = {
            'CMF': "<b>Core Mass Fraction (CMF):</b> The fraction of the planet's mass that is contained in its core.",
            'WMF': "<b>Water Mass Fraction (WMF):</b> The fraction of the planet's mass that is composed of water.",
            'AMF': "<b>Atmosphere Mass Fraction (AMF):</b> The fraction of the planet's mass that is in its gaseous envelope."
        }

        for param in result._save_parameters:
            if param in describe_df.index:
                mean = describe_df.loc[param]['mean']
                std = describe_df.loc[param]['std']
                text += f"<p>{explainer_map.get(param, f'<b>{param}</b>:')}</p>"
                text += f"<p>Mean: {mean:.3f}, Std Dev: {std:.3f}</p>"
        
        self.explainer_text.setHtml(text)


    def show_error(self, error_message):
        self.run_button.setEnabled(True)
        self.run_button.setText("Run")
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setText("An error occurred")
        msg.setInformativeText(error_message)
        msg.setWindowTitle("Error")
        msg.exec() 



if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_win = MainWindow(planet_name='TOI')
    main_win.show()
    sys.exit(app.exec()) 