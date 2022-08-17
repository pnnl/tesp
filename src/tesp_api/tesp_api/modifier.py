import model

#from src.tesp_support.tesp_support.glmModel.model import GLModel
from model import GLModel


class GLMModifier:
    batteries = list()
    billing_meters = list()
    capacitors = list()
    fuses = list()
    houses = list()
    lines = list()
    loads = list()
    model = GLModel()
    modded_model = GLModel()
    secondary_transformers = list()
    solar_pvs = list()
    substation_transformers = list()
    switches = list()
    triplex_lines = list()
    triplex_loads = list()
    zip_loads = list()

    def _get_batteries(self):
        return self.batteries

    def _get_billing_meters(self):
        return self.meters

    def _get_capacitors(self):
        return self.capacitors

    def  _get_fuses(self):
        return self.fuses

    def  _get_houses(self):
        return self.houses

    def  _get_lines(self):
        return self.lines

    def _get_loads(self):
        return self.loads

    def _get_secondary_transformers(self):
        return self.secondary_transformers

    def _get_solar_pvs(self):
        return self.solar_pvs

    def _get_substation_transformer(self):
        return self.substation_transformers

    def _get_switches(self):
        return self.switches

    def _get_triplex_lines(self):
        return self.triplex_lines

    def _get_triplex_loads(self):
        return self.triplex_loads

    def _get_zip_loads(self):
        return self.zip_loads

    def add_obj_to_billing_meters(self):
        return True

    def add_obj_to_houses(self):
        return True

    def add_recorder(self):
        return True

    def create_billing_meters(self):
        return True

    def get_downstream(self):
        return True

    def get_model(self):
        return self.model

    def get_obj(self):
        return True

    def get_path_to_substation(self):
        return True

    def init(self):
        return True

    def mod_model(self):
        return True



    def read_model(self, filepath):
        self.model.read_glm(filepath)
        return True



    def remove_batteries(self):
        return True

    def remove_houses(self):
        return True

    def remove_objs(self):
        return True

    def remove_solar_pv(self):
        return True

    def resize_component(self):
        return True

    def resize_fuses(self):
        return True

    def resize_lines(self):
        return True

    def resize_secondary_transformers(self):
        return True

    def resize_substation_transformer(self):
        return True

    def resize_triplex_lines(self):
        return True




    def set_model(self):
        return True



    def set_simulation_times(self):
        return True

    def write_model(self):
        return True

    def write_mod_model(self,filepath):
        return True
