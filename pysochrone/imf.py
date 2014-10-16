from astropy import units as u
import numpy as np


class BaseInitialMassFunction(object):

    def __call__(self, mass):
        mass = u.Quantity(mass, 'Msun')
        return self._evaluate_xi(mass)

class SalpeterIMF(BaseInitialMassFunction):
    alpha = 2.3
    def _evaluate_xi(self, mass):
        return np.power(mass.value, -self.alpha)


class KroupaIMF(BaseInitialMassFunction):

    alpha = [0.3, 1.3, 2.3]
    mass_threshold = [0, 0.08, 0.5] * u.Msun
    def _evaluate_xi(self, mass):
        pass


