import h5py
import pandas as pd
from scipy import interpolate

class BaseIsochroneInterpolator(object):
    pass

class BastiIsochroneInterpolator(BaseIsochroneInterpolator):
    age_column_name = 'age'
    metallicity_column_name = 'feh'
    mass_column_name = 'mass_in'

    @classmethod
    def from_hdf5(cls, fname):
        isochrone_panel = pd.read_hdf(fname, 'isochrones')
        return cls(isochrone_panel)


    def __init__(self, isochrone_panel, interpolator=interpolate.LinearNDInterpolator):
        self.isochrone_panel = isochrone_panel

        self.isochrone_data_columns = self._get_data_columns()

        self.point_data_columns = [item for item in self.isochrone_data_columns
                                   if item != self.mass_column_name]

        age_metallicity_points = self.isochrone_panel.major_axis.tolist()
        age_metallicity_values = [self.isochrone_panel.major_xs(idx).values
                                  for idx in age_metallicity_points]

        self.interpolator = interpolator(
            age_metallicity_points, age_metallicity_values)


    def _get_data_columns(self):
        data_columns = (set(self.isochrone_panel.items) -
                        {self.age_column_name, self.metallicity_column_name})
        return [item for item in self.isochrone_panel.items
                if item in data_columns]


    def interpolate_isochrone(self, age, metallicity):
        interp_data = self.interpolator([age, metallicity])
        return pd.DataFrame(interp_data[0], columns=self.isochrone_data_columns)

    def interpolate_point(self, age, metallicity, mass):
        isochrone = self.interpolate_isochrone(age, metallicity)
        interp_point = interpolate.interp1d(
            isochrone[self.mass_column_name].values,
            isochrone[self.point_data_columns].values.T, bounds_error=False,
            fill_value=1e99)(mass)

        return pd.Series(interp_point, self.point_data_columns)


