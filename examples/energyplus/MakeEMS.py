import csv

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

zones = {}

hcoils = []
for i in range(1,4):
  hcoils.append ('Heating_Coil_{:d}'.format (i))
ccoils = []
for i in range(1,8):
  ccoils.append ('Cooling_Coil_{:d}'.format (i))

print ('Heating Coils', hcoils)
print ('Cooling Coils', ccoils)

fp = open('output/eplusout.eio', 'r')
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
  print ('{:32s} {:7.2f} {:2s} {:2s} {:14s} {:14s}'.format (zname, zvol, Hsched, Csched, Helem, Celem))
print ('{:3d} zones total {:6.2f} m3'.format(nzones,volume))

op = open('ems.idf', 'w')

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
    Until: 24:00, 16;
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
  Output:Variable,*,People Occupant Count,timestep;""", file=op)

op.close()