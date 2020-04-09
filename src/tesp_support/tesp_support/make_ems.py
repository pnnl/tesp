# Copyright (C) 2020 Battelle Memorial Institute
# file: make_ems.py
"""Creates the EMS for an EnergyPlus building model

Public Functions:
  :make_ems: Creates the energy management system (EMS) for FNCS/HELICS to interface with EnergyPlus.
"""
import sys
import re
#import tesp_support.helpers as helpers
import csv

if sys.platform == 'win32':
  pycall = 'python'
else:
  pycall = 'python3'

def schedule_sensor(name, op):
  print ('  EnergyManagementSystem:Sensor,', file=op)
  print ('    {:s},  !- Name'.format (name), file=op)
  print ('    {:s},  !- Output:Variable or Output:Meter Index Key Name'.format (name), file=op)
  print ('    Schedule Value;    !- Output:Variable or Output:Meter Name', file=op)

def schedule_actuator(name, target, op):
  print ('  EnergyManagementSystem:Actuator,', file=op)
  print ('    {:s},  !- Name'.format (name), file=op)
  print ('    {:s},  !- Actuated Component Unique Name'.format (target), file=op)
  print ('    Schedule:Compact, !- Actuated Component Type', file=op)
  print ('    Schedule Value;   !- Actuated Component Control Type', file=op)

def global_variable(name, op):
  print ('  EnergyManagementSystem:GlobalVariable,', file=op)
  print ('    {:s};'.format (name), file=op)

def output_variable(name, target, op):
  print ('  EnergyManagementSystem:OutputVariable,', file=op)
  print ('    {:s},  !- Name'.format (name), file=op)
  print ('    {:s},  !- EMS Variable Name'.format (target), file=op)
  print ('    Averaged,     !- Type of Data in Variable', file=op)
  print ('    ZoneTimeStep, !- Update Frequency', file=op)
  print ('    ,             !- EMS Program or Subroutine Name', file=op)
  print ('    ;             !- Units', file=op)

def heating_coil_sensor(name, target, op):
  print ('  EnergyManagementSystem:Sensor,', file=op)
  print ('    {:s},  !- Name'.format (name), file=op)
  print ('    {:s},  !- Coil'.format (target), file=op)
  print ('    Heating Coil Electric Energy;', file=op)

def cooling_coil_sensor(name, target, op):
  print ('  EnergyManagementSystem:Sensor,', file=op)
  print ('    {:s},  !- Name'.format (name), file=op)
  print ('    {:s},  !- Coil'.format (target), file=op)
  print ('    Cooling Coil Electric Energy;', file=op)

def zone_temperature_sensor(name, op):
  print ('  EnergyManagementSystem:Sensor,', file=op)
  print ('    {:s}_T,  !- Name'.format (name), file=op)
  print ('    {:s},    !- Zone'.format (name), file=op)
  print ('    Zone Mean Air Temperature;', file=op)

def zone_heating_sensor(name, op):
  print ('  EnergyManagementSystem:Sensor,', file=op)
  print ('    {:s}_H,                   !- Name'.format (name), file=op)
  print ('    {:s} VAV Box Reheat Coil, !- Zone/Coil'.format (name), file=op)
  print ('    Heating Coil Heating Energy;', file=op)

def zone_sensible_heating_sensor(name, op):
  print ('  EnergyManagementSystem:Sensor,', file=op)
  print ('    {:s}_H,  !- Name'.format (name), file=op)
  print ('    {:s},    !- Zone'.format (name), file=op)
  print ('    Zone Air System Sensible Heating Rate;', file=op)

def zone_sensible_cooling_sensor(name, op):
  print ('  EnergyManagementSystem:Sensor,', file=op)
  print ('    {:s}_C,  !- Name'.format (name), file=op)
  print ('    {:s},    !- Zone'.format (name), file=op)
  print ('    Zone Air System Sensible Cooling Rate;', file=op)

def get_eplus_token (sval):
  val = sval.strip()
  idx = val.rfind(';')
  if idx < 0:
    idx = val.rfind(',')
  return val[:idx].upper()

def summarize_idf (fname, baseidf):
  schedules = {}
  thermostats = {}
  zonecontrols = {}
  zones = {}
  hvacs = set()
  ccoils = {}
  hcoils = {}
  volume = 0
  nzones = 0
  ncontrols = 0
  nsetpoints = 0
  nschedused = 0
  idx_ccoil = 1
  idx_hcoil = 1

  fp = open(fname, 'r')
  rdr = csv.reader (fp)
  for row in rdr:
    if row[0].strip() == 'Component Sizing Information':
      if row[1].strip() == 'AirLoopHVAC':
        HVACname = row[2].strip()
        hvacs.add (HVACname)
    if row[0].strip() == 'Zone Information':
      zname = row[1].strip()
      zvol = float(row[19])
      nzones += 1
      volume += zvol
      zones[zname] = {'zvol': zvol, 'Hsched': '', 'Csched': ''}
  fp.close()

  fp = open(baseidf, 'r', errors='replace')
  print ('  parsing', baseidf)
  line = fp.readline()
  while line:
    if 'Coil:Heating:Electric' in line:
      if ';' not in line:  # bypass a comment line in the IDF header block
        coilname = get_eplus_token (fp.readline())
        if coilname not in hcoils:
          hcoils[coilname] = {'Sensor': 'Heating_Coil_{:d}'.format(idx_hcoil)}
          idx_hcoil += 1
    if 'Coil:Cooling:DX' in line:
      if ';' not in line:  # bypass a comment line in the IDF header block
        coilname = get_eplus_token (fp.readline())
        if coilname not in ccoils:
          ccoils[coilname] = {'Sensor': 'Cooling_Coil_{:d}'.format(idx_ccoil)}
          idx_ccoil += 1
    if 'Schedule:Compact' in line:
      schedule = line
      line = fp.readline()
      schedule += line
      name = get_eplus_token (line)
      while True:
        line = fp.readline()
        schedule += line
        if ';' in line:
          break
      schedules[name] = {'Schedule': schedule, 'Used': False, 'Heating': False, 'Alias' : ''}
    if 'ThermostatSetpoint:DualSetpoint' in line:
      name = get_eplus_token (fp.readline())
      heat = get_eplus_token (fp.readline())
      cool = get_eplus_token (fp.readline())
      thermostats[name] = {'Heating': heat, 'Cooling': cool}
      nsetpoints += 1
    if 'ZoneControl:Thermostat' in line:
      name = get_eplus_token (fp.readline())
      zone = get_eplus_token (fp.readline())
      ctrltype = get_eplus_token (fp.readline())
      objtype = get_eplus_token (fp.readline())
      ctrlname = get_eplus_token (fp.readline())
      zonecontrols[zone] = ctrlname
      ncontrols += 1
    line = fp.readline()

  fp.close()

  idx_hsched = 1
  idx_csched = 1
  for zone, ctrlname in zonecontrols.items():
    if ctrlname in thermostats:
      heat = thermostats[ctrlname]['Heating']
      cool = thermostats[ctrlname]['Cooling']
      if not schedules[heat]['Used']:
        schedules[heat]['Used'] = True
        schedules[heat]['Heating'] = True
        schedules[heat]['Alias'] = 'H{:d}'.format(idx_hsched)
        idx_hsched += 1
      if not schedules[cool]['Used']:
        schedules[cool]['Used'] = True
        schedules[cool]['Alias'] = 'C{:d}'.format(idx_csched)
        idx_csched += 1
      zones[zone]['Hsched'] = heat
      zones[zone]['Csched'] = cool
    else:
      print ('  ** No Schedule Found for Zone={:s}'.format(zone))
  for name, row in schedules.items():
    if row['Used']:
      nschedused += 1

  nhvacs = len(hvacs)
  nccoils = len(ccoils)
  nhcoils = len(hcoils)
  print ('  === {:d} zones total {:.2f} m3 with {:d} zone controls, {:d} dual setpoints, {:d} schedules, {:d} heating coils, {:d} cooling coils and {:d} HVAC loops'.format(
    nzones, volume, ncontrols, nsetpoints, nschedused, nhcoils, nccoils, nhvacs))
# print ('  === hvacs', hvacs)
#  print ('  === ccoil', ccoils)
#  print ('  === hcoil', hcoils)
# print ('  === schedules used')
# for name, row in schedules.items():
#   if row['Used']:
#     print (name, row['Heating'], row['Alias'], row['Schedule'])
# print ('  === thermostats')
# for name, row in thermostats.items():
#   print (name, row)
# print ('  === zonecontrols')
# for name, row in zonecontrols.items():
#   print (name, row)
# print ('  === zones')
# for zname, row in zones.items():
#   zvol = row['zvol']
#   Hsched = row['Hsched']
#   Csched = row['Csched']
#   print ('{:40s} {:8.2f}   {:40s}   {:40s}'.format (zname, zvol, Hsched, Csched))
  return zones, zonecontrols, thermostats, schedules, hcoils, ccoils, hvacs

def write_new_ems (target, zones, zonecontrols, thermostats, schedules, hcoils, ccoils, hvacs):
  op = open(target, 'w')
  print ("""! ***EMS PROGRAM***""", file=op)
  for key, row in schedules.items():
    if row['Used']:
      alias = row['Alias'] + '_NOM'
      insensitive = re.compile(re.escape(key), re.IGNORECASE)
      data = insensitive.sub(alias, row['Schedule'])
      print (data, file=op)

  print ("""
  EnergyManagementSystem:ProgramCallingManager,
    Volume_Initializer,   !- Name
    BeginNewEnvironment,  !- Calling Point
    Initialize_Volumes;   !- Program Name
  EnergyManagementSystem:ProgramCallingManager,
    Setpoint_Controller,          !- Name
    BeginTimestepBeforePredictor, !- Calling Point
    Set_Setpoints;                !- Program Name
  EnergyManagementSystem:ProgramCallingManager,
    Demand_Reporter,                      !- Name
    EndOfZoneTimestepAfterZoneReporting,  !- Calling Point
    Report_Demand,
    Calculate_Temperatures;               !- Program Name
  EnergyManagementSystem:Program,
    Set_Setpoints,      !- Name
    Set H1 = H1_NOM + HEAT_SETP_DELTA*5.0/9.0,
    Set C1 = C1_NOM + COOL_SETP_DELTA*5.0/9.0,
    Set H2 = H2_NOM + HEAT_SETP_DELTA*5.0/9.0,
    Set C2 = C2_NOM + COOL_SETP_DELTA*5.0/9.0;
  EnergyManagementSystem:Program,
    Initialize_Volumes,""", file=op)

  term = ','
  idx = 1
  nzones = len(zones)
  volume = 0.0
  for zname, row in zones.items():
    zvol = row['zvol']
    volume += zvol
    if idx == nzones:
      term = ';'
    print ('    Set {:s}_V = {:.2f}{:s}'.format (zname, zvol, term), file=op)
    idx += 1
  print ("""  
  EnergyManagementSystem:Program,
    Calculate_Temperatures,
    Set TOTAL_COOL_V = 0.0,
    Set TOTAL_HEAT_V = 0.0,
    Set C_DES = 0.0,
    Set H_DES = 0.0,
    Set C_CUR = 0.0,
    Set H_CUR = 0.0,""", file=op)

  for zname, row in zones.items():
    Hsens = zname + '_H'
    Csens = zname + '_C'
    Hsched = row['Hsched']
    Csched = row['Csched']
    print ('  IF ({:s} == 0 && {:s} <> 0),'.format (Hsens, Csens), file=op)
    print ('    Set C_DES = C_DES + {:s} * {:s}_V,'.format (Csched, zname), file=op)
    print ('    Set C_CUR = C_CUR + {:s}_T * {:s}_V,'.format (zname, zname), file=op)
    print ('    Set TOTAL_COOL_V = TOTAL_COOL_V + {:s}_V,'.format (zname), file=op)
    print ('  ELSEIF ({:s} == 0 && {:s} == 0),'.format (Hsens, Csens), file=op)
    print ('    Set C_DES = C_DES,', file=op)
    print ('    Set C_CUR = C_CUR,', file=op)
    print ('  ELSE,', file=op)
    print ('    Set H_DES = H_DES + {:s} * {:s}_V,'.format (Hsched, zname), file=op)
    print ('    Set H_CUR = H_CUR + {:s}_T * {:s}_V,'.format (zname, zname), file=op)
    print ('    Set TOTAL_HEAT_V = TOTAL_HEAT_V + {:s}_V,'.format (zname), file=op)
    print ('  ENDIF,', file=op)

  print ("""! Average temperature over zone air volumes""", file=op)
  print ('  Set Total_V = {:.2f},'.format (volume), file=op)
  print ('  Set T_CUR = 0,', file=op)
  for zname, row in zones.items():
    print ('  Set T_CUR = T_CUR + {:s}_T * {:s}_V,'.format (zname, zname), file=op)
  print ('  Set T_CUR = T_CUR/Total_V*9.0/5.0+32.0,', file=op)

  print ("""! Average cooling setpoint over zone air volumes""", file=op)
  print ('  Set T_Cooling = 0,', file=op)
  for zname, row in zones.items():
    print ('  Set T_Cooling = T_Cooling + {:s} * {:s}_V,'.format (row['Csched'], zname), file=op)
  print ('  Set T_Cooling = T_Cooling/Total_V*9.0/5.0+32.0,', file=op)

  print ("""! Average heating setpoint over zone air volumes""", file=op)
  print ('  Set T_Heating = 0,', file=op)
  for zname, row in zones.items():
    print ('  Set T_Heating = T_Heating + {:s} * {:s}_V,'.format (row['Hsched'], zname), file=op)
  print ('  Set T_Heating = T_Heating/Total_V*9.0/5.0+32.0,', file=op)

  print ("""
  Set Desired_Cooling_Temperature = 0.0,
  Set Current_Cooling_Temperature = 0.0,
  Set Desired_Heating_Temperature = 0.0,
  Set Current_Heating_Temperature = 0.0,

  IF (C_DES > 0 && H_DES > 0), ! Scenario 1, both heating and cooling
    Set Desired_Cooling_Temperature = C_DES/TOTAL_COOL_V*9.0/5.0+32.0,
    Set Desired_Heating_Temperature = H_DES/TOTAL_HEAT_V*9.0/5.0+32.0,     
    Set Current_Cooling_Temperature = C_CUR/TOTAL_COOL_V*9.0/5.0+32.0, 
    Set Current_Heating_Temperature = H_CUR/TOTAL_HEAT_V*9.0/5.0+32.0,   
  ELSEIF (C_DES == 0 && H_DES == 0),  ! Scenario 2, no heating or cooling
    Set Desired_Cooling_Temperature = T_Cooling,
    Set Desired_Heating_Temperature = T_Heating,     
    Set Current_Cooling_Temperature = T_Cooling, 
    Set Current_Heating_Temperature = T_Heating, 
  ELSEIF (C_DES > 0 && H_DES == 0), ! Scenario 3, only cooling
    Set Desired_Cooling_Temperature = C_DES/TOTAL_COOL_V*9.0/5.0+32.0,
    Set Desired_Heating_Temperature = T_Heating,     
    Set Current_Cooling_Temperature = C_CUR/TOTAL_COOL_V*9.0/5.0+32.0,
    Set Current_Heating_Temperature = T_Heating, 
  ELSEIF (C_DES == 0 && H_DES > 0), ! Scenario 4, only heating
    Set Desired_Cooling_Temperature = T_Cooling,
    Set Desired_Heating_Temperature = H_DES/TOTAL_HEAT_V*9.0/5.0+32.0,   
    Set Current_Cooling_Temperature = T_Cooling, 
    Set Current_Heating_Temperature = H_CUR/TOTAL_HEAT_V*9.0/5.0+32.0,
  ENDIF;
""", file=op)

  print ("""  EnergyManagementSystem:Program,
    Report_Demand,      !- Name
    Set Cooling_Power_State = 0.0,
    Set Heating_Power_State = 0.0,
    Set Flexible_Cooling_Demand = 0.0,
    Set Flexible_Heating_Demand = 0.0""", file=op)
  for name, row in ccoils.items():
    print ('    Set Flexible_Cooling_Demand = Flexible_Cooling_Demand + {:s},'.format(row['Sensor']), file=op)
  print ('    Set Flexible_Cooling_Demand = Flexible_Cooling_Demand/(60*60*ZoneTimeStep),', file=op)
  print ('    IF Flexible_Cooling_Demand <> 0.0,', file=op)
  print ('      Set Cooling_Power_State = 1.0,', file=op)
  print ('    ENDIF,', file=op)
  for name, row in hcoils.items():
    print ('    Set Flexible_Heating_Demand = Flexible_Heating_Demand + {:s},'.format(row['Sensor']), file=op)
  print ('    Set Flexible_Heating_Demand = Flexible_Heating_Demand/(60*60*ZoneTimeStep),', file=op)
  print ('    IF Flexible_Heating_Demand <> 0.0,', file=op)
  print ('      Set Heating_Power_State = 1.0,', file=op)
  print ('    ENDIF,', file=op)
  print ('    Set Cooling_Deadband = 0.0,', file=op)
  print ('    Set Heating_Deadband = 0.0;', file=op)

  for name, row in schedules.items():
    if row['Used']:
      alias = row['Alias']
      schedule_sensor (alias + '_NOM', op)
      schedule_actuator (alias, name, op)

  global_variable ('Flexible_Cooling_Demand', op)
  global_variable ('Flexible_Heating_Demand', op)
  global_variable ('Desired_Cooling_Temperature', op)
  global_variable ('Desired_Heating_Temperature', op)
  global_variable ('Cooling_Deadband', op)
  global_variable ('Heating_Deadband', op)
  global_variable ('Current_Cooling_Temperature', op)
  global_variable ('Current_Heating_Temperature', op)
  global_variable ('Cooling_Power_State', op)
  global_variable ('Heating_Power_State', op)
  global_variable ('H_DES', op)
  global_variable ('C_DES', op)
  global_variable ('H_CUR', op)
  global_variable ('C_CUR', op)

  output_variable ('Cooling Controlled Load', 'Flexible_Cooling_Demand', op)
  output_variable ('Heating Controlled Load', 'Flexible_Heating_Demand', op)
  output_variable ('Cooling Desired Temperature', 'Desired_Cooling_Temperature', op)
  output_variable ('Heating Desired Temperature', 'Desired_Heating_Temperature', op)
  output_variable ('Cooling Thermostat Deadband', 'Cooling_Deadband', op)
  output_variable ('Heating Thermostat Deadband', 'Heating_Deadband', op)
  output_variable ('Cooling Current Temperature', 'Current_Cooling_Temperature', op)
  output_variable ('Heating Current Temperature', 'Current_Heating_Temperature', op)
  output_variable ('Cooling Power State', 'Cooling_Power_State', op)
  output_variable ('Heating Power State', 'Heating_Power_State', op)
  output_variable ('Heating Desire', 'H_DES', op)
  output_variable ('Cooling Desire', 'C_DES', op)
  output_variable ('Heating Current', 'H_CUR', op)
  output_variable ('Cooling Current', 'C_CUR', op)

  for name, row in ccoils.items():
    cooling_coil_sensor (row['Sensor'], name, op)
  for name, row in hcoils.items():
    heating_coil_sensor (row['Sensor'], name, op)

  for zname, row in zones.items():
    zone_temperature_sensor (zname, op)
    zone_sensible_heating_sensor (zname, op)
    zone_sensible_cooling_sensor (zname, op)
    global_variable (zname + '_V', op)

  print ("""! ***EXTERNAL INTERFACE***
  ExternalInterface,
    FNCS;             !- Name of External Interface
  ExternalInterface:Variable,
    COOL_SETP_DELTA,  !- Name
    0;                !- Initial Value
  ExternalInterface:Variable,
    HEAT_SETP_DELTA,  !- Name
    0;                !- Initial Value
! ***GENERAL REPORTING***
  Output:VariableDictionary,IDF,Unsorted;
! ***REPORT METERS/VARIABLES***
  Output:Variable,EMS,Cooling Controlled Load,timestep;
  Output:Variable,EMS,Heating Controlled Load,timestep;
  Output:Variable,EMS,Cooling Desired Temperature,timestep;
  Output:Variable,EMS,Heating Desired Temperature,timestep;
  Output:Variable,EMS,Cooling Thermostat Deadband,timestep;
  Output:Variable,EMS,Heating Thermostat Deadband,timestep;
  Output:Variable,EMS,Cooling Current Temperature,timestep;
  Output:Variable,EMS,Heating Current Temperature,timestep;
  Output:Variable,EMS,Cooling Power State,timestep;
  Output:Variable,EMS,Heating Power State,timestep;
  Output:Variable,WHOLE BUILDING,Facility Total Electric Demand Power,timestep;
  Output:Variable,FACILITY,Facility Thermal Comfort ASHRAE 55 Simple Model Summer or Winter Clothes Not Comfortable Time,timestep;
  Output:Variable,*,People Occupant Count,timestep;
  Output:Variable,*,Site Outdoor Air Drybulb Temperature,timestep; """, file=op)

  op.close()

def make_ems(sourcedir='./output', baseidf='SchoolBase.idf', target='ems.idf'):
  """Creates the EMS for an EnergyPlus building model

  Args:
    target (str): desired output file in PWD, default ems.idf
    baseidf (str): is the original EnergyPlus model file without the EMS
    sourcedir (str): directory of the output from EnergyPlus baseline simulation, default ./output
  """

  print ('*** make_ems from', sourcedir, 'to', target)
  zones, zonecontrols, thermostats, schedules, hcoils, ccoils, hvacs = summarize_idf (sourcedir + '/eplusout.eio', baseidf)
  return write_new_ems (target, zones, zonecontrols, thermostats, schedules, hcoils, ccoils, hvacs)

  zones = {} 

  hcoils = []
  for i in range(1,4):
    hcoils.append ('Heating_Coil_{:d}'.format (i))
  ccoils = []
  for i in range(1,8):
    ccoils.append ('Cooling_Coil_{:d}'.format (i))

  print ('Heating Coils', hcoils)
  print ('Cooling Coils', ccoils)

  fp = open(sourcedir + '/eplusout.eio', 'r')
  rdr = csv.reader (fp)
  for row in rdr:
    if row[0].strip() == 'Zone Information':
      zname = row[1].strip()
      zvol = float(row[19])
      Hsched = 'H2'
      Csched = 'C2'
      Helem = ''
      Celem = 'Cooling_Coil_4'
      if 'POD_1' in zname:
        Celem = 'Cooling_Coil_5'
      if 'POD_2' in zname:
        Celem = 'Cooling_Coil_6'
      if 'POD_3' in zname:
        Celem = 'Cooling_Coil_7'
      if 'KITCHEN' in zname:
        Helem = 'Heating_Coil_1'
        Celem = 'Cooling_Coil_1'
      if 'GYM' in zname:
        Helem = 'Heating_Coil_2'
        Celem = 'Cooling_Coil_2'
      if 'CAFE' in zname:
        Helem = 'Heating_Coil_3'
        Celem = 'Cooling_Coil_3'
      if 'BATH' in zname or 'CORRIDOR' in zname or 'KITCHEN' in zname or 'MECH_' in zname:
        Hsched = 'H1'
        Csched = 'C1'
      zones[zname] = {'zvol':zvol, 'Hsched': Hsched, 'Csched': Csched, 'Helem': Helem, 'Celem': Celem}
  fp.close()

  volume = 0
  nzones = 0
  for zname, row in zones.items():
    zvol = row['zvol']
    Hsched = row['Hsched']
    Csched = row['Csched']
    Helem = row['Helem']
    Celem = row['Celem']
    nzones += 1
    volume += zvol
    print ('{:32s} {:8.2f} {:2s} {:2s} {:14s} {:14s}'.format (zname, zvol, Hsched, Csched, Helem, Celem))
  print ('{:3d} zones total {:8.2f} m3'.format(nzones,volume))

  op = open(target, 'w')

  print ("""! ***EMS PROGRAM***

  Schedule:Compact,
    C2_NOM,
    Temperature,
    Through: 6/30,
    For: SummerDesignDay,
    Until: 24:00, 24,
    For: WeekEnds Holidays WinterDesignDay,
    Until: 24:00, 27,
    For: AllOtherDays,
    Until: 06:00, 27,
    Until: 21:00, 24,
    Until: 24:00, 27,
    Through: 9/1,
    For: SummerDesignDay,
    Until: 24:00, 24,
    For: WeekEnds Holidays WinterDesignDay,
    Until: 24:00, 27,
    For: AllOtherDays,
    Until: 07:00, 27,
    Until: 18:00, 24,
    Until: 24:00, 27,
    Through: 12/31,
    For: SummerDesignDay,
    Until: 24:00, 24,
    For: WeekEnds Holidays WinterDesignDay,
    Until: 24:00, 27,
    For: AllOtherDays,
    Until: 06:00, 27,
    Until: 21:00, 24,
    Until: 24:00, 27;
  Schedule:Compact,
    C1_NOM,
    Temperature,
    Through: 12/31,
    For: SummerDesignDay,
    Until: 06:00, 27,
    Until: 21:00, 24,
    Until: 24:00, 27,
    For: AllOtherDays,
    Until: 24:00, 27;
  Schedule:Compact,
    H2_NOM,
    Temperature,
    Through: 6/30,
    For: WinterDesignDay,
    Until: 24:00, 21,
    For: WeekEnds Holidays SummerDesignDay,
    Until: 24:00, 16,
    For: AllOtherDays,
    Until: 06:00, 16,
    Until: 21:00, 21,
    Until: 24:00, 16,
    Through: 9/1,
    For: WinterDesignDay,
    Until: 24:00, 21,
    For: WeekEnds Holidays SummerDesignDay,
    Until: 24:00, 16,
    For: AllOtherDays,
    Until: 07:00, 16,
    Until: 18:00, 21,
    Until: 24:00, 16,
    Through: 12/31,
    For: WinterDesignDay,
    Until: 24:00, 21,
    For: WeekEnds Holidays SummerDesignDay,
    Until: 24:00, 16,
    For: AllOtherDays,
    Until: 06:00, 16,
    Until: 21:00, 21,
    Until: 24:00, 16;
  Schedule:Compact,
    H1_NOM,
    Temperature,
    Through: 12/31,
    For: WinterDesignDay,
    Until: 06:00, 16,
    Until: 21:00, 21,
    Until: 24:00, 16,
    For: AllOtherDays,
    Until: 24:00, 16;""", file=op)

  print ("""EnergyManagementSystem:ProgramCallingManager,
    Volume_Initializer,   !- Name
    BeginNewEnvironment,  !- Calling Point
    Initialize_Volumes;   !- Program Name
  EnergyManagementSystem:ProgramCallingManager,
    Setpoint_Controller,          !- Name
    BeginTimestepBeforePredictor, !- Calling Point
    Set_Setpoints;                !- Program Name
  EnergyManagementSystem:ProgramCallingManager,
    Demand_Reporter,                      !- Name
    EndOfZoneTimestepAfterZoneReporting,  !- Calling Point
    Report_Demand,
    Calculate_Temperatures;               !- Program Name
  EnergyManagementSystem:Program,
    Set_Setpoints,      !- Name
    Set H1 = H1_NOM + HEAT_SETP_DELTA*5.0/9.0,
    Set C1 = C1_NOM + COOL_SETP_DELTA*5.0/9.0,
    Set H2 = H2_NOM + HEAT_SETP_DELTA*5.0/9.0,
    Set C2 = C2_NOM + COOL_SETP_DELTA*5.0/9.0;
  EnergyManagementSystem:Program,
    Initialize_Volumes,""", file=op)

  term = ','
  idx = 1
  for zname, row in zones.items():
    if idx == nzones:
      term = ';'
    print ('    Set {:s}_V = {:.2f}{:s}'.format (zname, row['zvol'], term), file=op)
    idx += 1

  print ("""  
  EnergyManagementSystem:Program,
    Calculate_Temperatures,
    Set TOTAL_COOL_V = 0.0,
    Set TOTAL_HEAT_V = 0.0,
    Set C_DES = 0.0,
    Set H_DES = 0.0,
    Set C_CUR = 0.0,
    Set H_CUR = 0.0,""", file=op)

  for zname, row in zones.items():
    Hsched = row['Hsched']
    Csched = row['Csched']
    Helem = row['Helem']
    if len(Helem) < 1:
      Helem = zname + '_H'
    Celem = row['Celem']
    print ('  IF ({:s} == 0 && {:s} <> 0),'.format (Helem, Celem), file=op)
    print ('    Set C_DES = C_DES + {:s} * {:s}_V,'.format (Csched, zname), file=op)
    print ('    Set C_CUR = C_CUR + {:s}_T * {:s}_V,'.format (zname, zname), file=op)
    print ('    Set TOTAL_COOL_V = TOTAL_COOL_V + {:s}_V,'.format (zname), file=op)
    print ('  ELSEIF ({:s} == 0 && {:s} == 0),'.format (Helem, Celem), file=op)
    print ('    Set C_DES = C_DES,', file=op)
    print ('    Set C_CUR = C_CUR,', file=op)
    print ('  ELSE,', file=op)
    print ('    Set H_DES = H_DES + {:s} * {:s}_V,'.format (Hsched, zname), file=op)
    print ('    Set H_CUR = H_CUR + {:s}_T * {:s}_V,'.format (zname, zname), file=op)
    print ('    Set TOTAL_HEAT_V = TOTAL_HEAT_V + {:s}_V,'.format (zname), file=op)
    print ('  ENDIF,', file=op)

  print ("""! Average temperature over zone air volumes""", file=op)
  print ('  Set Total_V = {:.2f},'.format (volume), file=op)
  print ('  Set T_CUR = 0,', file=op)
  for zname, row in zones.items():
    print ('  Set T_CUR = T_CUR + {:s}_T * {:s}_V,'.format (zname, zname), file=op)
  print ('  Set T_CUR = T_CUR/Total_V*9.0/5.0+32.0,', file=op)
    
  print ("""! Average cooling setpoint over zone air volumes""", file=op)
  print ('  Set T_Cooling = 0,', file=op)
  for zname, row in zones.items():
    print ('  Set T_Cooling = T_Cooling + {:s} * {:s}_V,'.format (row['Csched'], zname), file=op)
  print ('  Set T_Cooling = T_Cooling/Total_V*9.0/5.0+32.0,', file=op)

  print ("""! Average heating setpoint over zone air volumes""", file=op)
  print ('  Set T_Heating = 0,', file=op)
  for zname, row in zones.items():
    print ('  Set T_Heating = T_Heating + {:s} * {:s}_V,'.format (row['Hsched'], zname), file=op)
  print ('  Set T_Heating = T_Heating/Total_V*9.0/5.0+32.0,', file=op)

  print ("""
  Set Desired_Cooling_Temperature = 0.0,
  Set Current_Cooling_Temperature = 0.0,
  Set Desired_Heating_Temperature = 0.0,
  Set Current_Heating_Temperature = 0.0,

  IF (C_DES > 0 && H_DES > 0), ! Scenario 1, both heating and cooling
    Set Desired_Cooling_Temperature = C_DES/TOTAL_COOL_V*9.0/5.0+32.0,
    Set Desired_Heating_Temperature = H_DES/TOTAL_HEAT_V*9.0/5.0+32.0,     
    Set Current_Cooling_Temperature = C_CUR/TOTAL_COOL_V*9.0/5.0+32.0, 
    Set Current_Heating_Temperature = H_CUR/TOTAL_HEAT_V*9.0/5.0+32.0,   
  ELSEIF (C_DES == 0 && H_DES == 0),  ! Scenario 2, no heating or cooling
    Set Desired_Cooling_Temperature = T_Cooling,
    Set Desired_Heating_Temperature = T_Heating,     
    Set Current_Cooling_Temperature = T_Cooling, 
    Set Current_Heating_Temperature = T_Heating, 
  ELSEIF (C_DES > 0 && H_DES == 0), ! Scenario 3, only cooling
    Set Desired_Cooling_Temperature = C_DES/TOTAL_COOL_V*9.0/5.0+32.0,
    Set Desired_Heating_Temperature = T_Heating,     
    Set Current_Cooling_Temperature = C_CUR/TOTAL_COOL_V*9.0/5.0+32.0,
    Set Current_Heating_Temperature = T_Heating, 
  ELSEIF (C_DES == 0 && H_DES > 0), ! Scenario 4, only heating
    Set Desired_Cooling_Temperature = T_Cooling,
    Set Desired_Heating_Temperature = H_DES/TOTAL_HEAT_V*9.0/5.0+32.0,   
    Set Current_Cooling_Temperature = T_Cooling, 
    Set Current_Heating_Temperature = H_CUR/TOTAL_HEAT_V*9.0/5.0+32.0,
  ENDIF;
""", file=op)

  print ("""  EnergyManagementSystem:Program,
    Report_Demand,      !- Name
    Set Cooling_Power_State = 0.0,
    Set Heating_Power_State = 0.0,""", file=op)
  if len(ccoils) > 0:
    print ('    Set Flexible_Cooling_Demand = {:s},'.format(ccoils[0]), file=op)
    for i in range (1, len(ccoils)):
      print ('    Set Flexible_Cooling_Demand = Flexible_Cooling_Demand + {:s},'.format(ccoils[i]), file=op)
    print ('    Set Flexible_Cooling_Demand = Flexible_Cooling_Demand/(60*60*ZoneTimeStep),', file=op)
    print ('    IF Flexible_Cooling_Demand <> 0.0,', file=op)
    print ('      Set Cooling_Power_State = 1.0,', file=op)
    print ('    ENDIF,', file=op)
  if len(hcoils) > 0:
    print ('    Set Flexible_Heating_Demand = {:s},'.format(hcoils[0]), file=op)
    for i in range (1, len(hcoils)):
      print ('    Set Flexible_Heating_Demand = Flexible_Heating_Demand + {:s},'.format(hcoils[i]), file=op)
    print ('    Set Flexible_Heating_Demand = Flexible_Heating_Demand/(60*60*ZoneTimeStep),', file=op)
    print ('    IF Flexible_Heating_Demand <> 0.0,', file=op)
    print ('      Set Heating_Power_State = 1.0,', file=op)
    print ('    ENDIF,', file=op)
  print ('    Set Cooling_Deadband = 0.0,', file=op)
  print ('    Set Heating_Deadband = 0.0;', file=op)

  schedule_sensor ('H1_NOM', op)
  schedule_sensor ('C1_NOM', op)
  schedule_sensor ('H2_NOM', op)
  schedule_sensor ('C2_NOM', op)

  schedule_actuator ('H1', 'HTGSETP_SCH_BathCorrMechKitchen', op)
  schedule_actuator ('C1', 'CLGSETP_SCH_BathCorrMechKitchen', op)
  schedule_actuator ('H2', 'HTGSETP_SCH', op)
  schedule_actuator ('C2', 'CLGSETP_SCH', op)

  global_variable ('Flexible_Cooling_Demand', op)
  global_variable ('Flexible_Heating_Demand', op)
  global_variable ('Desired_Cooling_Temperature', op)
  global_variable ('Desired_Heating_Temperature', op)
  global_variable ('Cooling_Deadband', op)
  global_variable ('Heating_Deadband', op)
  global_variable ('Current_Cooling_Temperature', op)
  global_variable ('Current_Heating_Temperature', op)
  global_variable ('Cooling_Power_State', op)
  global_variable ('Heating_Power_State', op)
  global_variable ('H_DES', op)
  global_variable ('C_DES', op)
  global_variable ('H_CUR', op)
  global_variable ('C_CUR', op)

  output_variable ('Cooling Controlled Load', 'Flexible_Cooling_Demand', op)
  output_variable ('Heating Controlled Load', 'Flexible_Heating_Demand', op)
  output_variable ('Cooling Desired Temperature', 'Desired_Cooling_Temperature', op)
  output_variable ('Heating Desired Temperature', 'Desired_Heating_Temperature', op)
  output_variable ('Cooling Thermostat Deadband', 'Cooling_Deadband', op)
  output_variable ('Heating Thermostat Deadband', 'Heating_Deadband', op)
  output_variable ('Cooling Current Temperature', 'Current_Cooling_Temperature', op)
  output_variable ('Heating Current Temperature', 'Current_Heating_Temperature', op)
  output_variable ('Cooling Power State', 'Cooling_Power_State', op)
  output_variable ('Heating Power State', 'Heating_Power_State', op)
  output_variable ('Heating Desire', 'H_DES', op)
  output_variable ('Cooling Desire', 'C_DES', op)
  output_variable ('Heating Current', 'H_CUR', op)
  output_variable ('Cooling Current', 'C_CUR', op)

  cooling_coil_sensor ('Cooling_Coil_1', 'PSZ-AC_1:6_COOLC DXCOIL', op)
  cooling_coil_sensor ('Cooling_Coil_2', 'PSZ-AC_2:5_COOLC DXCOIL', op)
  cooling_coil_sensor ('Cooling_Coil_3', 'PSZ-AC_2:7_COOLC DXCOIL', op)
  cooling_coil_sensor ('Cooling_Coil_4', 'VAV_OTHER_COOLC DXCOIL', op)
  cooling_coil_sensor ('Cooling_Coil_5', 'VAV_POD_1_COOLC DXCOIL', op)
  cooling_coil_sensor ('Cooling_Coil_6', 'VAV_POD_2_COOLC DXCOIL', op)
  cooling_coil_sensor ('Cooling_Coil_7', 'VAV_POD_3_COOLC DXCOIL', op)

  heating_coil_sensor ('Heating_Coil_1', 'PSZ-AC_1:6_HEATC', op)
  heating_coil_sensor ('Heating_Coil_2', 'PSZ-AC_2:5_HEATC', op)
  heating_coil_sensor ('Heating_Coil_3', 'PSZ-AC_2:7_HEATC', op)

  for zname, row in zones.items():
    zone_temperature_sensor (zname, op)
  for zname, row in zones.items():
    if 'CAFETERIA' not in zname and 'KITCHEN' not in zname and 'GYM' not in zname:
      zone_heating_sensor (zname, op)
  for zname, row in zones.items():
    global_variable (zname + '_V', op)

  print ("""! ***EXTERNAL INTERFACE***
  ExternalInterface,
    FNCS;             !- Name of External Interface
  ExternalInterface:Variable,
    COOL_SETP_DELTA,  !- Name
    0;                !- Initial Value
  ExternalInterface:Variable,
    HEAT_SETP_DELTA,  !- Name
    0;                !- Initial Value
! ***GENERAL REPORTING***
  Output:VariableDictionary,IDF,Unsorted;
! ***REPORT METERS/VARIABLES***
  Output:Variable,EMS,Cooling Controlled Load,timestep;
  Output:Variable,EMS,Heating Controlled Load,timestep;
  Output:Variable,EMS,Cooling Desired Temperature,timestep;
  Output:Variable,EMS,Heating Desired Temperature,timestep;
  Output:Variable,EMS,Cooling Thermostat Deadband,timestep;
  Output:Variable,EMS,Heating Thermostat Deadband,timestep;
  Output:Variable,EMS,Cooling Current Temperature,timestep;
  Output:Variable,EMS,Heating Current Temperature,timestep;
  Output:Variable,EMS,Cooling Power State,timestep;
  Output:Variable,EMS,Heating Power State,timestep;
  Output:Variable,WHOLE BUILDING,Facility Total Electric Demand Power,timestep;
  Output:Variable,FACILITY,Facility Thermal Comfort ASHRAE 55 Simple Model Summer or Winter Clothes Not Comfortable Time,timestep;
  Output:Variable,*,People Occupant Count,timestep;
  Output:Variable,*,Site Outdoor Air Drybulb Temperature,timestep; """, file=op)

  op.close()

