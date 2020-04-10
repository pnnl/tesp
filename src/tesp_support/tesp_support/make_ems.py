# Copyright (C) 2020 Battelle Memorial Institute
# file: make_ems.py
"""Creates and merges the EMS for an EnergyPlus building model

Public Functions:
  :make_ems: Creates the energy management system (EMS) for FNCS/HELICS to interface with EnergyPlus.
  :merge_idf: Assembles the base IDF, the EMS, start time and end time
"""
import sys
import re
import csv
from datetime import datetime

if sys.platform == 'win32':
  pycall = 'python'
else:
  pycall = 'python3'

def idf_int(val):
  """Helper function to format integers for the EnergyPlus IDF input data file

  Args:
    val (int): the integer to format

  Returns:
     str: the integer in string format, padded with a comma and zero or one blanks, in order to fill three spaces
  """
  sval = str(val)
  if len(sval) < 2:
    return sval + ', '
  return sval + ','

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
  print ('    Zone Air System Sensible Heating Energy;', file=op)

def zone_sensible_cooling_sensor(name, op):
  print ('  EnergyManagementSystem:Sensor,', file=op)
  print ('    {:s}_C,  !- Name'.format (name), file=op)
  print ('    {:s},    !- Zone'.format (name), file=op)
  print ('    Zone Air System Sensible Cooling Energy;', file=op)

def zone_occupant_sensor (name, op):
  print ('  EnergyManagementSystem:Sensor,', file=op)
  print ('    {:s}_O,  !- Name'.format (name), file=op)
  print ('    {:s},    !- Zone'.format (name), file=op)
  print ('    Zone People Occupant Count;', file=op)

def get_eplus_token (sval):
  val = sval.strip()
  idx = val.rfind(';')
  if idx < 0:
    idx = val.rfind(',')
  return val[:idx].upper()

def print_idf_summary (target, zones, zonecontrols, thermostats, schedules, hcoils, ccoils, hvacs):
  print ('  === hvacs', hvacs)
  print ('  === ccoil', ccoils)
  print ('  === hcoil', hcoils)
  print ('  === schedules used')
  for name, row in schedules.items():
    if row['Used']:
      print (name, row['Heating'], row['Alias'], row['Schedule'])
  print ('  === thermostats')
  for name, row in thermostats.items():
    print (name, row)
  print ('  === zonecontrols')
  for name, row in zonecontrols.items():
    print (name, row)
  print ('  === zones')
  for zname, row in zones.items():
    zvol = row['zvol']
    Hsched = row['Hsched']
    Csched = row['Csched']
    People = row['People']
    print ('{:40s} {:8.2f}   {:40s}   {:40s} {:}'.format (zname, zvol, Hsched, Csched, People))

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
      zones[zname] = {'zvol': zvol, 'Hsched': '', 'Csched': '', 'People': False}
  fp.close()

  fp = open(baseidf, 'r', errors='replace')
  print ('  parsing', baseidf)
  line = fp.readline()
  while line:
    if 'People,' in line:
      name = get_eplus_token (fp.readline())
      zname = get_eplus_token (fp.readline())
      zones[zname]['People'] = True
      while ';' not in line:
        line = fp.readline()
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
  return zones, zonecontrols, thermostats, schedules, hcoils, ccoils, hvacs

def write_new_ems (target, zones, zonecontrols, thermostats, schedules, hcoils, ccoils, hvacs):
  op = open(target, 'w')
  print ("""! ***EMS PROGRAM***""", file=op)
  nschedused = 0
  for key, row in schedules.items():
    if row['Used']:
      alias = row['Alias'] + '_NOM'
      insensitive = re.compile(re.escape(key), re.IGNORECASE)
      data = insensitive.sub(alias, row['Schedule'])
      print (data, file=op)
      nschedused += 1

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
    Report_Occupants,
    Calculate_Temperatures;               !- Program Name
  EnergyManagementSystem:Program,
    Set_Setpoints,      !- Name""", file=op)
  idx = 1
  for key, row in schedules.items():
    if row['Used']:
      alias = row['Alias']
      setp = 'COOL_SETP_DELTA'
      term = ';'
      if 'H' in alias[0]:
        setp = 'HEAT_SETP_DELTA'
      if idx < nschedused:
        term = ','
      print ('    Set {:s} = {:s}_NOM + {:s}*5.0/9.0{:s}'.format (alias, alias, setp, term), file=op)
      idx += 1

  print("""
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
    Set C_SET = 0.0,
    Set H_SET = 0.0,
    Set C_CUR = 0.0,
    Set H_CUR = 0.0,""", file=op)
  print ('    Set Total_V = {:.2f},'.format (volume), file=op)

  for zname, row in zones.items():
    Hsens = zname + '_H'
    Csens = zname + '_C'
    Hsched = row['Hsched']
    Csched = row['Csched']
    Halias = schedules[Hsched]['Alias']
    Calias = schedules[Csched]['Alias']
    print ('    IF ({:s} > 0),'.format (Csens), file=op)
    print ('      Set C_SET = C_SET + {:s} * {:s}_V,'.format (Calias, zname), file=op)
    print ('      Set C_CUR = C_CUR + {:s}_T * {:s}_V,'.format (zname, zname), file=op)
    print ('      Set TOTAL_COOL_V = TOTAL_COOL_V + {:s}_V,'.format (zname), file=op)
    print ('    ELSEIF ({:s} > 0),'.format (Hsens), file=op)
    print ('      Set H_SET = H_SET + {:s} * {:s}_V,'.format (Halias, zname), file=op)
    print ('      Set H_CUR = H_CUR + {:s}_T * {:s}_V,'.format (zname, zname), file=op)
    print ('      Set TOTAL_HEAT_V = TOTAL_HEAT_V + {:s}_V,'.format (zname), file=op)
    print ('    ENDIF,', file=op)

  print ("""! Average temperature over zone air volumes""", file=op)
  print ('    Set T_CUR = 0,', file=op)
  for zname, row in zones.items():
    print ('    Set T_CUR = T_CUR + {:s}_T * {:s}_V,'.format (zname, zname), file=op)
  print ('    Set T_CUR = T_CUR/Total_V*9.0/5.0+32.0,', file=op)

  print ("""! Average cooling schedule and setpoint over zone air volumes
    Set Schedule_Cooling_Temperature = 0.0,
    Set T_Cooling = 0,""", file=op)
  for zname, row in zones.items():
    alias = schedules[row['Csched']]['Alias']
    print ('    Set T_Cooling = T_Cooling + {:s} * {:s}_V,'.format (alias, zname), file=op)
    print ('    Set Schedule_Cooling_Temperature = Schedule_Cooling_Temperature + {:s}_NOM * {:s}_V,'.format (alias, zname), file=op)
  print ('    Set T_Cooling = T_Cooling/Total_V*9.0/5.0+32.0,', file=op)
  print ('    Set Schedule_Cooling_Temperature = Schedule_Cooling_Temperature/Total_V*9.0/5.0+32.0,', file=op)

  print ("""! Average heating schedule and setpoint over zone air volumes
    Set Schedule_Heating_Temperature = 0.0,
    Set T_Heating = 0,""", file=op)
  for zname, row in zones.items():
    alias = schedules[row['Hsched']]['Alias']
    print ('    Set T_Heating = T_Heating + {:s} * {:s}_V,'.format (alias, zname), file=op)
    print ('    Set Schedule_Heating_Temperature = Schedule_Heating_Temperature + {:s}_NOM * {:s}_V,'.format (alias, zname), file=op)
  print ('    Set T_Heating = T_Heating/Total_V*9.0/5.0+32.0,', file=op)
  print ('    Set Schedule_Heating_Temperature = Schedule_Heating_Temperature/Total_V*9.0/5.0+32.0,', file=op)

  print ("""
    Set Setpoint_Cooling_Temperature = 0.0,
    Set Current_Cooling_Temperature = 0.0,
    Set Setpoint_Heating_Temperature = 0.0,
    Set Current_Heating_Temperature = 0.0,

    IF (C_SET > 0 && H_SET > 0), ! Scenario 1, both heating and cooling
      Set Setpoint_Cooling_Temperature = C_SET/TOTAL_COOL_V*9.0/5.0+32.0,
      Set Setpoint_Heating_Temperature = H_SET/TOTAL_HEAT_V*9.0/5.0+32.0,     
      Set Current_Cooling_Temperature = C_CUR/TOTAL_COOL_V*9.0/5.0+32.0, 
      Set Current_Heating_Temperature = H_CUR/TOTAL_HEAT_V*9.0/5.0+32.0,   
    ELSEIF (C_SET == 0 && H_SET == 0),  ! Scenario 2, no heating or cooling
      Set Setpoint_Cooling_Temperature = T_Cooling,
      Set Setpoint_Heating_Temperature = T_Heating,     
      Set Current_Cooling_Temperature = T_Cooling, 
      Set Current_Heating_Temperature = T_Heating, 
    ELSEIF (C_SET > 0 && H_SET == 0), ! Scenario 3, only cooling
      Set Setpoint_Cooling_Temperature = C_SET/TOTAL_COOL_V*9.0/5.0+32.0,
      Set Setpoint_Heating_Temperature = T_Heating,     
      Set Current_Cooling_Temperature = C_CUR/TOTAL_COOL_V*9.0/5.0+32.0,
      Set Current_Heating_Temperature = T_Heating, 
    ELSEIF (C_SET == 0 && H_SET > 0), ! Scenario 4, only heating
      Set Setpoint_Cooling_Temperature = T_Cooling,
      Set Setpoint_Heating_Temperature = H_SET/TOTAL_HEAT_V*9.0/5.0+32.0,   
      Set Current_Cooling_Temperature = T_Cooling, 
      Set Current_Heating_Temperature = H_CUR/TOTAL_HEAT_V*9.0/5.0+32.0,
    ENDIF;
""", file=op)

  print ("""  
  EnergyManagementSystem:Program,
    Report_Demand,      !- Name
    Set Cooling_Power_State = 0.0,
    Set Heating_Power_State = 0.0,
    Set Flexible_Cooling_Demand = 0.0,
    Set Flexible_Heating_Demand = 0.0,""", file=op)
  for name, row in ccoils.items():
    print ('    Set Flexible_Cooling_Demand = Flexible_Cooling_Demand + {:s},'.format(row['Sensor']), file=op)
  print ('    Set Flexible_Cooling_Demand = Flexible_Cooling_Demand/(60*60*ZoneTimeStep),', file=op)
  print ('    IF Flexible_Cooling_Demand > 1.0,', file=op)
  print ('      Set Cooling_Power_State = 1.0,', file=op)
  print ('    ENDIF,', file=op)
  for name, row in hcoils.items():
    print ('    Set Flexible_Heating_Demand = Flexible_Heating_Demand + {:s},'.format(row['Sensor']), file=op)
  print ('    Set Flexible_Heating_Demand = Flexible_Heating_Demand/(60*60*ZoneTimeStep),', file=op)
  print ('    IF Flexible_Heating_Demand > 1.0,', file=op)
  print ('      Set Heating_Power_State = 1.0,', file=op)
  print ('    ENDIF;', file=op)

  print ("""  
  EnergyManagementSystem:Program,
    Report_Occupants,
    Set Total_Occupants = 0.0,""", file=op)
  term = ','
  idx = 1
  for name, row in zones.items():
    if idx == nzones:
      term = ';'
    if row['People']:
      print ('    Set Total_Occupants = Total_Occupants + {:s}_O{:s}'.format(name, term), file=op)
    idx += 1

  for name, row in schedules.items():
    if row['Used']:
      alias = row['Alias']
      schedule_sensor (alias + '_NOM', op)
      schedule_actuator (alias, name, op)

  global_variable ('Flexible_Cooling_Demand', op)
  global_variable ('Flexible_Heating_Demand', op)
  global_variable ('Setpoint_Cooling_Temperature', op)
  global_variable ('Setpoint_Heating_Temperature', op)
  global_variable ('Schedule_Cooling_Temperature', op)
  global_variable ('Schedule_Heating_Temperature', op)
  global_variable ('Current_Cooling_Temperature', op)
  global_variable ('Current_Heating_Temperature', op)
  global_variable ('Cooling_Power_State', op)
  global_variable ('Heating_Power_State', op)
  global_variable ('H_SET', op)
  global_variable ('C_SET', op)
  global_variable ('H_CUR', op)
  global_variable ('C_CUR', op)
  global_variable ('TOTAL_HEAT_V', op)
  global_variable ('TOTAL_COOL_V', op)
  global_variable ('T_CUR', op)
  global_variable ('Total_Occupants', op)

  output_variable ('Cooling Controlled Load', 'Flexible_Cooling_Demand', op)
  output_variable ('Heating Controlled Load', 'Flexible_Heating_Demand', op)
  output_variable ('Cooling Schedule Temperature', 'Schedule_Cooling_Temperature', op)
  output_variable ('Heating Schedule Temperature', 'Schedule_Heating_Temperature', op)
  output_variable ('Cooling Setpoint Temperature', 'Setpoint_Cooling_Temperature', op)
  output_variable ('Heating Setpoint Temperature', 'Setpoint_Heating_Temperature', op)
  output_variable ('Cooling Current Temperature', 'Current_Cooling_Temperature', op)
  output_variable ('Heating Current Temperature', 'Current_Heating_Temperature', op)
  output_variable ('Cooling Power State', 'Cooling_Power_State', op)
  output_variable ('Heating Power State', 'Heating_Power_State', op)
  output_variable ('Heating Setpoint', 'H_SET', op)
  output_variable ('Cooling Setpoint', 'C_SET', op)
  output_variable ('Heating Current', 'H_CUR', op)
  output_variable ('Cooling Current', 'C_CUR', op)
  output_variable ('Heating Volume', 'TOTAL_HEAT_V', op)
  output_variable ('Cooling Volume', 'TOTAL_COOL_V', op)
  output_variable ('Indoor Air Temperature', 'T_CUR', op)
  output_variable ('Occupant Count', 'Total_Occupants', op)

  for name, row in ccoils.items():
    cooling_coil_sensor (row['Sensor'], name, op)
  for name, row in hcoils.items():
    heating_coil_sensor (row['Sensor'], name, op)

  for zname, row in zones.items():
    zone_temperature_sensor (zname, op)
    if row['People']:
      zone_occupant_sensor (zname, op)
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
  Output:Variable,EMS,Cooling Schedule Temperature,timestep;
  Output:Variable,EMS,Heating Schedule Temperature,timestep;
  Output:Variable,EMS,Cooling Setpoint Temperature,timestep;
  Output:Variable,EMS,Heating Setpoint Temperature,timestep;
  Output:Variable,EMS,Cooling Current Temperature,timestep;
  Output:Variable,EMS,Heating Current Temperature,timestep;
  Output:Variable,EMS,Cooling Power State,timestep;
  Output:Variable,EMS,Heating Power State,timestep;
  Output:Variable,EMS,Cooling Volume,timestep;
  Output:Variable,EMS,Heating Volume,timestep;
  Output:Variable,EMS,Occupant Count,timestep;
  Output:Variable,EMS,Indoor Air Temperature,timestep;
  Output:Variable,WHOLE BUILDING,Facility Total Electric Demand Power,timestep;
  Output:Variable,FACILITY,Facility Thermal Comfort ASHRAE 55 Simple Model Summer or Winter Clothes Not Comfortable Time,timestep;
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
#  print_idf_summary (target, zones, zonecontrols, thermostats, schedules, hcoils, ccoils, hvacs)
  return write_new_ems (target, zones, zonecontrols, thermostats, schedules, hcoils, ccoils, hvacs)

def merge_idf (base, ems, StartTime, EndTime, target):
  """Assembles a base EnergyPlus building model with EMS and simulation period

  Args:
    base (str): fully qualified base IDF model
    ems (str): fully qualified EMS model file
    StartTime (str): Date-Time to start simulation, Y-m-d H:M:S
    EndTime (str): Date-Time to end simulation, Y-m-d H:M:S
  """

  time_fmt = '%Y-%m-%d %H:%M:%S'
  dt1 = datetime.strptime (StartTime, time_fmt)
  dt2 = datetime.strptime (EndTime, time_fmt)

  ep_dow_names = ['Monday,   ', 'Tuesday,  ', 'Wednesday,', 'Thursday, ', 'Friday,   ', 'Saturday, ', 'Sunday,   ']
  dow = dt1.weekday()
  begin_month = dt1.month
  begin_day = dt1.day
  end_month = dt2.month
  end_day = dt2.day
  if dt2.hour == 0 and dt2.minute == 0 and dt2.second == 0:
    end_day -= 1

  ip = open (base, 'r', encoding='latin-1')
  op = open (target, 'w', encoding='latin-1')
  print ('filtering', base, 'plus', ems, 'to', target)
  for ln in ip:
    line = ln.rstrip('\n')
    if '!- Begin Month' in line:
      print ('    %s                      !- Begin Month' % idf_int(begin_month), file=op)
    elif '!- Begin Day of Month' in line:
      print ('    %s                      !- Begin Day of Month' % idf_int(begin_day), file=op)
    elif '!- End Month' in line:
      print ('    %s                      !- End Month' % idf_int(end_month), file=op)
    elif '!- End Day of Month' in line:
      print ('    %s                      !- End Day of Month' % idf_int(end_day), file=op)
    elif '!- Day of Week for Start Day' in line:
      print ('    %s               !- Day of Week for Start Day' % ep_dow_names[dow], file=op)
    else:
      print (line, file=op)
  ip.close()

  ip = open (ems, 'r', encoding='latin-1')
  for ln in ip:
    line = ln.rstrip('\n')
    print (line, file=op)
  op.close()

