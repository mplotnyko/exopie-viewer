
from PyQt6.QtCore import QObject, pyqtSignal
import exopie
import traceback

class Worker(QObject):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, planet_type, mass, mass_unc, radius, radius_unc, n_samples, 
                 teq=None, teq_unc=None, xSi=None, xFe=None, star=None, ratio=None):
        super().__init__()
        self.planet_type = planet_type
        self.mass = mass
        self.mass_unc = mass_unc
        self.radius = radius
        self.radius_unc = radius_unc
        self.n_samples = n_samples
        self.teq = teq
        self.teq_unc = teq_unc
        self.xSi = xSi
        self.xFe = xFe
        self.star = star
        self.ratio = ratio

    def run(self):
        try:
            planet_map = {
                "Rocky": exopie.rocky,
                "Water": exopie.water,
                "Envelope": exopie.envelope
            }
            
            planet_class = planet_map.get(self.planet_type)
            if not planet_class:
                self.error.emit(f"Unknown planet type: {self.planet_type}")
                return

            # Handle asymmetric uncertainties (list) or symmetric (float)
            if isinstance(self.mass_unc, (list, tuple)):
                mass_param = [self.mass, *self.mass_unc]
            else:
                mass_param = [self.mass, self.mass_unc]

            if isinstance(self.radius_unc, (list, tuple)):
                radius_param = [self.radius, *self.radius_unc]
            else:
                radius_param = [self.radius, self.radius_unc]
            
            kwargs = {
                'N': self.n_samples,
                'Mass': mass_param,
                'Radius': radius_param
            }
            
            if self.xSi: kwargs['xSi'] = self.xSi
            if self.xFe: kwargs['xFe'] = self.xFe

            if self.planet_type == "Envelope":
                if isinstance(self.teq_unc, (list, tuple)):
                    kwargs['Teq'] = [self.teq, *self.teq_unc]
                else:
                    kwargs['Teq'] = [self.teq, self.teq_unc]
            
            planet = planet_class(**kwargs)
            
            # Pass stellar constraints to run() if available
            run_kwargs = {}
            if self.star: run_kwargs['star'] = self.star
            if self.ratio: run_kwargs['ratio'] = self.ratio
            
            planet.run(**run_kwargs)
            self.finished.emit(planet)
        except Exception as e:
            self.error.emit(f"An error occurred: {e}\n{traceback.format_exc()}")
