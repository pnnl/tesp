import json
import math


def processLSEDataFixedDemandData(LSEDataFixedDemandDataRaw):
    """
    This function processes LSEDataFixedDemand Data
    """

    _LSEDataFixedDemand = {}
    lse_id_list = []
    hour = 0
    for lse_rec in LSEDataFixedDemandDataRaw:
        lse_rec_ary = lse_rec.strip().split('\t')
        if not lse_rec_ary[0] in lse_id_list:
            lse_id_list.append(lse_rec_ary[0])
            _LSEDataFixedDemand[str(lse_rec_ary[0])] = lse_rec_ary[1:]
            hour = len(lse_rec_ary) - 3
        else:
            _LSEDataFixedDemand[str(lse_rec_ary[0])].extend(lse_rec_ary[3:])

    for key, value in _LSEDataFixedDemand.items():
        value[0] = int(value[0].strip())
        value[1] = int(value[1].strip())
        for i in range(2, len(value)):
            value[i] = float(value[i])

    # detect re-occurance and attached it
    return _LSEDataFixedDemand


def processLSEDataPriceSensitiveDemand(LSEDataPriceSensitiveDemandRaw):
    """
    This function processes LSEDataPriceSensitiveDemand Data
    """

    temp_LSEDataPriceSensitiveDemand = {}
    lse_id_list = []

    for lse_rec in LSEDataPriceSensitiveDemandRaw:
        lse_rec_ary = lse_rec.strip().split('\t')

        if not lse_rec_ary[0] in lse_id_list:
            lse_id_list.append(lse_rec_ary[0])

            # // Name ID atBus hourIndex   c d  SLMax
            temp_LSEDataPriceSensitiveDemand[str(lse_rec_ary[0])] = {"ID": lse_rec_ary[1].strip(),
                                                                     "atBus": lse_rec_ary[2].strip(),
                                                                     "hour-" + lse_rec_ary[3].strip(): {
                                                                         "c": float(lse_rec_ary[4]),
                                                                         "d": float(lse_rec_ary[5]),
                                                                         "SLMax": float(lse_rec_ary[6])}}
        else:
            new_hour = {"hour-" + lse_rec_ary[3].strip(): {"c": float(lse_rec_ary[4]),
                                                           "d": float(lse_rec_ary[5]), "SLMax": float(lse_rec_ary[6])}}
            temp_LSEDataPriceSensitiveDemand[str(lse_rec_ary[0])].update(new_hour)

    return temp_LSEDataPriceSensitiveDemand


def get_hourly_bus_loadPQ(bus_i, hour, LSEDataFixedDemand, power_factor=0.9):
    loadP = 0
    loadQ = 0
    for load_id, load_rec in LSEDataFixedDemand.items():
        bus_i_idx = 1
        hour_rec_idx = hour + 2
        if load_rec[bus_i_idx] == bus_i:
            loadP = load_rec[hour_rec_idx]
            if power_factor != 0.0:
                loadQ = loadP * math.tan(math.acos(power_factor))

    return loadP, loadQ


def convertDataToMATPOWER(output_file, NodeData, output_bus_data, output_gen_data, output_branch_data,
                          output_gencost_data):
    # header
    output_file.write("function mpc = " + case_name[:-2])

    header_lines = r"""%% MATPOWER Case Format : Version 2
    mpc.version = '2';
    %% ======================================================================
    %% FNCS communication interface
    %% This has been added to simplify the set-up process
    %% ======================================================================
    % Number of buses where distribution networks are going to be connected to
    mpc.BusFNCSNum = 1;
    % Buses where distribution networks are going to be connected to
    mpc.BusFNCS = [ 7 ];
    % Number of distribution feeders (GridLAB-D instances)
    mpc.SubNumFNCS = 9;
    %% Substation names, and the transmission network bus where it is connected to
    mpc.SubNameFNCS = [ 1 7 ];

    %% ======================================================================
    %% For creating scenarios for visualization
    %% Setting up the matrix of generators that could become off-line
    % Number of generators that might be turned off-line
    mpc.offlineGenNum = 1;
    % Matrix contains the bus number of the corresponding off-line generators
    mpc.offlineGenBus = [ 2 ];       

    %% ======================================================================
    %% An amplification factor is used to simulate a higher load at the feeder end
    mpc.ampFactor = 20;
    %% ======================================================================"""

    output_file.write("\n" + header_lines)

    power_flow_header = r"""%%-----  Power Flow Data  -----%%
    %% system MVA base
    mpc.baseMVA = 100;"""

    output_file.write("\n" + power_flow_header)

    bus_data_dim = "mpc.busData = [ {} 13 ];".format(str(NodeData['node_number']))
    print(bus_data_dim)
    output_file.write("\n" + bus_data_dim)

    # ------------------------------------------------
    # ------------Bus data ----------------------------
    # -------------------------------------------------
    output_file.write("\n" + "mpc.bus = [\n")

    for bus_rec in output_bus_data.values():
        output_file.write("\t" + str(bus_rec)[1:-1] + ";\n")

    output_file.write("];\n")

    # ------------------------------------------------
    # ------------Gen data ----------------------------
    # -------------------------------------------------

    gen_data_dim = "mpc.genData = [ {} 21 ];".format(len(output_gen_data.keys()))
    output_file.write("\n" + gen_data_dim)

    output_file.write("\n" + "mpc.gen = [\n")

    for gen_rec in output_gen_data.values():
        output_file.write("\t" + str(gen_rec)[1:-1] + ";\n")

    output_file.write("];\n")

    # ------------------------------------------------
    # ------------Branch data -------------------------
    # -------------------------------------------------

    branch_data_dim = "mpc.branchData = [ {} 13 ];".format(len(output_branch_data.keys()))
    output_file.write("\n" + branch_data_dim)

    output_file.write("\n" + "mpc.branch = [\n")

    for bra_rec in output_branch_data.values():
        output_file.write("\t" + str(bra_rec)[1:-1] + ";\n")

    output_file.write("];\n")

    # ------------------------------------------------
    # ------------Area data -------------------------
    # -------------------------------------------------

    # ------------------------------------------------
    # ------------gen cost data -------------------------
    # -------------------------------------------------

    gencost_data_dim = "mpc.branchData = [ {} 7 ];".format(len(output_gencost_data.keys()))
    output_file.write("\n" + gencost_data_dim)

    output_file.write("\n" + "mpc.gencost = [\n")

    for gencost_rec in output_gencost_data.values():
        output_file.write("\t" + str(gencost_rec)[1:-1] + ";\n")

    output_file.write("];\n")


def convertDataToPYPowerJSON(output_file, NodeData, output_bus_data, output_gen_data, output_branch_data,
                             output_gencost_data):
    pp_case = {}
    pp_case["version"] = "2"
    pp_case["baseMVA"] = 100.0
    pp_case["bus"] = list(output_bus_data.values())
    pp_case["gen"] = list(output_gen_data.values())
    pp_case["branch"] = list(output_branch_data.values())
    pp_case["gencost"] = list(output_gencost_data.values())
    pp_case["DSO"] = [[
        7,
        "SUBSTATION7",
        400.0,
        "0.0"
    ]]

    pp_case["UnitsOut"] = list()
    pp_case["BranchesOut"] = list()
    pp_case["StartTime"] = "2013-07-01 00:00:00",
    pp_case["Tmax"] = 172800
    pp_case["Period"] = 3600
    pp_case["dt"] = 3600
    pp_case["CSVFile"] = "NonGLDLoad.txt"
    pp_case["opf_dc"] = 1
    pp_case["pf_dc"] = 0

    json.dump(pp_case, output_file)


# ======================================================================================================================
# ***********************************************************************************************************************
#                      Main execution part
# ***********************************************************************************************************************
# =======================================================================================================================

output_format = "MATPOWER"
# output_format = "JSON"

# case_name = "8BusTestCase10000"
case_name = "8BusTestCase5000"
# case_name = "8BusTestCase2000"
# case_name = "8BusTestCase1000"

input_file = open("../" + case_name + ".dat", 'r')

if output_format == 'MATPOWER':
    case_name = "mpc_{}.m".format(case_name)
else:
    case_name = "pp_{}.json".format(case_name)

output_file = open(case_name, 'w')

# specify the hour for outputting the case
hour = 0

# save the hourly load data as CSV?

isNodeDataStart = False
isNodeDataEnd = False
isBranchDataStart = False
isBranchDataEnd = False
isGenDataStart = False
isGenDataEnd = False
isLSEDataFixedDemandStart = False
isLSEDataFixedDemandEnd = False
isLSEDataPriceSensitiveDemandStart = False
isLSEDataPriceSensitiveDemandEnd = False
isLSEDataHybridDemandStart = False
isLSEDataHybridDemandEnd = False
isGenLearningDataStart = False
isGenLearningDataEnd = False

# -----------for storing the raw data------------------#
NodeDataRaw = []
BranchDataRaw = []
GenDataRaw = []
LSEDataFixedDemandRaw = []
LSEDataPriceSensitiveDemandRaw = []
LSEDataHybridDemandRaw = []
GenLearningDataRaw = []

# --------for storing data in a good format-----------#
NodeData = {}
BranchData = {}
GenData = {}
LSEDataFixedDemand = {}
LSEDataPriceSensitiveDemand = {}
LSEDataHybridDemand = {}
GenLearningData = {}

BASE_S = 0
BASE_V = 0
Max_Day = 0

bus_with_largest_gen_cap = 0
largest_gen_cap = 0.0

# --------for storing data for output-----------#
output_BusData = {}
output_GenData = {}
output_BranchData = {}
output_GenCostData = {}

version = "2",
baseMVA = 100.0

line_num = 0
for line in input_file:
    line_num = line_num + 1
    if line[0:2] == "//":
        # print("skip comment line, line #",line_num, line)
        continue
    elif "BASE_S" in line:

        temp_ary = line.strip().split('\t')
        print(temp_ary)
        BASE_S = float(temp_ary[1])
    elif "BASE_V" in line:

        temp_ary = line.strip().split('\t')
        print(temp_ary)
        BASE_V = float(temp_ary[1])
    elif "Max_Day" in line:

        temp_ary = line.strip().split('\t')
        print(temp_ary)
        Max_Day = float(temp_ary[1])
    elif "#NodeDataStart" in line:
        isNodeDataStart = True
        continue
    elif "#NodeDataEnd" in line:
        isNodeDataStart = False
        isNodeDataEnd = True
        continue
    elif "#BranchDataStart" in line:
        isBranchDataStart = True
        continue
    elif "#BranchDataEnd" in line:
        isBranchDataStart = False
        isBranchDataEnd = True
        continue
    elif "#GenDataStart" in line:
        isGenDataStart = True
        continue
    elif "#GenDataEnd" in line:
        isGenDataStart = False
        isGenDataEnd = False
        continue

    elif "#LSEDataFixedDemandStart" in line:
        isLSEDataFixedDemandStart = True
        continue
    elif "#LSEDataFixedDemandEnd" in line:
        isLSEDataFixedDemandStart = False
        isLSEDataFixedDemandEnd = True
        continue

    elif "#LSEDataPriceSensitiveDemandStart" in line:
        isLSEDataPriceSensitiveDemandStart = True
        continue
    elif "#LSEDataPriceSensitiveDemandEnd" in line:
        isLSEDataPriceSensitiveDemandStart = False
        isLSEDataPriceSensitiveDemandEnd = True
        continue

    if isNodeDataStart and (not isNodeDataEnd):
        NodeDataRaw.append(line)

    if isBranchDataStart and (not isBranchDataEnd):
        BranchDataRaw.append(line)
    if isGenDataStart and (not isGenDataEnd):
        GenDataRaw.append(line)
    if isLSEDataFixedDemandStart and (not isLSEDataFixedDemandEnd):
        LSEDataFixedDemandRaw.append(line)
    if isLSEDataPriceSensitiveDemandStart and (not isLSEDataPriceSensitiveDemandEnd):
        LSEDataPriceSensitiveDemandRaw.append(line)

for node_rec in NodeDataRaw:
    NodeDataAry = node_rec.strip().split('\t')
    NodeData['node_number'] = int(NodeDataAry[0])
    NodeData['penalty_weight'] = float(NodeDataAry[1])

for bra_rec in BranchDataRaw:
    BranchDataAry = bra_rec.strip().split('\t')
    BranchData[str(BranchDataAry[0])] = {"From": int(BranchDataAry[1].strip()), "To": int(BranchDataAry[2].strip()),
                                         "MaxCap": float(BranchDataAry[3]), "Reactance": float(BranchDataAry[4])}

for gen_rec in GenDataRaw:
    GenDataAry = gen_rec.strip().split('\t')
    GenData[str(GenDataAry[0])] = {"ID": str(GenDataAry[1].strip()), "atBus": int(GenDataAry[2].strip()),
                                   "FCost": float(GenDataAry[3]), "a": float(GenDataAry[4]),
                                   "b": float(GenDataAry[5]), "capL": float(GenDataAry[6]),
                                   "capU": float(GenDataAry[7]), "InitMoney": float(GenDataAry[8])}
    if largest_gen_cap < float(GenDataAry[7]):
        largest_gen_cap = float(GenDataAry[7])
        bus_with_largest_gen_cap = int(GenDataAry[2].strip())

LSEDataFixedDemand = processLSEDataFixedDemandData(LSEDataFixedDemandRaw)

LSEDataPriceSensitiveDemand = processLSEDataPriceSensitiveDemand(LSEDataPriceSensitiveDemandRaw)

print("node data:", NodeData)

print("Branch data:", BranchData)

print("Gen data:", GenData)

print("LSE Fixed Demand data:", LSEDataFixedDemand)

print("LSE Price sensitive demand data:", LSEDataPriceSensitiveDemand)

##########TODO adapt the data to matpower format #############


# busData
bus_num_list = []

for bra_id, bra_rec in BranchData.items():
    print(bra_rec["From"], bra_rec["To"])
    if bra_rec["From"] not in bus_num_list:
        bus_num_list.append(bra_rec["From"])
    if bra_rec["To"] not in bus_num_list:
        bus_num_list.append(bra_rec["To"])

for i in bus_num_list:
    bus_rec = []

    bus_i = int(i)
    bus_type = 1
    # make the bus with largest gen cap as the reference(or swing) bus
    if bus_i == bus_with_largest_gen_cap:
        bus_type = 3
    PD, QD = get_hourly_bus_loadPQ(i, hour, LSEDataFixedDemand, power_factor=0.90)
    GS = 0
    BS = 0
    bus_area = 1
    VM = 1.0
    VA = 0.0
    base_kV = BASE_V
    zone = 1
    Vmax = 1.05
    Vmin = 0.95

    bus_rec = [bus_i, bus_type, PD, QD, GS, BS, bus_area, VM, VA, base_kV, zone, Vmax, Vmin]

    output_BusData[bus_i] = bus_rec

print(output_BusData)

# genData

for gen_id, gen_rec in GenData.items():
    bus_num = gen_rec['atBus']
    PG = 0
    QG = 0
    PMAX = gen_rec["capU"]
    PMIN = gen_rec["capL"]
    QMAX = PMAX  # assumption here
    QMIN = -PMAX  # assumption here
    VG = 1.0
    MBASE = PMAX
    GEN_STATUS = 1

    Other_values = [0] * 10
    out_gen_rec = [bus_num, PG, QG, QMAX, QMIN, VG, MBASE, GEN_STATUS, PMAX, PMIN]
    out_gen_rec.extend(Other_values)

    output_GenData[gen_id] = out_gen_rec

print(output_GenData)

# branch data

base_Z = BASE_V * BASE_V / baseMVA

for bra_id, bra_rec in BranchData.items():
    f_bus = bra_rec["From"]
    t_bus = bra_rec["To"]
    r = 0
    x = bra_rec["Reactance"] / base_Z
    b = 0
    rate_a = bra_rec["MaxCap"]
    rate_b = 0
    rate_c = 0
    tap = 1
    shift = 0
    br_status = 1
    ang_min = -360
    ang_max = 360

    out_bra_rec = [f_bus, t_bus, r, x, b, rate_a, rate_b, rate_c, tap, shift, br_status, ang_min, ang_max]

    output_BranchData[bra_id] = out_bra_rec

print(output_BranchData)

# generator cost data


for gen_id, gen_rec in GenData.items():
    model = 2
    start_up = gen_rec["InitMoney"]
    shut_down = 0
    ncost = 3
    c2 = gen_rec["b"]
    c1 = gen_rec["a"]
    c0 = gen_rec["FCost"]

    out_gen_rec = [model, start_up, shut_down, ncost, c2, c1, c0]

    output_GenCostData[gen_id] = out_gen_rec

if output_format == "MATPOWER":
    convertDataToMATPOWER(output_file, NodeData, output_BusData, output_GenData, output_BranchData,
                          output_GenCostData)
else:
    convertDataToPYPowerJSON(output_file, NodeData, output_BusData, output_GenData, output_BranchData,
                             output_GenCostData)
