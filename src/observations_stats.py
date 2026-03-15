from pyinaturalist import *


class ObservationsStats(Observations):

    def filter_by_year(self, year: int):
        return ObservationsStats([obs for obs in self.data if obs.observed_on.year == year])