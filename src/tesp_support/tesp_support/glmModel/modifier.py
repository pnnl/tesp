import GLMModel

class GLMModifier:
    batteries = list()
    billing_meters = list()
    capacitors = list()
    fuses = list()
    houses = list()
    lines = list()
    loads = list()
    model = GLModel()
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

    def add_obj_to_houses(self):

    def add_recorder(self):

    def create_billing_meters(self):

    def get_downstream(self):



    def get_model(self):
        return self.model

    def get_obj(self):

    def get_path_to_substation(self):

    def init(self):

    def read_model(self):

    def remove_batteries(self):

    def remove_houses(self):

    def remove_objs(self):

    def remove_solar_pv(self):

    def resize_component(self):

    def resize_fuses(self):

    def resize_lines(self):

    def resize_secondary_transformers(self):

    def resize_substation_transformer(self):

    def resize_triplex_lines(self):

    def set_model(self):

    def set_simulation_times(self):

    def write_model(self):
