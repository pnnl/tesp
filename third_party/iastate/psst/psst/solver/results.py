import pandas as pd
import click

class PSSTResults(object):

    def __init__(self, model):

        self._model = model
        self._maximum_hours = 24

    @property
    def production_cost(self):
        m = self._model
        st = 'SecondStage'
        return sum([m.ProductionCost[g, t].value for t in m.GenerationTimeInStage[st] if t < self._maximum_hours for g in m.Generators])

    @property
    def commitment_cost(self):
        m = self._model
        st = 'FirstStage'
        return sum([m.StartupCost[g, t].value + m.ShutdownCost[g, t].value for g in m.Generators for t in m.CommitmentTimeInStage[st] if t < self._maximum_hours])

    @property
    def noload_cost(self):
        m = self._model
        st = 'FirstStage'
        return sum([sum([m.UnitOn[g, t].value for t in m.CommitmentTimeInStage[st] if t < self._maximum_hours]) * m.MinimumProductionCost[g].value * m.TimePeriodLength.value for g in m.Generators])

    @property
    def unit_commitment(self):
        df = self._get('UnitOn', self._model)
        return df.clip_lower(0)

    @property
    def line_power(self):
        return self._get('LinePower', self._model)

    @property
    def angles(self):
        return self._get('Angle', self._model)

    @property
    def maximum_power_available(self):
        return self._get('MaximumPowerAvailable', self._model)

    @property
    def minimum_power_available(self):
        return self._get('MinimumPowerAvailable', self._model)

    @property
    def power_generated(self):
        return self._get('PowerGenerated', self._model)

    @property
    def slack_variables(self):
        return self._get('LoadGenerateMismatch', self._model)

    @property
    def regulating_reserve_up_available(self):
        return self._get('RegulatingReserveUpAvailable', self._model)

    @property
    def maximum_power_output(self):
        return self._get('MaximumPowerOutput', self._model, self._model.Generators)

    @property
    def maximum_line_power(self):
        return self._get('ThermalLimit', self._model, self._model.TransmissionLines)

    @property
    def lmp(self):
        return self._get('PowerBalance', self._model, dual=True)

    @property
    def reserve_zonal_down_dual(self):
        return self._get('EnforceZonalReserveDownRequirements', self._model, dual=True)

    @property
    def reserve_zonal_up_dual(self):
        return self._get('EnforceZonalReserveUpRequirements', self._model, dual=True)

    @staticmethod
    def _get(attribute, model, set1=None, set2=None, dual=False):
        _dict = dict()

        if set1 is not None and set2 is None:
            for s1 in set1:
                _dict[s1] = getattr(model, attribute)[s1]

            return pd.Series(_dict)

        else:
            if set1 is None and set2 is None:
                set1 = set()
                set2 = set()
                index = getattr(model, attribute + '_index')
                for i, j in index:
                    set1.add(i)
                    set2.add(j)


            for s1 in set1:
                _dict[s1] = list()

                for s2 in set2:
                    if dual is True:
                        _dict[s1].append(model.dual.get(getattr(model, attribute)[s1, s2]))
                    else:
                        _dict[s1].append(getattr(model, attribute)[s1, s2].value)

            return pd.DataFrame(_dict)

