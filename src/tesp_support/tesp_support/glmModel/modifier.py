import json
import math

# from src.tesp_support.tesp_support.glmModel.model import GLModel
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
    config_data = {}
    c_p_frac = 0.0

    # fgconfig: path and name of the file that is to be used as the configuration json for loading
    # ConfigDict dictionary
    def initialize_config_dict(self, fgconfig):
        if fgconfig is not None:
            with open(fgconfig, 'r') as fgfile:
                confile = fgfile.read()
                self.config_data = json.loads(confile)
                fgfile.close()
            tval2 = self.config_data['feedergenerator']['constants']
            self.config_data = tval2
            cval1 = self.config_data['c_z_frac']['value']
            cval2 = self.config_data['c_i_frac']['value']
            self.c_p_frac = 1.0 - cval1 - cval2

    def _get_batteries(self):
        return self.batteries

    def _get_billing_meters(self):
        return self.meters

    def _get_capacitors(self):
        return self.capacitors

    def _get_fuses(self):
        return self.fuses

    def _get_houses(self):
        return self.houses

    def _get_lines(self):
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
        # self.initialize_config_dict("FeederGenerator.json")
        tlist = list(self.model.network.nodes.data())
        for basenode in tlist:
            print(basenode)
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

    def write_mod_model(self, filepath):
        return True

    def create_kersting_quadriplex(self, kva):
        kerst_quad_dict = dict()
        kerst_quad_dict["key"] = 'quad_cfg_{:d}'.format(int(kva))
        kerst_quad_dict["amps"] = kva / math.sqrt(3.0) / 0.208
        kerst_quad_dict["npar"] = math.ceil(kerst_quad_dict["amps"] / 202.0)
        kerst_quad_dict["apar"] = 202.0 * kerst_quad_dict["npar"]
        kerst_quad_dict["scale"] = 5280.0 / 100.0 / kerst_quad_dict[
            "npar"]  # for impedance per mile of parallel circuits
        kerst_quad_dict["r11"] = 0.0268 * kerst_quad_dict["scale"]
        kerst_quad_dict["x11"] = 0.0160 * kerst_quad_dict["scale"]
        kerst_quad_dict["r12"] = 0.0160 * kerst_quad_dict["scale"]
        kerst_quad_dict["x12"] = 0.0103 * kerst_quad_dict["scale"]
        kerst_quad_dict["r13"] = 0.0085 * kerst_quad_dict["scale"]
        kerst_quad_dict["x13"] = 0.0095 * kerst_quad_dict["scale"]
        kerst_quad_dict["r22"] = 0.0258 * kerst_quad_dict["scale"]
        kerst_quad_dict["x22"] = 0.0176 * kerst_quad_dict["scale"]
        return kerst_quad_dict


# Helper functions
#    def write_node_house_configs (self, fp, xfkva, xfkvll, xfkvln, phs, want_inverter=False):
#      """Writes transformers, inverter settings for GridLAB-D houses at a primary load point.

# An aggregated single-phase triplex or three-phase quadriplex line configuration is also
# written, based on estimating enough parallel 1/0 AA to supply xfkva load.
# This function should only be called once for each combination of xfkva and phs to use,
# and it should be called before write_node_houses.

# Args:
#    fp (file): Previously opened text file for writing; the caller closes it.
#    xfkva (float): the total transformer size to serve expected load; make this big enough to avoid overloads
#    xfkvll (float): line-to-line voltage [kV] on the primary. The secondary voltage will be 208 three-phase
#    xfkvln (float): line-to-neutral voltage [kV] on the primary. The secondary voltage will be 120/240 for split secondary
#    phs (str): either 'ABC' for three-phase, or concatenation of 'A', 'B', and/or 'C' with 'S' for single-phase to triplex
#    want_inverter (boolean): True to write the IEEE 1547-2018 smarter inverter function setpoints
# """
# if want_inverter:
#    print ('#define INVERTER_MODE=CONSTANT_PF', file=fp)
#    print ('//#define INVERTER_MODE=VOLT_VAR', file=fp)
#    print ('//#define INVERTER_MODE=VOLT_WATT', file=fp)
#    print ('// default IEEE 1547-2018 settings for Category B', file=fp)
#    print ('#define INV_V1=0.92', file=fp)
#    print ('#define INV_V2=0.98', file=fp)
#    print ('#define INV_V3=1.02', file=fp)
#    print ('#define INV_V4=1.08', file=fp)
#    print ('#define INV_Q1=0.44', file=fp)
#    print ('#define INV_Q2=0.00', file=fp)
#    print ('#define INV_Q3=0.00', file=fp)
#    print ('#define INV_Q4=-0.44', file=fp)
#    print ('#define INV_VIN=200.0', file=fp)
#    print ('#define INV_IIN=32.5', file=fp)
#    print ('#define INV_VVLOCKOUT=300.0', file=fp)
#    print ('#define INV_VW_V1=1.05 // 1.05833', file=fp)
#    print ('#define INV_VW_V2=1.10', file=fp)
#    print ('#define INV_VW_P1=1.0', file=fp)
#    print ('#define INV_VW_P2=0.0', file=fp)
#    if 'S' in phs:
#        for secphs in phs.rstrip('S'):
#            xfkey = 'XF{:s}_{:d}'.format (secphs, int(xfkva))
#            write_xfmr_config (xfkey, secphs + 'S', kvat=xfkva, vnom=None, vsec=120.0, install_type='PADMOUNT', vprimll=None, vprimln=1000.0*xfkvln, op=fp)
#            self.create_kersting_triplex (fp, xfkva)
#    else:
#        xfkey = 'XF3_{:d}'.format (int(xfkva))
#        write_xfmr_config (xfkey, phs, kvat=xfkva, vnom=None, vsec=208.0, install_type='PADMOUNT', vprimll=1000.0*xfkvll, vprimln=None, op=fp)
#        self.create_kersting_quadriplex (fp, xfkva)


def create_kersting_triplex(self, kva):
    """Writes a triplex_line_configuration based on 1/0 AA example from Kersting's book

    The conductor capacity is 202 amps, so the number of triplex in parallel will be kva/0.12/202
    """
    kerst_trip_dict = dict()
    kerst_trip_dict["key"] = 'tpx_cfg_{:d}'.format(int(kva))
    kerst_trip_dict["amps"] = kva / 0.12
    kerst_trip_dict["npar"] = math.ceil(kerst_trip_dict["amps"] / 202.0)
    kerst_trip_dict["apar"] = 202.0 * kerst_trip_dict["npar"]
    kerst_trip_dict["scale"] = 5280.0 / 100.0 / kerst_trip_dict["npar"]  # for impedance per mile of parallel circuits
    kerst_trip_dict["r11"] = 0.0271 * kerst_trip_dict["scale"]
    kerst_trip_dict["x11"] = 0.0146 * kerst_trip_dict["scale"]
    kerst_trip_dict["r12"] = 0.0087 * kerst_trip_dict["scale"]
    kerst_trip_dict["x12"] = 0.0081 * kerst_trip_dict["scale"]
    return kerst_trip_dict


def write_xfmr_config(self, key, phs, kvat, vnom, vsec, install_type, vprimll, vprimln):
    """Write a transformer_configuration

    Args:
        key (str): name of the configuration
        phs (str): primary phasing
        kvat (float): transformer rating in kVA
        vnom (float): primary voltage rating, not used any longer (see vprimll and vprimln)
        vsec (float): secondary voltage rating, should be line-to-neutral for single-phase or line-to-line for three-phase
        install_type (str): should be VAULT, PADMOUNT or POLETOP
        vprimll (float): primary line-to-line voltage, used for three-phase transformers
        vprimln (float): primary line-to-neutral voltage, used for single-phase transformers
        op (file): an open GridLAB-D input file
    """
    xfmr_config_dict = dict()
    #    print('object transformer_configuration {', file=op)
    # print('  name ' + ConfigDict['name_prefix']['value'] + key + ';', file=op)
    xfmr_config_dict["name"] = self.config_data['name_prefix']['value'] + key + ";"
    # print('  power_rating ' + format(kvat, '.2f') + ';', file=op)
    xfmr_config_dict['power_rating'] = format(kvat, '.2f') + ';'
    kvaphase = kvat
    if 'XF2' in key:
        kvaphase /= 2.0
    if 'XF3' in key:
        kvaphase /= 3.0
    if 'A' in phs:
        xfmr_config_dict['powerA_rating'] = format(kvaphase, '.2f')
    else:
        xfmr_config_dict['powerA_rating'] = '0.0'
    if 'B' in phs:
        xfmr_config_dict['powerB_rating'] = format(kvaphase, '.2f')
    else:
        xfmr_config_dict['powerB_rating'] = '0.0'
    if 'C' in phs:
        xfmr_config_dict['powerC_rating'] = format(kvaphase, '.2f')
    else:
        xfmr_config_dict['powerC_rating'] = '0.0'
    xfmr_config_dict['powerC_rating'] = install_type
    if 'S' in phs:
        row = self.Find1PhaseXfmr(kvat)
        xfmr_config_dict['connect_type'] = 'SINGLE_PHASE_CENTER_TAPPED'
        xfmr_config_dict['primary_voltage'] = str(vprimln)
        xfmr_config_dict['secondary_voltage'] = format(vsec, '.1f')
        xfmr_config_dict['resistance'] = format(row[1] * 0.5, '.5f')
        xfmr_config_dict['resistance1'] = format(row[1], '.5f')
        xfmr_config_dict['resistance2'] = format(row[1], '.5f')
        xfmr_config_dict['reactance'] = format(row[2] * 0.8, '.5f')
        xfmr_config_dict['reactance1'] = format(row[2] * 0.4, '.5f')
        xfmr_config_dict['reactance2'] = format(row[2] * 0.4, '.5f')
        xfmr_config_dict['shunt_resistance'] = format(1.0 / row[3], '.2f')
        xfmr_config_dict['shunt_reactance'] = format(1.0 / row[4], '.2f')
    else:
        row = self.Find3PhaseXfmr(kvat)
        xfmr_config_dict['connect_type'] = 'WYE_WYE'
        xfmr_config_dict['primary_voltage'] = str(vprimll)
        xfmr_config_dict['secondary_voltage'] = format(vsec, '.1f')
        xfmr_config_dict['resistance'] = format(row[1], '.5f')
        xfmr_config_dict['reactance'] = format(row[2], '.5f')
        xfmr_config_dict['shunt_resistance'] = format(1.0 / row[3], '.2f')
        xfmr_config_dict['shunt_reactance'] = format(1.0 / row[4], '.2f')
        return xfmr_config_dict

    def Find3PhaseXfmr(self, kva):
        """Select a standard 3-phase transformer size, with data

        Standard sizes are 30, 45, 75, 112.5, 150, 225, 300, 500, 750, 1000, 1500,
        2000, 2500, 3750, 5000, 7500 or 10000 kVA

        Args:
            kva (float): the minimum transformer rating

        Returns:
            [float,float,float,float,float]: the kva, %r, %x, %no-load loss, %magnetizing current
        """
        for row in self.config_data['three_phase']['value']:
            if row[0] >= kva:
                return row[0], 0.01 * row[1], 0.01 * row[2], 0.01 * row[3], 0.01 * row[4]
        return Find3PhaseXfmrKva(kva), 0.01, 0.08, 0.005, 0.01

    def Find3PhaseXfmr(self, kva):
        """Select a standard 3-phase transformer size, with data

        Standard sizes are 30, 45, 75, 112.5, 150, 225, 300, 500, 750, 1000, 1500,
        2000, 2500, 3750, 5000, 7500 or 10000 kVA

        Args:
            kva (float): the minimum transformer rating

        Returns:
            [float,float,float,float,float]: the kva, %r, %x, %no-load loss, %magnetizing current
        """
        for row in self.config_data['three_phase']['value']:
            if row[0] >= kva:
                return row[0], 0.01 * row[1], 0.01 * row[2], 0.01 * row[3], 0.01 * row[4]
        return Find3PhaseXfmrKva(kva), 0.01, 0.08, 0.005, 0.01

    def Find1PhaseXfmr(self, kva):
        """Select a standard 1-phase transformer size, with data

        Standard sizes are 5, 10, 15, 25, 37.5, 50, 75, 100, 167, 250, 333 or 500 kVA

        Args:
            kva (float): the minimum transformer rating

        Returns:
            [float,float,float,float,float]: the kva, %r, %x, %no-load loss, %magnetizing current
        """
        for row in self.config_data['single_phase']['value']:
            if row[0] >= kva:
                return row[0], 0.01 * row[1], 0.01 * row[2], 0.01 * row[3], 0.01 * row[4]
        return Find1PhaseXfmrKva(kva), 0.01, 0.06, 0.005, 0.01

    def Find1PhaseXfmrKva(kva):
        """Select a standard 1-phase transformer size, with some margin

        Standard sizes are 5, 10, 15, 25, 37.5, 50, 75, 100, 167, 250, 333 or 500 kVA

        Args:
            kva (float): the minimum transformer rating

        Returns:
            float: the kva size, or 0 if none found
        """
        # kva *= xfmrMargin
        kva *= self.config_data['xmfr']['xfmrMargin']['value']
        for row in self.config_data['single_phase']['value']:
            if row[0] >= kva:
                return row[0]
        n500 = int((kva + 250.0) / 500.0)
        return 500.0 * n500

    def Find3PhaseXfmrKva(self, kva):
        """Select a standard 3-phase transformer size, with some margin

        Standard sizes are 30, 45, 75, 112.5, 150, 225, 300, 500, 750, 1000, 1500,
        2000, 2500, 3750, 5000, 7500 or 10000 kVA

        Args:
            kva (float): the minimum transformer rating


        Returns:
            float: the kva size, or 0 if none found
        """
        # kva *= xfmrMargin
        kva = self.config_data['xmfr']['xfmrMargin']['value']
        for row in self.config_data['three_phase']['value']:
            if row[0] >= kva:
                return row[0]
        n10 = int((kva + 5000.0) / 10000.0)
        return 500.0 * n10
