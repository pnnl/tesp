% Copyright (C) 2021-2022 Battelle Memorial Institute
% file: InvFeederGen.glm

clear all;
format long g;

%% Most of the things you might want to change via a scripting mechanism are located in this section

% Directory for input files (CSVs)
% dir = 'c:/tesp/examples/ieee8500/backbone/';
dir = '~/src/ptesp/examples/ieee8500/backbone/';
% Directory for output of GLM files
% dir2 = 'c:/tesp/examples/ieee8500/';
dir2 = '~/src/ptesp/examples/ieee8500/';

% Power flow solver method
solver_method = 'NR'; % 'FBS';

% Start and stop times
start_date='''2000-09-01';
stop_date  = '''2000-09-02';
start_time='0:00:00''';
stop_time = '0:00:00''';
timezone='PST+8PDT';

% Minimum timestep
minimum_timestep = 15; % 4;

% Do you want to use houses?
houses = 'y';   % 'y' indicates you want to use houses, 'n' indicates static loads
use_load = 'y'; % 'y' indicates you want zip loads, 'n' indicates no appliances within the home
alt_climate_file = '../weather/WA-Yakima_Air_Terminal.tmy3';
climate_file = '../weather/AZ-Tucson_International_Ap.tmy3';
initial_air_temperature = 82;

load_scalar = 1.0;   % leave as 1 for house models; if houses='n', then this scales the base load of the original 8500 node system
house_scalar = 8;%8.7;%6;  % changes square ft (an increase in house_scalar will decrease sqft and decrease load)
zip_scalar = 0.3;%0.3;%3;   % scales the zip load (an increase in zip_scalar will increase load)

solar_fraction = 0.9;    % portion of houses with solar
battery_fraction = 0.5;  % portion of solar houses adding storage

gas_perc = 0.5; % ratio of homes that use gas heat (rest use resistive)
elec_cool_perc = 1.0; % ratio of homes that use electric AC (rest use NONE)

perc_gas_wh = 0.5; % ratio of homes with gas waterheaters (rest use electrical)

% if > 0 adds metrics_collector objects to meters with bill_mode,
% inverters, houses, waterheaters and the swing node
% also puts a metrics_collector_writer as the first object
metrics_interval = 300;

% Voltage regulator and capacitor settings
%  All voltages in on 120 volt per unit basis
%  VAr setpoints for capacitors are in kVAr
%  Time is in seconds

% Regulator bandcenter voltage, bandwidth voltage, time delay
reg = [7500/60, 2,  60;  % VREG1 (at feeder head)
       7480/60, 2, 120;  % VREG2 (cascaded reg on north side branch, furthest down circuit)
       7480/60, 2,  75;  % VREG3 (cascaded reg on north side branch, about halfway up circuit before VREG2)
       7500/60, 2,  90]; % VREG4 (solo reg on south side branch)
%reg = [7460/60, 2,  60;  % VREG1 (at feeder head)
%       7430/60, 2, 120;  % VREG2 (cascaded reg on north side branch, furthest down circuit)
%       7400/60, 2,  75;  % VREG3 (cascaded reg on north side branch, about halfway up circuit before VREG2)
%       7410/60, 2,  90]; % VREG4 (solo reg on south side branch)
     
% Capacitor voltage high, voltage low, kVAr high, kVAr low, time delay
% - Note, Cap0-Cap2 are in VOLTVAR control mode, Cap3 is in MANUAL mode
% -- (Cap3 is on south side branch after VREG 4)
cap = [128, 114, 475, -350, 480;  % CapBank0 (right before VREG2, but after VREG3)
       128, 114, 425, -350, 300;  % CapBank1 (a little after substation, before VREG3 or VREG4))
       130, 114, 450, -350, 180]; % CapBank2 (at substation)


%%  Power factor and ZIP settings for each ZIP load %%
% Lights
light_type = 'OTHER';
if (strcmp(light_type,'INCANDESCENT'))
    avg_lights = 1;          % normal distribution clipped at 0.5 and 2 kW
    std_dev_lights = 0.2;    % represents total AVAILABLE light load - schedule uses 20-50 perc of this 
    lights_pwr_frac = 0.0032;
    lights_curr_frac = 0.4257;
    lights_imp_frac = 0.5711;
    lights_pwr_pf = 1;
    lights_curr_pf = -1;
    lights_imp_pf = 1;
else
    avg_lights = .25;        % normal distribution clipped at .1 and .4 kW
    std_dev_lights = 0.05;   % represents total AVAILABLE light load - schedule uses 20-50 perc of this 
    lights_pwr_frac = 0.5849;
    lights_curr_frac = 0.0067;
    lights_imp_frac = 0.4085;
    lights_pwr_pf = -0.78;
    lights_curr_pf = 0.42;
    lights_imp_pf = -0.88;
end

% Plugs
avg_plug = 0.075;          % normal distribution clipped at 0.05 and .5 kW
std_dev_plug = 0.02;      
plug_pwr_frac = 0.0; % 0.1;
plug_curr_frac = 1.0; % 0.1;
plug_imp_frac = 0.0; % 0.8;
plug_pwr_pf = 0.95;
plug_curr_pf = 0.95;
plug_imp_pf = 0.95;

% Fan
avg_fan = 0.075;          % normal distribution clipped at 0.05 and .5 kW
std_dev_fan = 0.02;      
fan_pwr_frac = 0.0135;
fan_curr_frac = 0.2534;
fan_imp_frac = 0.7332;
fan_pwr_pf = -1;
fan_curr_pf = 0.95;
fan_imp_pf = 0.97;

% CRT TV
avg_crt_tv = 0.075;          % normal distribution clipped at 0.025 and .125 kW
std_dev_crt_tv = 0.02;      
crt_tv_pwr_frac = 0.1719;
crt_tv_curr_frac = 0.8266;
crt_tv_imp_frac = 0.0015;
crt_tv_pwr_pf = -0.92;
crt_tv_curr_pf = 1;
crt_tv_imp_pf = -0.99;

% LCD TV
avg_lcd_tv = 0.125;          % normal distribution clipped at 0.025 and .4 kW
std_dev_lcd_tv = 0.05;      
lcd_tv_pwr_frac = 0.9987;
lcd_tv_curr_frac = 0.0396;
lcd_tv_imp_frac = -0.0383;
lcd_tv_pwr_pf = -1;
lcd_tv_curr_pf = -0.54;
lcd_tv_imp_pf = 0.61;

lcd_to_crt = 0.8;  % 80 percent lcd

%% Some nominal voltage stuff for assigning flat start voltages
nom_volt1 = '7199.558';
nom_volt2 = '12470.00';
nom_volt3 = '69715.05';
nom_volt4 = '115000.00';


%% Load Lines.csv values

% Name1|From node2|Phases3|to node4|Phases5|Length6|Units7|Config8|Status9
fidLines = fopen([dir 'Lines.csv']);
Header1Lines = textscan(fidLines,'%s',1);
Header2Lines = textscan(fidLines,'%s %s %s %s %s %s %s %s %s',2,'Delimiter',',');

RawLines = textscan(fidLines,'%s %s %s %s %s %n %s %s %s','Delimiter',',');

% Load Transformers.csv values
% Name1|Phases2|From3|To4|primV5|secV6|MVA7|PrimConn8|SecConn9|%X10|%R11
fidTrans = fopen([dir 'Transformers.csv']);
Header1Trans = textscan(fidTrans,'%s',1);
Header2Trans = textscan(fidTrans,'%s %s %s %s %s %s %s %s %s %s %s',2,'Delimiter',',');

RawTrans = textscan(fidTrans,'%s %n %s %s %n %n %n %s %s %n %n','Delimiter',',');

% Load LoadXfmrs.csv values
% Name1|#ofPhases2|From3|Phase4|PrimkV5|PrimkVA6|ToPh1-7|Ph1-8|SeckVPh1-9|
% SeckVAPh1-10|ToPh2-11|Ph2-12|SeckVPh2-13|SeckVAPh2-14|imag-15|R1-16|
% R2-17|R3-18|NoLoad-19|X12-20|X13-21|X23-22
fidLoadTrans = fopen([dir 'LoadXfmrs.csv']);
Header1LoadTrans = textscan(fidLoadTrans,'%s',1);
Header2LoadTrans = textscan(fidLoadTrans,'%s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s',2,'Delimiter',',');

RawLoadTrans = textscan(fidLoadTrans,'%s %n %s %s %n %n %s %s %n %n %s %s %n %n %n %n %n %n %n %n %n %n','Delimiter',',');

% Load Triplex_Lines.csv values
% Name1|From2|Phases3|To4|Phases5|LineConf6|Length7|Units8
fidTripLines = fopen([dir 'Triplex_Lines.csv']);
Header1TripLines = textscan(fidTripLines,'%s',14);
Header2TripLines = textscan(fidTripLines,'%s',10);
Header3TripLines = textscan(fidTripLines,'%s',16);
Header4TripLines = textscan(fidTripLines,'%s %s %s %s %s %s %s %s',1,'Delimiter',',');

RawTripLines = textscan(fidTripLines,'%s %s %s %s %s %s %n %s','Delimiter',',');

% Load Loads.csv values
% Name1|#ofPh|NameofBus3|Ph4|NomVolt5|Status6|Model7|Connect8|Power9|PF10
fidTripLoads = fopen([dir 'Loads.csv']);
Header1TripLoads = textscan(fidTripLoads,'%s',12);
Header2TripLoads = textscan(fidTripLoads,'%s',8);
Header3TripLoads = textscan(fidTripLoads,'%s',11);
Header4TripLoads = textscan(fidTripLoads,'%s',10);
Header5TripLoads = textscan(fidTripLoads,'%s %s %s %s %s %s %s %s %s %s',1,'Delimiter',',');

RawTripLoads = textscan(fidTripLoads,'%s %n %s %s %n %s %n %s %n %n','Delimiter',',');

fidcond = fopen([dir 'WireData.dss']);
Header1 = textscan(fidcond,'%s',4);

% Values{1}-name | {2}-ohms/km | {3}-GMR in cm | {4}-outer rad? (cm)
CondValues = textscan(fidcond,'%*s WireData.%s Rac=%n %*s GMRac=%n %*s Radius=%n %*s %*s %s');

Racunits = 'Ohm/km';
GMRunits = 'cm';

fclose('all');

NameLines = char(RawLines{1});
FromLines = char(RawLines{2});
PhasesLines = char(RawLines{3});
ToLines = char(RawLines{4});
LengthLines = (RawLines{6});
UnitLines = char(RawLines{7});
ConfigLines = char(RawLines{8});
StatusLines = char(RawLines{9});

EndLines = length(NameLines);
EndLoadTrans = length(RawLoadTrans{1});
EndTripLines = length(RawTripLines{1});
EndTripLoads = length(RawTripLoads{1});
EndTripNodes = length(RawTripLines{1});

%% Print to glm file
open_name = [dir2 'inv8500.glm'];
fid = fopen(open_name,'wt');

%% Header stuff and schedules
fprintf(fid,'// IEEE 8500 node test system with smart inverters.\n');
fprintf(fid,'//  Generated %s using Matlab %s.\n\n',datestr(clock),version);

fprintf(fid,'clock {\n');
fprintf(fid,'     timezone %s;\n',timezone);
fprintf(fid,'     starttime %s %s;\n',start_date,start_time);
fprintf(fid,'     stoptime %s %s;\n',stop_date,stop_time);
fprintf(fid,'}\n\n');


%%
fprintf(fid,'module powerflow {\n');
fprintf(fid,'    solver_method %s;\n',solver_method);
fprintf(fid,'    line_limits FALSE;\n');
fprintf(fid,'    default_maximum_voltage_error 1e-4;\n');
fprintf(fid,'};\n');
if (strcmp(houses,'y') ~= 0)
    fprintf(fid,'module residential {\n');
    fprintf(fid,'     implicit_enduses NONE;\n');
    fprintf(fid,'     ANSI_voltage_check FALSE;\n');
    fprintf(fid,'}\n');
    fprintf(fid,'module climate;\n');
end

fprintf(fid,'module market;\n');
fprintf(fid,'module connection; // FNCS\n');
if (solar_fraction > 0) || (battery_fraction > 0)
    fprintf(fid,'module generators;\n');
    fprintf(fid,'#define SOLAR_STATUS=ONLINE\n');
    fprintf(fid,'#define BATTERY_STATUS=OFFLINE\n');
end
fprintf(fid,'module tape;\n\n');

fprintf(fid,'#define INVERTER_MODE=CONSTANT_PF\n');
fprintf(fid,'//#define INVERTER_MODE=VOLT_VAR\n');
fprintf(fid,'//#define INVERTER_MODE=VOLT_WATT\n');
fprintf(fid,'#define INV_VBASE=240.0\n');
fprintf(fid,'#define INV_V1=0.92\n');
fprintf(fid,'#define INV_V2=0.98\n');
fprintf(fid,'#define INV_V3=1.02\n');
fprintf(fid,'#define INV_V4=1.08\n');
fprintf(fid,'#define INV_Q1=0.44\n');
fprintf(fid,'#define INV_Q2=0.00\n');
fprintf(fid,'#define INV_Q3=0.00\n');
fprintf(fid,'#define INV_Q4=-0.44\n');
fprintf(fid,'#define INV_VIN=200.0\n');
fprintf(fid,'#define INV_IIN=32.5\n');
fprintf(fid,'#define INV_VVLOCKOUT=300.0\n');
fprintf(fid,'#define INV_VW_V1=1.05 // 1.05833\n');
fprintf(fid,'#define INV_VW_V2=1.10\n');
fprintf(fid,'#define INV_VW_P1=1.0\n');
fprintf(fid,'#define INV_VW_P2=0.0\n');

fprintf(fid,'// basic residential rate from www.tep.com/rates\n');
fprintf(fid,'// #define TEPCO_MONTHLY_FEE=13.00\n');
fprintf(fid,'// #define TEPCO_PRICE_0=0.102013 // 0-500 kwh\n');
fprintf(fid,'// #define TEPCO_PRICE_1=0.117013 // 501-1000 kwh\n');
fprintf(fid,'// #define TEPCO_PRICE_2=0.122513 // >1000 kwh\n\n');

fprintf(fid,'// residential time-of-use rate from www.tep.com/rates\n');
fprintf(fid,'// winter peak hours are 6-9 a.m. and 6-9 p.m., Oct-Apr\n');
fprintf(fid,'// summer peak hours are 3-7 p.m., May-Sep\n');
fprintf(fid,'// only M-F, excluding 6 holidays not accounted for below\n');
fprintf(fid,'// the holidays are Memorial, Indep, Labor, Thanksgiving, Xmas, New Years\n');
fprintf(fid,'#define TEPCO_MONTHLY_FEE=10.00\n');
fprintf(fid,'schedule TEPCO_PRICE_0 { // 0-500 kwh\n');
fprintf(fid,' *  6-8,18-20       * 10-4 1-5 0.104717;\n');
fprintf(fid,' *  0-5,9-17,21-23  * 10-4 1-5 0.097803;\n');
fprintf(fid,' *  *               * 10-4 6-0 0.097803;\n');
fprintf(fid,' *  15-18           *  5-9 1-5 0.138719;\n');
fprintf(fid,' *  0-14,19-23      *  5-9 1-5 0.098484;\n');
fprintf(fid,' *  *               *  5-9 6-0 0.098484;\n');
fprintf(fid,'}\n');
fprintf(fid,'schedule TEPCO_PRICE_1 { // 501-1000 kwh\n');
fprintf(fid,' *  6-8,18-20       * 10-4 1-5 0.113717;\n');
fprintf(fid,' *  0-5,9-17,21-23  * 10-4 1-5 0.106803;\n');
fprintf(fid,' *  *               * 10-4 6-0 0.106803;\n');
fprintf(fid,' *  15-18           *  5-9 1-5 0.147719;\n');
fprintf(fid,' *  0-14,19-23      *  5-9 1-5 0.107484;\n');
fprintf(fid,' *  *               *  5-9 6-0 0.107484;\n');
fprintf(fid,'}\n');
fprintf(fid,'schedule TEPCO_PRICE_2 { // >1000 kwh\n');
fprintf(fid,' *  6-8,18-20       * 10-4 1-5 0.119217;\n');
fprintf(fid,' *  0-5,9-17,21-23  * 10-4 1-5 0.112303;\n');
fprintf(fid,' *  *               * 10-4 6-0 0.112303;\n');
fprintf(fid,' *  15-18           *  5-9 1-5 0.153219;\n');
fprintf(fid,' *  0-14,19-23      *  5-9 1-5 0.112984;\n');
fprintf(fid,' *  *               *  5-9 6-0 0.112984;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'#include "schedules.glm";\n\n');

if (strcmp(houses,'y') ~= 0)
    fprintf(fid,'#set minimum_timestep=%d;\n',minimum_timestep);
end
fprintf(fid,'#set profiler=1;\n');
fprintf(fid,'#set relax_naming_rules=1;\n');
fprintf(fid,'#set suppress_repeat_messages=1;\n');
%fprintf(fid,'#set savefile="8500_balanced_%s.xml";\n',solver_method);
fprintf(fid,'#set randomseed=10\n');
if (metrics_interval > 0)
    fprintf(fid,'#define METRICS_INTERVAL=%.0f\n',metrics_interval);
    fprintf(fid,'object metrics_collector_writer {\n');
    fprintf(fid,'     interval ${METRICS_INTERVAL};\n');
    fprintf(fid,'     filename inv8500_metrics.json;\n');
    fprintf(fid,'};\n\n');
end

if (strcmp(houses,'y') ~= 0)
    fprintf(fid,'object csv_reader {\n');
    fprintf(fid,'  name CsvReader;\n');
    fprintf(fid,'//  filename sunny.csv;\n');
    fprintf(fid,'  filename cloudy.csv;\n');
    fprintf(fid,'};\n');
    fprintf(fid,'object climate {\n');
    fprintf(fid,'     name climate;\n');
    fprintf(fid,'     reader CsvReader;\n');
    fprintf(fid,'//     tmyfile sunny.csv;\n');
    fprintf(fid,'     tmyfile cloudy.csv;\n');
    fprintf(fid,'//     tmyfile "%s";\n',climate_file);
    fprintf(fid,'//     tmyfile "%s";\n',alt_climate_file);
    fprintf(fid,'//     interpolate QUADRATIC;\n');
    fprintf(fid,'}\n\n');
end

%% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%Create Regulator objects -- Easiest by hand
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
fprintf(fid,'// Regulators and regulator configurations\n\n');

fprintf(fid,'object regulator_configuration {\n');
fprintf(fid,'     connect_type 1;\n');
fprintf(fid,'     name reg_config_1;\n');
if strcmp(solver_method,'FBS')
    fprintf(fid,'     Control LINE_DROP_COMP;\n');
    fprintf(fid,'     band_center %.1f;\n',reg(1,1));
    fprintf(fid,'     band_width %.1f;\n',reg(1,2));
    fprintf(fid,'     current_transducer_ratio 0;\n');
    fprintf(fid,'     power_transducer_ratio 60.0;\n');
    fprintf(fid,'     compensator_r_setting_A 0.0;\n');
    fprintf(fid,'     compensator_x_setting_A 0.0;\n');
    fprintf(fid,'     compensator_r_setting_B 0.0;\n');
    fprintf(fid,'     compensator_x_setting_B 0.0;\n');
    fprintf(fid,'     compensator_r_setting_C 0.0;\n');
    fprintf(fid,'     compensator_x_setting_C 0.0;\n');
elseif strcmp(solver_method,'NR')
    fprintf(fid,'     // Control MANUAL;\n');
    fprintf(fid,'     Control OUTPUT_VOLTAGE;\n');
    fprintf(fid,'     band_center %4.1f;\n',reg(1,1)*60);
    fprintf(fid,'     band_width %3.1f;\n',reg(1,2)*60);
else
    fprintf('Uh-oh, screw up in regulators - possibly unknown type of solver');
end
fprintf(fid,'     time_delay %.1f;\n',reg(1,3));
fprintf(fid,'     raise_taps 16;\n');
fprintf(fid,'     lower_taps 16;\n');
fprintf(fid,'     regulation 0.1;\n');
fprintf(fid,'     Type B;\n');
fprintf(fid,'     tap_pos_A 0;\n');
fprintf(fid,'     tap_pos_B 0;\n');
fprintf(fid,'     tap_pos_C 0;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object regulator_configuration {\n');
fprintf(fid,'     connect_type 1;\n');
fprintf(fid,'     name reg_config_2;\n');
if strcmp(solver_method,'FBS')
    fprintf(fid,'     Control LINE_DROP_COMP;\n');
    fprintf(fid,'     band_center %.1f;\n',reg(2,1));
    fprintf(fid,'     band_width %.1f;\n',reg(2,2));
    fprintf(fid,'     current_transducer_ratio 0;\n');
    fprintf(fid,'     power_transducer_ratio 60.0;\n');
    fprintf(fid,'     compensator_r_setting_A 0.0;\n');
    fprintf(fid,'     compensator_x_setting_A 0.0;\n');
    fprintf(fid,'     compensator_r_setting_B 0.0;\n');
    fprintf(fid,'     compensator_x_setting_B 0.0;\n');
    fprintf(fid,'     compensator_r_setting_C 0.0;\n');
    fprintf(fid,'     compensator_x_setting_C 0.0;\n');
elseif strcmp(solver_method,'NR')
    fprintf(fid,'     // Control MANUAL;\n');
    fprintf(fid,'     Control OUTPUT_VOLTAGE;\n');
    fprintf(fid,'     band_center %4.1f;\n',reg(2,1)*60);
    fprintf(fid,'     band_width %3.1f;\n',reg(2,2)*60);
else
    fprintf('Uh-oh, screw up in regulators - possibly unknown type of solver');
end
fprintf(fid,'     time_delay %.1f;\n',reg(2,3));
fprintf(fid,'     raise_taps 16;\n');
fprintf(fid,'     lower_taps 16;\n');
fprintf(fid,'     regulation 0.1;\n');
fprintf(fid,'     Type B;\n');  
fprintf(fid,'     tap_pos_A 2;\n');
fprintf(fid,'     tap_pos_B 1;\n');
fprintf(fid,'     tap_pos_C 0;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object regulator_configuration {\n');
fprintf(fid,'     connect_type 1;\n');
fprintf(fid,'     name reg_config_3;\n');
if strcmp(solver_method,'FBS')
    fprintf(fid,'     Control LINE_DROP_COMP;\n');
    fprintf(fid,'     band_center %.1f;\n',reg(3,1));
    fprintf(fid,'     band_width %.1f;\n',reg(3,2));
    fprintf(fid,'     current_transducer_ratio 0;\n');
    fprintf(fid,'     power_transducer_ratio 60.0;\n');
    fprintf(fid,'     compensator_r_setting_A 0.0;\n');
    fprintf(fid,'     compensator_x_setting_A 0.0;\n');
    fprintf(fid,'     compensator_r_setting_B 0.0;\n');
    fprintf(fid,'     compensator_x_setting_B 0.0;\n');
    fprintf(fid,'     compensator_r_setting_C 0.0;\n');
    fprintf(fid,'     compensator_x_setting_C 0.0;\n');
elseif strcmp(solver_method,'NR')
    fprintf(fid,'     // Control MANUAL;\n');
    fprintf(fid,'     Control OUTPUT_VOLTAGE;\n');
    % Changed from 125*60 to 123*60
    fprintf(fid,'     band_center %4.1f;\n',reg(3,1)*60);
    fprintf(fid,'     band_width %3.1f;\n',reg(3,2)*60);
else
    fprintf('Uh-oh, screw up in regulators - possibly unknown type of solver');
end
fprintf(fid,'     time_delay %.1f;\n',reg(3,3));
fprintf(fid,'     raise_taps 16;\n');
fprintf(fid,'     lower_taps 16;\n');
fprintf(fid,'     regulation 0.1;\n');
fprintf(fid,'     Type B;\n');  
fprintf(fid,'     tap_pos_A 4;\n');
fprintf(fid,'     tap_pos_B 2;\n');
fprintf(fid,'     tap_pos_C 0;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object regulator_configuration {\n');
fprintf(fid,'     connect_type 1;\n');
fprintf(fid,'     name reg_config_4;\n');
if strcmp(solver_method,'FBS')
    fprintf(fid,'     Control LINE_DROP_COMP;\n');
    fprintf(fid,'     band_center %.1f;\n',reg(4,1));
    fprintf(fid,'     band_width %.1f;\n',reg(4,2));
    fprintf(fid,'     current_transducer_ratio 0;\n');
    fprintf(fid,'     power_transducer_ratio 60.0;\n');
    fprintf(fid,'     compensator_r_setting_A 0.0;\n');
    fprintf(fid,'     compensator_x_setting_A 0.0;\n');
    fprintf(fid,'     compensator_r_setting_B 0.0;\n');
    fprintf(fid,'     compensator_x_setting_B 0.0;\n');
    fprintf(fid,'     compensator_r_setting_C 0.0;\n');
    fprintf(fid,'     compensator_x_setting_C 0.0;\n');
elseif strcmp(solver_method,'NR')
    fprintf(fid,'     // Control MANUAL;\n');
    fprintf(fid,'     Control OUTPUT_VOLTAGE;\n');
    fprintf(fid,'     band_center %4.1f;\n',reg(4,1)*60);
    fprintf(fid,'     band_width %3.1f;\n',reg(4,2)*60);
else
    fprintf('Uh-oh, screw up in regulators - possibly unknown type of solver');
end
fprintf(fid,'     time_delay %.1f;\n',reg(4,3));
fprintf(fid,'     raise_taps 16;\n');
fprintf(fid,'     lower_taps 16;\n');
fprintf(fid,'     regulation 0.1;\n');
fprintf(fid,'     Type B;\n');  
fprintf(fid,'     tap_pos_A 2;\n');
fprintf(fid,'     tap_pos_B 2;\n');
fprintf(fid,'     tap_pos_C 1;\n');
fprintf(fid,'}\n\n');


fprintf(fid,'object regulator {\n');
fprintf(fid,'     name FEEDER_REG;\n');
fprintf(fid,'     phases ABCN;\n');
fprintf(fid,'     from regxfmr_HVMV_Sub_LSB;\n');
fprintf(fid,'     to _HVMV_Sub_LSB;\n');
fprintf(fid,'     configuration reg_config_1;\n');
fprintf(fid,'     object metrics_collector {\n');
fprintf(fid,'         interval ${METRICS_INTERVAL};\n');
fprintf(fid,'     };\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object regulator {\n');
fprintf(fid,'     name VREG2;\n');
fprintf(fid,'     phases ABCN;\n');
fprintf(fid,'     from regxfmr_190-8593;\n');
fprintf(fid,'     to gld_190-8593;\n');
fprintf(fid,'     configuration reg_config_2;\n');
fprintf(fid,'     object metrics_collector {\n');
fprintf(fid,'         interval ${METRICS_INTERVAL};\n');
fprintf(fid,'     };\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object regulator {\n');
fprintf(fid,'     name VREG3;\n');
fprintf(fid,'     phases ABCN;\n');
fprintf(fid,'     from regxfmr_190-8581;\n');
fprintf(fid,'     to gld_190-8581;\n');
fprintf(fid,'     configuration reg_config_3;\n');
fprintf(fid,'     object metrics_collector {\n');
fprintf(fid,'         interval ${METRICS_INTERVAL};\n');
fprintf(fid,'     };\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object regulator {\n');
fprintf(fid,'     name VREG4;\n');
fprintf(fid,'     phases ABCN;\n');
fprintf(fid,'     from regxfmr_190-7361;\n');
fprintf(fid,'     to gld_190-7361;\n');
fprintf(fid,'     configuration reg_config_4;\n');
fprintf(fid,'     object metrics_collector {\n');
fprintf(fid,'         interval ${METRICS_INTERVAL};\n');
fprintf(fid,'     };\n');
fprintf(fid,'}\n\n');



%% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%Create Capacitor objects
%Unsure of the MVAR values for cap3, is it .9 per phase or .9 total?
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

fprintf(fid,'// Capacitors\n\n');

fprintf(fid,'object capacitor {\n');
fprintf(fid,'     parent R42246;\n');
fprintf(fid,'     phases ABCN;\n');
fprintf(fid,'     pt_phase ABC;\n');
fprintf(fid,'     name CapBank0;\n');
fprintf(fid,'     phases_connected ABCN;\n');
fprintf(fid,'     // control MANUAL;\n');
fprintf(fid,'     control VARVOLT;\n');
fprintf(fid,'     // switchA OPEN;\n');
fprintf(fid,'     // switchB OPEN;\n');
fprintf(fid,'     // switchC OPEN;\n');
fprintf(fid,'     capacitor_A 0.4 MVAr;\n');
fprintf(fid,'     capacitor_B 0.4 MVAr;\n');
fprintf(fid,'     capacitor_C 0.4 MVAr;\n');
fprintf(fid,'     control_level INDIVIDUAL;\n');
fprintf(fid,'     voltage_set_high %.1f;\n', cap(1,1)*60);
fprintf(fid,'     voltage_set_low %.1f;\n', cap(1,2)*60);
fprintf(fid,'     VAr_set_high %.1f kVAr;\n', cap(1,3));
fprintf(fid,'     VAr_set_low %.1f kVAr;\n', cap(1,4));
fprintf(fid,'     time_delay %.1f;\n', cap(1,5));
fprintf(fid,'     lockout_time 1;\n');
fprintf(fid,'     remote_sense CAP_3;\n');
fprintf(fid,'     remote_sense_B L2823592_CAP;\n');
fprintf(fid,'     nominal_voltage %s;\n',nom_volt1);
fprintf(fid,'     object metrics_collector {\n');
fprintf(fid,'         interval ${METRICS_INTERVAL};\n');
fprintf(fid,'     };\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object capacitor {\n');
fprintf(fid,'     parent R42247;\n');
fprintf(fid,'     pt_phase ABC;\n');
fprintf(fid,'     phases ABCN;\n');
fprintf(fid,'     name CapBank1;\n');
fprintf(fid,'     phases_connected ABCN;\n');
fprintf(fid,'     // control MANUAL;\n');
fprintf(fid,'     control VARVOLT;\n');
fprintf(fid,'     // switchA OPEN;\n');
fprintf(fid,'     // switchB OPEN;\n');
fprintf(fid,'     // switchC OPEN;\n');
fprintf(fid,'     capacitor_A 0.3 MVAr;\n');
fprintf(fid,'     capacitor_B 0.3 MVAr;\n');
fprintf(fid,'     capacitor_C 0.3 MVAr;\n');
fprintf(fid,'     control_level INDIVIDUAL;\n');
fprintf(fid,'     voltage_set_high %.1f;\n', cap(2,1)*60);
fprintf(fid,'     voltage_set_low %.1f;\n', cap(2,2)*60);
fprintf(fid,'     VAr_set_high %.1f kVAr;\n', cap(2,3));
fprintf(fid,'     VAr_set_low %.1f kVAr;\n', cap(2,4));
fprintf(fid,'     time_delay %.1f;\n', cap(2,5));
fprintf(fid,'     remote_sense CAP_2;\n');
fprintf(fid,'     lockout_time 1;\n');
fprintf(fid,'     remote_sense_B Q16483_CAP;\n');
fprintf(fid,'     nominal_voltage %s;\n',nom_volt1);
fprintf(fid,'     object metrics_collector {\n');
fprintf(fid,'         interval ${METRICS_INTERVAL};\n');
fprintf(fid,'     };\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object capacitor {\n');
fprintf(fid,'     parent R20185;\n');
fprintf(fid,'     pt_phase ABC;\n');
fprintf(fid,'     phases ABCN;\n');
fprintf(fid,'     name CapBank2;\n');
fprintf(fid,'     phases_connected ABCN;\n');
fprintf(fid,'     // control MANUAL;\n');
fprintf(fid,'     control VARVOLT;\n');
fprintf(fid,'     // switchA OPEN;\n');
fprintf(fid,'     // switchB OPEN;\n');
fprintf(fid,'     // switchC OPEN;\n');
fprintf(fid,'     capacitor_A 0.3 MVAr;\n');
fprintf(fid,'     capacitor_B 0.3 MVAr;\n');
fprintf(fid,'     capacitor_C 0.3 MVAr;\n');
fprintf(fid,'     control_level INDIVIDUAL;\n');
fprintf(fid,'     voltage_set_high %.1f;\n', cap(3,1)*60);
fprintf(fid,'     voltage_set_low %.1f;\n', cap(3,2)*60);
fprintf(fid,'     VAr_set_high %.1f kVAr;\n', cap(3,3));
fprintf(fid,'     VAr_set_low %.1f kVAr;\n', cap(3,4));
fprintf(fid,'     time_delay %.1f;\n', cap(3,5));
fprintf(fid,'     lockout_time 1;\n');
fprintf(fid,'     remote_sense CAP_1;\n');
fprintf(fid,'     remote_sense_B Q16642_CAP;\n');
fprintf(fid,'     nominal_voltage %s;\n',nom_volt1);
fprintf(fid,'     object metrics_collector {\n');
fprintf(fid,'         interval ${METRICS_INTERVAL};\n');
fprintf(fid,'     };\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object capacitor {\n');
fprintf(fid,'     phases ABCN;\n');
fprintf(fid,'     parent R18242;\n');
fprintf(fid,'     name CapBank3;\n');
fprintf(fid,'     phases_connected ABCN;\n');
fprintf(fid,'     control MANUAL;\n');
fprintf(fid,'     capacitor_A 0.3 MVAr;\n');
fprintf(fid,'     capacitor_B 0.3 MVAr;\n');
fprintf(fid,'     capacitor_C 0.3 MVAr;\n');
fprintf(fid,'     control_level INDIVIDUAL;\n');
fprintf(fid,'     switchA CLOSED;\n');
fprintf(fid,'     switchB CLOSED;\n');
fprintf(fid,'     switchC CLOSED;\n');
fprintf(fid,'     nominal_voltage %s;\n',nom_volt1);
fprintf(fid,'     object metrics_collector {\n');
fprintf(fid,'         interval ${METRICS_INTERVAL};\n');
fprintf(fid,'     };\n');
fprintf(fid,'}\n\n');

%% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%Create Transformer objects -- only one transformer, so mostly by hand
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

fprintf(fid,'// Transformer and configuration at feeder\n\n');


fprintf(fid,'object transformer_configuration:27500 {\n');
fprintf(fid,'     connect_type DELTA_GWYE;\n');
fprintf(fid,'     name trans_config_1;\n');
fprintf(fid,'     install_type PADMOUNT;\n');
fprintf(fid,'     power_rating %5.0fkVA;\n',1000*RawTrans{7}(1));
fprintf(fid,'     primary_voltage %3.1fkV;\n',RawTrans{5}(1));
fprintf(fid,'     secondary_voltage %2.2fkV;\n',RawTrans{6}(1));
fprintf(fid,'     reactance %1.5f;\n',.01*RawTrans{10}(1));
fprintf(fid,'     resistance %1.5f;\n',.01*RawTrans{11}(1));
fprintf(fid,'}\n\n');

fprintf(fid,'object transformer {\n');
fprintf(fid,'     phases ABCN;\n');
fprintf(fid,'     name %s;\n',char(RawTrans{1}(1)));
fprintf(fid,'     from %s;\n',gld_strict_name(char(RawTrans{3}(1))));
fprintf(fid,'     to %s;\n',gld_strict_name(char(RawTrans{4}(1))));
fprintf(fid,'     configuration trans_config_1;\n');
fprintf(fid,'}\n\n');



%% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%Create Center-tap Transformer objects
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

fprintf(fid,'// Center-tap transformer configurations\n\n');

RHL = 0.006;
RHT = 0.012;
RLT = 0.012;

XHL = 0.0204;
XHT = 0.0204;
XLT = 0.0136;

XH = 0.5*(XHL+XHT-XLT);
XL = 0.5*(XHL+XLT-XHT);
XT = 0.5*(XLT+XHT-XHL);

for i=1:EndLoadTrans
   t_conf = sprintf('xf%.0f%.0f%s',RawLoadTrans{6}(i),RawLoadTrans{10}(i),char(RawLoadTrans{4}(i))); 
   t_confs(i,1:length(t_conf)) = t_conf;
   if i==1
      fprintf(fid,'object transformer_configuration {\n');
      fprintf(fid,'     name %s;\n',t_conf);
      fprintf(fid,'     connect_type SINGLE_PHASE_CENTER_TAPPED;\n');
      fprintf(fid,'     install_type POLETOP;\n');
      fprintf(fid,'     primary_voltage %5.1fV;\n',1000*RawLoadTrans{5}(i));
      fprintf(fid,'     secondary_voltage %3.1fV;\n',1000*RawLoadTrans{9}(i));
      fprintf(fid,'     power_rating %2.1fkVA;\n',RawLoadTrans{6}(i));
      fprintf(fid,'     power%s_rating %2.1fkVA;\n',char(RawLoadTrans{4}(i)),RawLoadTrans{10}(i));
      fprintf(fid,'     impedance %f+%fj;\n',RHL,XH);
      fprintf(fid,'     impedance1 %f+%fj;\n',RHT,XL);
      fprintf(fid,'     impedance2 %f+%fj;\n',RLT,XT);
      fprintf(fid,'     shunt_resistance 500.0;\n'); % these are per-unit parallel impedances
      fprintf(fid,'     shunt_reactance 200.0;\n');
      fprintf(fid,'}\n\n');
   else
      stop = 0;
      for m=1:(i-1)
         if (strcmp(t_conf(1:length(t_conf)),t_confs(m,1:length(t_conf))))
            stop = 1;
            m = i-2;
         end 
      end

      if stop ~= 1 
        fprintf(fid,'object transformer_configuration {\n');
        fprintf(fid,'     name %s;\n',t_conf);
        fprintf(fid,'     connect_type SINGLE_PHASE_CENTER_TAPPED;\n');
        fprintf(fid,'     install_type POLETOP;\n');
        fprintf(fid,'     primary_voltage %5.1f;\n',1000*RawLoadTrans{5}(i));
        fprintf(fid,'     secondary_voltage %3.1f;\n',1000*RawLoadTrans{9}(i));
        fprintf(fid,'     power_rating %2.1f;\n',RawLoadTrans{6}(i));
        fprintf(fid,'     power%s_rating %2.1f;\n',char(RawLoadTrans{4}(i)),RawLoadTrans{10}(i));
        fprintf(fid,'     impedance 0.006+0.0136j;\n');
        fprintf(fid,'     impedance1 0.012+0.0204j;\n');
        fprintf(fid,'     impedance2 0.012+0.0204j;\n');
        fprintf(fid,'     shunt_resistance 500.0;\n'); % these are per-unit parallel impedances
        fprintf(fid,'     shunt_reactance 200.0;\n');
        fprintf(fid,'}\n\n');          
      end
   end
       

end

fprintf(fid,'// Center-tap transformers\n\n');

for i=1:EndLoadTrans
    fprintf(fid,'object transformer {\n');
    fprintf(fid,'     configuration xf%.0f%.0f%s;\n',RawLoadTrans{6}(i),RawLoadTrans{10}(i),char(RawLoadTrans{4}(i)));
    fprintf(fid,'     name %s;\n',char(RawLoadTrans{1}(i))); 
    fprintf(fid,'     from %s;\n',gld_strict_name(char(RawLoadTrans{3}(i))));   
    fprintf(fid,'     to %s;\n',gld_strict_name(char(RawLoadTrans{7}(i))));
    fprintf(fid,'     nominal_voltage %s;\n',nom_volt1);
    fprintf(fid,'     phases %sS;\n',char(RawLoadTrans{4}(i)));
    fprintf(fid,'}\n\n');    
end



%% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%Create Triplex-Load objects
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
fprintf(fid,'// Triplex Node Objects with loads\n\n');
total_houses = 0;
if ( strcmp(houses,'y')~=0 )
    disp('Generating houses...');
    total_houses = 0;
    floor_area_large = 0;
    floor_area_small = 1000000;
    
    % summary load and resource metrics
    total_floor_area = 0;
    total_reload = 0;
    total_imload = 0;
    total_wh_kw = 0;
    total_wh_num = 0;
    total_ac_num = 0;
    total_ac_kw = 0;
    total_solar_num = 0;
    total_solar_kw = 0;
    total_battery_num = 0;
    total_battery_kw = 0;
    
    % Make sure it's only psuedo-randomized, but repeatable
    s2 = RandStream.create('mrg32k3a','NumStreams',3,'StreamIndices',2);
    RandStream.setGlobalStream(s2);

    total_houses_num = 0;
    for i=1:EndTripLoads
        reload = load_scalar*RawTripLoads{9}(i)*1000;
        imload = load_scalar*RawTripLoads{9}(i)*1000*tan(acos(RawTripLoads{10}(i)));
        
        total_reload = total_reload + reload;
        total_imload = total_imload + imload;

        total_houses_num = total_houses_num + ceil(sqrt(reload^2 + imload^2) / house_scalar / 1000);   
    end
    
    for i=1:EndTripLoads
        reload = load_scalar*RawTripLoads{9}(i)*1000;
        imload = load_scalar*RawTripLoads{9}(i)*1000*tan(acos(RawTripLoads{10}(i)));

        no_of_houses = ceil(sqrt(reload^2 + imload^2) / house_scalar / 1000);
       
        
        fprintf(fid,'object triplex_node {\n');
        fprintf(fid,'     name %s;\n',char(RawTripLoads{3}(i)));
        fprintf(fid,'     nominal_voltage 120;\n');
        Tph = char(RawTripLoads{3}(i));
        PhLoad = Tph(10);
        fprintf(fid,'     phases %sS;\n',PhLoad);
        fprintf(fid,'}\n\n');
        
        fprintf(fid,'// Converted from load: %.1f+%.1fj\n',reload,imload);
        for jj=1:no_of_houses
            floor_area = 2000+500*randn(1);
            if (floor_area > 3500)
                floor_area = 3500;
            elseif (floor_area < 500);
                floor_area = 500;
            end
            
            total_floor_area = total_floor_area + floor_area;
            
            if (floor_area > floor_area_large)
                floor_area_large = floor_area;
            end
            
            if (floor_area < floor_area_small)
                floor_area_small = floor_area;
            end
            
            scalar_A = 324.9/8907 * floor_area^0.442;  % used for scaling light and plug loads
            skew = 4800*randn(1);
            
            % putting house, battery and storage on the same meter for now
            mtr_root = sprintf ('%s_%.0f', char(RawTripLoads{3}(i)),jj);
            
            fprintf(fid,'object triplex_meter {\n');
            fprintf(fid,'     name %s;\n',mtr_root);
            fprintf(fid,'     parent %s;\n',char(RawTripLoads{3}(i)));
            fprintf(fid,'     nominal_voltage 120;\n');
            Tph = char(RawTripLoads{3}(i));
            PhLoad = Tph(10);
            fprintf(fid,'     phases %sS;\n',PhLoad);
            fprintf(fid,'     bill_day 1;\n');
            fprintf(fid,'     monthly_fee ${TEPCO_MONTHLY_FEE};\n');
            fprintf(fid,'     bill_mode TIERED_TOU;\n');
            fprintf(fid,'     price TEPCO_PRICE_0;\n');
            fprintf(fid,'     first_tier_energy 500;\n');
            fprintf(fid,'     first_tier_price TEPCO_PRICE_1;\n');
            fprintf(fid,'     second_tier_energy 1000;\n');
            fprintf(fid,'     second_tier_price TEPCO_PRICE_2;\n');
            if (metrics_interval > 0)
                fprintf(fid,'     object metrics_collector {\n');
                fprintf(fid,'         interval ${METRICS_INTERVAL};\n');
                fprintf(fid,'     };\n');
            end
            fprintf(fid,'}\n\n');
        
            fprintf(fid,'object house {\n');
            fprintf(fid,'     parent %s;\n',mtr_root);
            fprintf(fid,'     schedule_skew %.0f;\n',skew);
            fprintf(fid,'     name %s_house;\n',mtr_root);
            fprintf(fid,'     floor_area %.1f;\n',floor_area);
            
            ti = floor(5*rand(1)) + 3; % can use to shift thermal integrity
            
            if (ti > 6)
                ti = 6;
            end
            
            fprintf(fid,'     thermal_integrity_level %d;\n',ti);
%            fprintf(fid,'     air_temperature %.1f;\n', initial_air_temperature);
            % for TESP dictionary, print the system types before setpoints
            if (rand(1) < gas_perc)
                heat_type = 'GAS';
            else
                heat_type = 'RESISTANCE';
            end

            if (rand(1) < elec_cool_perc)
                cool_type = 'ELECTRIC';
                total_ac_num = total_ac_num + 1;
                [ac_btu, ac_kw] = estimate_ac_size (floor_area, ti);
                total_ac_kw = total_ac_kw + ac_kw;
                fprintf (fid, '     // AC size estimate %d BTU/hr or %7.2f kW\n', ac_btu, ac_kw);
            else
                cool_type = 'NONE';
            end

            fprintf(fid,'     auxiliary_system_type NONE;\n');
            fprintf(fid,'     heating_system_type %s;\n',heat_type);
            fprintf(fid,'     cooling_system_type %s;\n',cool_type);
            fprintf(fid,'     hvac_power_factor %.3f;\n',0.85 + .1 * rand(1));
            % Set cool temp and schedule
            cool_schedule = ceil(9*rand(1));

            cool_temp = 1.5+0.5*rand(1);
            if (cool_temp > 3)
                cool_temp = 3;
            elseif (cool_temp < 0);
                cool_temp = 0;
            end
            cooloffset = 80-10*rand(1); %cooling temp between 70-80
            fprintf(fid,'     cooling_setpoint cooling%d*%1.2f+%2.2f;\n',cool_schedule,cool_temp,cooloffset);

            % Set heat temp and schedule
            heat_schedule = ceil(9*rand(1));
            heatoffset = 70 - 6*rand(1);
            while (heatoffset > cooloffset - 2)
                heatoffset = 70 - 6*rand(1);
            end
            
            heat_temp = 1.5+0.5*rand(1);
            if (heat_temp > 3)
                heat_temp = 3;
            elseif (heat_temp < 0);
                heat_temp = 0;
            end
            fprintf(fid,'     heating_setpoint heating%d*%1.2f+%2.2f;\n',heat_schedule,heat_temp,heatoffset);

            % Water heater settings
            if (rand(1) < perc_gas_wh)
                wh_type = 'gas';
            else
                wh_type = 'elec';
            end
            
            skew2 = 7200*randn(1);
            
            if (strcmp(wh_type,'elec') ~= 0)
                fprintf(fid,'     object waterheater {\n');
                fprintf(fid,'         schedule_skew %.0f;\n',skew2);
                fprintf(fid,'         name %s_waterheater;\n',mtr_root);
                fprintf(fid,'         tank_height 3.78 ft;\n');
                
                test = rand(1);
                if test < 0.8
                        fprintf(fid,'         location GARAGE;\n');
                else
                        fprintf(fid,'         location INSIDE;\n');
                end
                fprintf(fid,'         tank_volume %f;\n',(45-5)+2*5.*rand(1));
                fprintf(fid,'         tank_UA %f;\n',3 + rand(1));
                wh_watts = (4500-500)+2*500.*rand(1);
                fprintf(fid,'         heating_element_capacity %f W;\n', wh_watts);
                total_wh_kw = total_wh_kw + 0.001 * wh_watts;
                total_wh_num = total_wh_num + 1;
                fprintf(fid,'         heat_mode ELECTRIC;\n');
                    tank_setpoint=(130-5)+2*5.*rand(1);
                fprintf(fid,'         tank_setpoint %f;\n',tank_setpoint);
                    therm_deadband = 4+4.*rand(1);
                fprintf(fid,'         thermostat_deadband %f;\n',therm_deadband);
                    lambda = 1.05;
                    init_temp = tank_setpoint + therm_deadband * lambda*exp(-lambda*rand(1)) - therm_deadband;
                fprintf(fid,'         temperature %f;\n',init_temp);
                
                temp2=round(2*rand(1))+1;

                water_var = 0.95 + rand(1) * 0.1; % +/-5% variability
                wh_sched = ceil(6*rand(1));
                
                if (floor_area > 1800)                
                    fprintf(fid,'         water_demand large_%d*%.1f;\n',wh_sched,water_var);
                else
                    fprintf(fid,'         water_demand small_%d*%.1f;\n',wh_sched,water_var);
                end

                if (metrics_interval > 0)
                    fprintf(fid,'         object metrics_collector {\n');
                    fprintf(fid,'             interval ${METRICS_INTERVAL};\n');
                    fprintf(fid,'         };\n');
                end
                fprintf(fid,'     };\n');
            end
            
            if (strcmp(use_load,'y')~=0)
                % Plugs
                fprintf(fid,'     object ZIPload {\n');
                fprintf(fid,'         schedule_skew %.0f;\n',skew);
                fprintf(fid,'         name %s_zip;\n',mtr_root);

                plug_schedule = ceil(3*rand(1));
                plug_load = avg_plug + std_dev_plug*randn(1);
                while(plug_load < 0.05 || plug_load > 0.5)
                    plug_load = avg_plug + std_dev_plug*randn(1);
                end

                fprintf(fid,'         base_power plug1*%f;\n',plug_schedule,zip_scalar*plug_load*scalar_A);
                fprintf(fid,'         power_fraction %f;\n',plug_pwr_frac);
                fprintf(fid,'         impedance_fraction %f;\n',plug_imp_frac);
                fprintf(fid,'         current_fraction %f;\n',plug_curr_frac);
                fprintf(fid,'         power_pf %f;\n',plug_pwr_pf);
                fprintf(fid,'         current_pf %f;\n',plug_curr_pf);
                fprintf(fid,'         impedance_pf %f;\n',plug_imp_pf);
                fprintf(fid,'     };\n');
            end

            if (metrics_interval > 0)
                fprintf(fid,'     object metrics_collector {\n');
                fprintf(fid,'         interval ${METRICS_INTERVAL};\n');
                fprintf(fid,'     };\n');
            end
            fprintf(fid,'};\n\n');
            
            if rand(1) < solar_fraction
                %Estimating size of solar array based on house sq ft
                if ((0.1*floor_area > 162) && (0.1*floor_area < 270))
                    panel_area = 0.1*floor_area;
                elseif  0.1*floor_area < 162
                    panel_area = 162;
                else
                    panel_area = 270;
                end
                                        
                array_efficiency = 0.2;
                sq_feet_to_sq_m = 1/10.7636;
                rated_insolation = 92.902; % W/ft^2 inside solar.cpp; 1000; %w/sq. m
                inverter_undersizing = 1.0; % 0.9;
                array_power  = panel_area * rated_insolation * array_efficiency;
                inverter_power = array_power * inverter_undersizing;
                
                fprintf(fid,'object inverter {\n');
                fprintf(fid,'    name %s_solar_inv;\n',mtr_root);
                fprintf(fid,'    parent %s;\n',mtr_root);
                fprintf(fid,'    phases %sS;\n',PhLoad);
                fprintf(fid,'    generator_status ${SOLAR_STATUS};\n');
                fprintf(fid,'    inverter_type FOUR_QUADRANT;\n');
                fprintf(fid,'    four_quadrant_control_mode ${INVERTER_MODE};\n');
                fprintf(fid,'    inverter_efficiency %.0f;\n',0.975);
                fprintf(fid,'    rated_power %.0f;\n',inverter_power);
                fprintf(fid,'    power_factor 1.0;\n');
                fprintf(fid,'    V_base ${INV_VBASE};\n'); 
                fprintf(fid,'    V1 ${INV_V1};\n'); 
                fprintf(fid,'    Q1 ${INV_Q1};\n'); 
                fprintf(fid,'    V2 ${INV_V2};\n'); 
                fprintf(fid,'    Q2 ${INV_Q2};\n'); 
                fprintf(fid,'    V3 ${INV_V3};\n'); 
                fprintf(fid,'    Q3 ${INV_Q3};\n'); 
                fprintf(fid,'    V4 ${INV_V4};\n'); 
                fprintf(fid,'    Q4 ${INV_Q4};\n'); 
                fprintf(fid,'    V_In ${INV_VIN};\n'); 
                fprintf(fid,'    I_In ${INV_IIN};\n'); 
                fprintf(fid,'    volt_var_control_lockout ${INV_VVLOCKOUT};\n'); 
                fprintf(fid,'    VW_V1 ${INV_VW_V1};\n'); 
                fprintf(fid,'    VW_V2 ${INV_VW_V2};\n'); 
                fprintf(fid,'    VW_P1 ${INV_VW_P1};\n'); 
                fprintf(fid,'    VW_P2 ${INV_VW_P2};\n'); 
                fprintf(fid,'    object solar {\n');                    
                fprintf(fid,'        name %s_solar;\n',mtr_root);
                fprintf(fid,'        generator_mode SUPPLY_DRIVEN;\n');
                fprintf(fid,'        generator_status ${SOLAR_STATUS};\n');
                fprintf(fid,'        panel_type SINGLE_CRYSTAL_SILICON;\n');
                fprintf(fid,'        efficiency 0.2;\n');
                fprintf(fid,'        rated_power %.0f;\n',array_power);
                fprintf(fid,'        // area %.0f;\n',panel_area);
                fprintf(fid,'     };\n');
                if (metrics_interval > 0)
                    fprintf(fid,'     object metrics_collector {\n');
                    fprintf(fid,'        interval ${METRICS_INTERVAL};\n');
                    fprintf(fid,'     };\n');
                end
                fprintf(fid,'};\n');
                total_solar_num = total_solar_num + 1;
                total_solar_kw = total_solar_kw + 0.001 * inverter_power;
                % 5-kW Tesla Powerwall 2
                if rand(1) < battery_fraction
                    fprintf(fid,'object inverter {\n');
                    fprintf(fid,'    name %s_battery_inv;\n',mtr_root);
                    fprintf(fid,'    parent %s;\n',mtr_root);
                    fprintf(fid,'    phases %sS;\n',PhLoad);
                    fprintf(fid,'    generator_status ${BATTERY_STATUS};\n');
                    fprintf(fid,'    generator_mode CONSTANT_PQ;\n');
                    fprintf(fid,'    inverter_type FOUR_QUADRANT;\n');
                    fprintf(fid,'    four_quadrant_control_mode LOAD_FOLLOWING;\n');
                    fprintf(fid,'    charge_lockout_time 1;\n');
                    fprintf(fid,'    discharge_lockout_time 1;\n');
                    fprintf(fid,'    rated_power %.0f;\n',5000);%Tesla Powerwall 2 
                    fprintf(fid,'    max_charge_rate %.0f;\n',5000);
                    fprintf(fid,'    max_discharge_rate %.0f;\n',5000);
                    fprintf(fid,'    sense_object %s;\n',mtr_root); %meter for house + solar + battery
                    fprintf(fid,'    charge_on_threshold %.0f;\n',-100);
                    fprintf(fid,'    charge_off_threshold %.0f;\n',0);
                    fprintf(fid,'    discharge_off_threshold %.0f;\n',2000);
                    fprintf(fid,'    discharge_on_threshold %.0f;\n',3000);
                    fprintf(fid,'    inverter_efficiency %.3f;\n',0.975);
                    fprintf(fid,'    object battery {\n');
                    fprintf(fid,'        name %s_battery;\n',mtr_root);
                    fprintf(fid,'        generator_status ${BATTERY_STATUS};\n');
                    fprintf(fid,'        use_internal_battery_model true;\n');
                    fprintf(fid,'        generator_mode CONSTANT_PQ;\n');
                    fprintf(fid,'        battery_type LI_ION;\n');
                    fprintf(fid,'        nominal_voltage %.0f;\n',480);%Tesla Powerwall 2 
                    fprintf(fid,'        battery_capacity %.0f;\n',13500);%Tesla Powerwall 2 
                    fprintf(fid,'        round_trip_efficiency %.2f;\n',0.86);
                    fprintf(fid,'        state_of_charge %.2f;\n',0.5);
                    fprintf(fid,'        generator_mode SUPPLY_DRIVEN;\n');
                    fprintf(fid,'    };\n');
                    if (metrics_interval > 0)
                        fprintf(fid,'    object metrics_collector {\n');
                        fprintf(fid,'        interval ${METRICS_INTERVAL};\n');
                        fprintf(fid,'    };\n');
                    end
                    fprintf(fid,'};\n');
                    total_battery_num = total_battery_num + 1;
                    total_battery_kw = total_battery_kw + 5;
                end
            end
        end     
        total_houses = total_houses + no_of_houses;
    end
else
    for i=1:EndTripLoads
        fprintf(fid,'object triplex_node {\n');
        fprintf(fid,'     name %s;\n',char(RawTripLoads{3}(i)));
        fprintf(fid,'     nominal_voltage 120;\n');
        Tph = char(RawTripLoads{3}(i));
        PhLoad = Tph(10);
        fprintf(fid,'     phases %sS;\n',PhLoad);

        reload = load_scalar*RawTripLoads{9}(i)*1000/2;
        imload = load_scalar*RawTripLoads{9}(i)*1000*tan(acos(RawTripLoads{10}(i)))/2;


        fprintf(fid,'     power_1 %.1f+%.1fj;\n',reload,imload);
        fprintf(fid,'     power_2 %.1f+%.1fj;\n',reload,imload);
        fprintf(fid,'}\n\n');   
    end
end



%% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%Create Triplex-Node objects (non-load objects)
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

fprintf(fid,'// Triplex Node Objects without loads\n\n');
disp('Printing triplex nodes...');
for i=1:EndTripNodes
    fprintf(fid,'object triplex_node {\n');
    fprintf(fid,'     name %s;\n',char(RawTripLines{2}(i)));
    fprintf(fid,'     nominal_voltage 120;\n');
    TphN = char(RawTripLines{4}(i));
    PhNode = TphN(10);
    fprintf(fid,'     phases %sS;\n',PhNode);
    fprintf(fid,'}\n\n');   
end

%% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%Create Node objects
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
disp('Printing nodes - this will take some time...');
fprintf(fid,'// Node Objects\n\n');

% Go through 'From' node list, eliminate any repeats
n=0;
for i=1:EndLines
    stop = 0;
    phase = char(RawLines{3}(i));
    phasebit = 0;
    
    if ~isempty(findstr(phase,'A'))
        phasebit = phasebit + 4;
    end
    if ~isempty(findstr(phase,'B'))
        phasebit = phasebit + 2;
    end
    if ~isempty(findstr(phase,'C'))
        phasebit = phasebit + 1;
    end
    
    for m=1:n
        if (strcmp(RawLines{2}(i),Node_Name{1}(m)))
            stop = 1;
            phasebit = bitor(phasebit,Node_Phase{1}(m));
            Node_Phase{1}(m) = phasebit;
            m=n;
        end 
    end
    if stop~=1
        n=n+1;
        Node_Name{1}(n) = RawLines{2}(i);
        Node_Phase{1}(n) = phasebit;
    end
end
% Go through 'to' node list
end_last = n;
for i=(EndLines+1):(EndLines*2)
    stop = 0;
    phase = char(RawLines{3}(i-EndLines));
    phasebit = 0;
    
    if ~isempty(findstr(phase,'A'))
        phasebit = phasebit + 4;
    end
    if ~isempty(findstr(phase,'B'))
        phasebit = phasebit + 2;
    end
    if ~isempty(findstr(phase,'C'))
        phasebit = phasebit + 1;
    end
    
    for m=1:n
        if (strcmp(RawLines{4}(i-EndLines),Node_Name{1}(m)))
            stop = 1;
            phasebit = bitor(phasebit,Node_Phase{1}(m));
            Node_Phase{1}(m) = phasebit;
            m=n;
        elseif (RawLines{6}(i-EndLines)==0.01||RawLines{6}(i-EndLines)==0.001)
            stop = 1;
            m = n;
        end
    end 
    if stop~=1
        n=n+1;
        Node_Name{1}(n) = RawLines{4}(i-EndLines);
        Node_Phase{1}(n) = phasebit;
    end
end
% Print Nodes, but override all of the capacitor nodes to be three phase
for i=1:length(Node_Name{1})
    phasebit = Node_Phase{1}(i);
    
    switch phasebit
        case 1
            phase = 'C';
        case 2
            phase = 'B';
        case 3
            phase = 'BC';
        case 4
            phase = 'A';
        case 5
            phase = 'AC';
        case 6 
            phase = 'AB';
        case 7
            phase = 'ABC';
    end
    
    if (~isempty(findstr(char(Node_Name{1}(i)),'Q'))||(~isempty(findstr(char(Node_Name{1}(i)),'L2823592')))) 
        fprintf(fid,'object node {\n');
        fprintf(fid,'     phases ABCN;\n');
        fprintf(fid,'     name %s;\n',gld_strict_name(char(Node_Name{1}(i))));
        fprintf(fid,'     nominal_voltage %s;\n',nom_volt1);
        fprintf(fid,'}\n\n');
    elseif (~isempty(findstr(char(Node_Name{1}(i)),'193-48013'))||(~isempty(findstr(char(Node_Name{1}(i)),'E182745')))||(~isempty(findstr(char(Node_Name{1}(i)),'193-51796')))) 
        % Some weird switch nodes that only need one phase attached
        fprintf(fid,'object node {\n');
        fprintf(fid,'     phases AN;\n');
        fprintf(fid,'     name %s;\n',gld_strict_name(char(Node_Name{1}(i))));
        fprintf(fid,'     nominal_voltage %s;\n',nom_volt1);
        fprintf(fid,'}\n\n');
    else
        fprintf(fid,'object node {\n');
        fprintf(fid,'     phases %sN;\n',phase);
        fprintf(fid,'     name %s;\n',gld_strict_name(char(Node_Name{1}(i))));
        fprintf(fid,'     nominal_voltage %s;\n',nom_volt1);
        fprintf(fid,'}\n\n');
    end
end

% One node object in regulators and HV needs to be manually generated
fprintf(fid,'object node {\n');
fprintf(fid,'     phases ABCN;\n');
fprintf(fid,'     name regxfmr_HVMV_Sub_LSB;\n');
fprintf(fid,'     nominal_voltage %s;\n',nom_volt1);
fprintf(fid,'}\n\n');

fprintf(fid,'object substation {\n');
fprintf(fid,'     name network_node;\n');
fprintf(fid,'     bustype SWING;\n');
fprintf(fid,'     nominal_voltage 66395.3;\n');
fprintf(fid,'     base_power 12MVA;\n');
fprintf(fid,'     power_convergence_value 100VA;\n');
fprintf(fid,'     phases ABCN;\n');
fprintf(fid,'     positive_sequence_voltage 69715.1;\n');
if (metrics_interval > 0)
    fprintf(fid,'     object metrics_collector {\n');
    fprintf(fid,'         interval ${METRICS_INTERVAL};\n');
    fprintf(fid,'     };\n');
end
fprintf(fid,'}\n\n');

fprintf(fid,'#ifdef USE_FNCS\n');
fprintf(fid,'object fncs_msg {\n');
fprintf(fid,'  name gridlabdSimulator1;\n');
fprintf(fid,'  parent network_node;\n');
fprintf(fid,'  configure inv8500_gridlabd.txt;\n');
fprintf(fid,'  option "transport:hostname localhost, port 5570";\n');
fprintf(fid,'}\n');
fprintf(fid,'#endif\n\n');

% high-side reactor that represents transmission source impedance
fprintf(fid,'object line_configuration {\n');
fprintf(fid,'  name lcon_series_reactor;\n');
fprintf(fid,'  z11 0.00000+23815.6j;\n');
fprintf(fid,'  z12 0.00000+0.00000j;\n');
fprintf(fid,'  z13 0.00000+0.00000j;\n');
fprintf(fid,'  z21 0.00000+0.00000j;\n');
fprintf(fid,'  z22 0.00000+23815.6j;\n');
fprintf(fid,'  z23 0.00000+0.00000j;\n');
fprintf(fid,'  z31 0.00000+0.00000j;\n');
fprintf(fid,'  z32 0.00000+0.00000j;\n');
fprintf(fid,'  z33 0.00000+23815.6j;\n');
fprintf(fid,'  c11 0.00000;\n');
fprintf(fid,'  c12 0.00000;\n');
fprintf(fid,'  c13 0.00000;\n');
fprintf(fid,'  c21 0.00000;\n');
fprintf(fid,'  c22 0.00000;\n');
fprintf(fid,'  c23 0.00000;\n');
fprintf(fid,'  c31 0.00000;\n');
fprintf(fid,'  c32 0.00000;\n');
fprintf(fid,'  c33 0.00000;\n');
fprintf(fid,'}\n');
fprintf(fid,'object overhead_line {\n');
fprintf(fid,'     name series_reactor;\n');
fprintf(fid,'     phases ABC;\n');
fprintf(fid,'     from network_node;\n');
fprintf(fid,'     to HVMV_Sub_HSB;\n');
fprintf(fid,'     length 3.28084;\n');
fprintf(fid,'     configuration lcon_series_reactor;\n');
fprintf(fid,'}\n');
fprintf(fid,'object node {\n');
fprintf(fid,'     name HVMV_Sub_HSB;\n');
fprintf(fid,'     nominal_voltage 66395.3;\n');
fprintf(fid,'     phases ABCN;\n');
fprintf(fid,'}\n\n');

%% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%Create Line and Conductor Configurations
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
fprintf(fid,'// Overhead Line Conductors and configurations.\n');
disp('Printing lines and conductors...');
% Print the conductors that are needed
for i = 1:length(CondValues{1})
    if (strcmp(char(CondValues{1}(i)),'397_ACSR')||strcmp(char(CondValues{1}(i)),'2/0_ACSR')||strcmp(char(CondValues{1}(i)),'4_ACSR')||strcmp(char(CondValues{1}(i)),'2_ACSR')||strcmp(char(CondValues{1}(i)),'1/0_ACSR')||strcmp(char(CondValues{1}(i)),'4_WPAL')||strcmp(char(CondValues{1}(i)),'1/0_TPX')||strcmp(char(CondValues{1}(i)),'4/0_TPX')||strcmp(char(CondValues{1}(i)),'4_DPX')||strcmp(char(CondValues{1}(i)),'1/0_3W_CS')||strcmp(char(CondValues{1}(i)),'4_TPX')||strcmp(char(CondValues{1}(i)),'6_WPAL')||strcmp(char(CondValues{1}(i)),'2_WPAL')||strcmp(char(CondValues{1}(i)),'2/0_WPAL')||strcmp(char(CondValues{1}(i)),'DEFAULT')||strcmp(char(CondValues{1}(i)),'600_CU'))
        fprintf(fid,'object overhead_line_conductor {\n');
        fprintf(fid,'     name %s;\n',gld_strict_name(char(CondValues{1}(i))));
        fprintf(fid,'     geometric_mean_radius %1.6f%s;\n',CondValues{3}(i),GMRunits);
        fprintf(fid,'     resistance %1.6f%s;\n',CondValues{2}(i),Racunits);
        
            [~,temp_rating] = strtok(CondValues{5}(i),'=');
            [temp_rating,~] = strtok(temp_rating,'=');
            temp_rating = str2double(temp_rating);
        fprintf(fid,'     rating.summer.emergency %.0f A;\n',temp_rating);
        fprintf(fid,'     rating.summer.continuous %.0f A;\n',temp_rating);
        fprintf(fid,'     rating.winter.emergency %.0f A;\n',temp_rating);
        fprintf(fid,'     rating.winter.continuous %.0f A;\n',temp_rating);
        fprintf(fid,'}\n\n');
    end
end

% Create line spacings 
fprintf(fid,'object line_spacing {\n');
fprintf(fid,'     name SinglePhase1A;\n');
fprintf(fid,'     distance_AN 2.3062m;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_spacing {\n');
fprintf(fid,'     name SinglePhase1B;\n');
fprintf(fid,'     distance_BN 2.3062m;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_spacing {\n');
fprintf(fid,'     name SinglePhase1C;\n');
fprintf(fid,'     distance_CN 2.3062m;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_spacing {\n');
fprintf(fid,'     name TwoPhase1AC;\n');
fprintf(fid,'     distance_AC 1.2192m;\n');
fprintf(fid,'     distance_CN 1.5911m;\n');
fprintf(fid,'     distance_AN 1.70388m;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_spacing {\n');
fprintf(fid,'     name ThreePhase1;\n');
fprintf(fid,'     distance_AB 0.97584m;\n');
fprintf(fid,'     distance_AC 1.2192m;\n');
fprintf(fid,'     distance_BC 0.762m;\n');
fprintf(fid,'     distance_BN 2.1336m;\n');
fprintf(fid,'     distance_AN 1.70388m;\n');
fprintf(fid,'     distance_CN 1.5911m;\n');
fprintf(fid,'}\n\n');

% Create all of the line configurations (67 of them + 3 oddballs)
fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_1PH-x4_ACSRx4_ACSR;\n');
fprintf(fid,'     conductor_B gld_4_ACSR;\n');
fprintf(fid,'     conductor_N gld_4_ACSR;\n');
fprintf(fid,'     spacing SinglePhase1B;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_1PH-xx4_ACSR4_ACSR;\n');
fprintf(fid,'     conductor_C gld_4_ACSR;\n');
fprintf(fid,'     conductor_N gld_4_ACSR;\n');
fprintf(fid,'     spacing SinglePhase1C;\n');
fprintf(fid,'}\n\n');
                          
fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_1PH-x2_ACSRx2_ACSR;\n');
fprintf(fid,'     conductor_B gld_2_ACSR;\n');
fprintf(fid,'     conductor_N gld_2_ACSR;\n');
fprintf(fid,'     spacing SinglePhase1B;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_1PH-x4_ACSRx4_WPAL;\n');
fprintf(fid,'     conductor_B gld_4_ACSR;\n');
fprintf(fid,'     conductor_N gld_4_WPAL;\n');
fprintf(fid,'     spacing SinglePhase1B;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_3PH_H-2/0_ACSR2/0_ACSR2/0_ACSR2_ACSR;\n');
fprintf(fid,'     conductor_A gld_2/0_ACSR;\n');
fprintf(fid,'     conductor_B gld_2/0_ACSR;\n');
fprintf(fid,'     conductor_C gld_2/0_ACSR;\n');
fprintf(fid,'     conductor_N gld_2_ACSR;\n');
fprintf(fid,'     spacing ThreePhase1;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_3PH_H-4_ACSR4_ACSR4_ACSR4_ACSR;\n');
fprintf(fid,'     conductor_A gld_4_ACSR;\n');
fprintf(fid,'     conductor_B gld_4_ACSR;\n');
fprintf(fid,'     conductor_C gld_4_ACSR;\n');
fprintf(fid,'     conductor_N gld_4_ACSR;\n');
fprintf(fid,'     spacing ThreePhase1;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_1PH-4_WPALxx2_WPAL;\n');
fprintf(fid,'     conductor_A gld_4_ACSR;\n');
fprintf(fid,'     conductor_N gld_4_ACSR;\n');
fprintf(fid,'     spacing SinglePhase1A;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_3PH_H-4_ACSR2_ACSR2_ACSR4_WPAL;\n');
fprintf(fid,'     conductor_A gld_4_ACSR;\n');
fprintf(fid,'     conductor_B gld_2_ACSR;\n');
fprintf(fid,'     conductor_C gld_2_ACSR;\n');
fprintf(fid,'     conductor_N gld_4_WPAL;\n');
fprintf(fid,'     spacing ThreePhase1;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_1PH-4_ACSRxx4_ACSR;\n');
fprintf(fid,'     conductor_A gld_4_ACSR;\n');
fprintf(fid,'     conductor_N gld_4_ACSR;\n');
fprintf(fid,'     spacing SinglePhase1A;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_3PH_H-4_ACSR4_ACSR4_ACSR4_WPAL;\n');
fprintf(fid,'     conductor_A gld_4_ACSR;\n');
fprintf(fid,'     conductor_B gld_4_ACSR;\n');
fprintf(fid,'     conductor_C gld_4_ACSR;\n');
fprintf(fid,'     conductor_N gld_4_WPAL;\n');
fprintf(fid,'     spacing ThreePhase1;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_1PH-2_ACSRxx2_ACSR;\n');
fprintf(fid,'     conductor_A gld_2_ACSR;\n');
fprintf(fid,'     conductor_N gld_2_ACSR;\n');
fprintf(fid,'     spacing SinglePhase1A;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_1PH-4_WPALxx4_ACSR;\n');
fprintf(fid,'     conductor_A gld_4_WPAL;\n');
fprintf(fid,'     conductor_N gld_4_ACSR;\n');
fprintf(fid,'     spacing SinglePhase1A;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_3PH_H-397_ACSR397_ACSR397_ACSR2/0_ACSR;\n');
fprintf(fid,'     conductor_A gld_397_ACSR;\n');	
fprintf(fid,'     conductor_B gld_397_ACSR;\n');
fprintf(fid,'     conductor_C gld_397_ACSR;\n');
fprintf(fid,'     conductor_N gld_2/0_ACSR;\n');
fprintf(fid,'     spacing ThreePhase1;\n');
fprintf(fid,'}\n\n');

% Page 2 
fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_1PH-2_ACSRxx4_ACSR;\n');
fprintf(fid,'     conductor_A gld_2_ACSR;\n');
fprintf(fid,'     conductor_N gld_4_ACSR;\n');
fprintf(fid,'     spacing SinglePhase1A;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_1PH-xx2_ACSR2_ACSR;\n');
fprintf(fid,'     conductor_C gld_2_ACSR;\n');
fprintf(fid,'     conductor_N gld_2_ACSR;\n');
fprintf(fid,'     spacing SinglePhase1C;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_1PH-xx4_WPAL4_WPAL;\n');
fprintf(fid,'     conductor_C gld_4_WPAL;\n');
fprintf(fid,'     conductor_N gld_4_WPAL;\n');
fprintf(fid,'     spacing SinglePhase1C;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_1PH-x4_WPALx4_WPAL;\n');
fprintf(fid,'     conductor_B gld_4_WPAL;\n');
fprintf(fid,'     conductor_N gld_4_WPAL;\n');
fprintf(fid,'     spacing SinglePhase1B;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_1PH-xx4_WPAL4_ACSR;\n');
fprintf(fid,'     conductor_C gld_4_WPAL;\n');
fprintf(fid,'     conductor_N gld_4_ACSR;\n');
fprintf(fid,'     spacing SinglePhase1C;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_1PH-x2_ACSRx1/0_TPX;\n');
fprintf(fid,'     conductor_B gld_2_ACSR;\n');
fprintf(fid,'     conductor_N gld_1/0_TPX;\n');
fprintf(fid,'     spacing SinglePhase1B;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_1PH-4_ACSRxx4_WPAL;\n');
fprintf(fid,'     conductor_A gld_4_ACSR;\n');
fprintf(fid,'     conductor_N gld_4_WPAL;\n');
fprintf(fid,'     spacing SinglePhase1A;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_1PH-xx4_ACSR1/0_TPX;\n');
fprintf(fid,'     conductor_C gld_4_ACSR;\n');
fprintf(fid,'     conductor_N gld_1/0_TPX;\n');
fprintf(fid,'     spacing SinglePhase1C;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_3PH_H-4_WPAL4_WPAL4_WPAL4_ACSR;\n');
fprintf(fid,'     conductor_A gld_4_WPAL;\n');
fprintf(fid,'     conductor_B gld_4_WPAL;\n');
fprintf(fid,'     conductor_C gld_4_WPAL;\n');
fprintf(fid,'     conductor_N gld_4_ACSR;\n');
fprintf(fid,'     spacing ThreePhase1;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_1PH-x4_WPALx4_ACSR;\n');
fprintf(fid,'     conductor_B gld_4_WPAL;\n');
fprintf(fid,'     conductor_N gld_4_ACSR;\n');
fprintf(fid,'     spacing SinglePhase1B;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_1PH-4_WPALxx4_WPAL;\n');
fprintf(fid,'     conductor_A gld_4_WPAL;\n');
fprintf(fid,'     conductor_N gld_4_WPAL;\n');
fprintf(fid,'     spacing SinglePhase1A;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_3PH_H-4_WPAL4_WPAL4_WPAL4_WPAL;\n');
fprintf(fid,'     conductor_A gld_4_WPAL;\n');
fprintf(fid,'     conductor_B gld_4_WPAL;\n');
fprintf(fid,'     conductor_C gld_4_WPAL;\n');
fprintf(fid,'     conductor_N gld_4_WPAL;\n');
fprintf(fid,'     spacing ThreePhase1;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_3PH_H-2_ACSR2_ACSR2_ACSR2_ACSR;\n');
fprintf(fid,'     conductor_A gld_2_ACSR;\n');
fprintf(fid,'     conductor_B gld_2_ACSR;\n');
fprintf(fid,'     conductor_C gld_2_ACSR;\n');
fprintf(fid,'     conductor_N gld_2_ACSR;\n');
fprintf(fid,'     spacing ThreePhase1;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_1PH-4_ACSRxx1/0_TPX;\n');
fprintf(fid,'     conductor_A gld_4_ACSR;\n');
fprintf(fid,'     conductor_N gld_1/0_TPX;\n');
fprintf(fid,'     spacing SinglePhase1A;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_3PH_H-4_ACSR2_ACSR2_ACSR4_ACSR;\n');
fprintf(fid,'     conductor_A gld_4_ACSR;\n');
fprintf(fid,'     conductor_B gld_2_ACSR;\n');
fprintf(fid,'     conductor_C gld_2_ACSR;\n');
fprintf(fid,'     conductor_N gld_4_ACSR;\n');
fprintf(fid,'     spacing ThreePhase1;\n');
fprintf(fid,'}\n\n');

%Page 3
fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_1PH-xx4_ACSR4_WPAL;\n');
fprintf(fid,'     conductor_C gld_4_ACSR;\n');
fprintf(fid,'     conductor_N gld_4_WPAL;\n');
fprintf(fid,'     spacing SinglePhase1C;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_1PH-4_ACSRxx2_ACSR;\n');
fprintf(fid,'     conductor_A gld_4_ACSR;\n');
fprintf(fid,'     conductor_N gld_2_ACSR;\n');
fprintf(fid,'     spacing SinglePhase1A;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_1PH-x4_WPALx1/0_TPX;\n');
fprintf(fid,'     conductor_B gld_4_WPAL;\n');
fprintf(fid,'     conductor_N gld_1/0_TPX;\n');
fprintf(fid,'     spacing SinglePhase1B;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_1PH-xx4_ACSR1/0_ACSR;\n');
fprintf(fid,'     conductor_C gld_4_ACSR;\n');
fprintf(fid,'     conductor_N gld_1/0_ACSR;\n');
fprintf(fid,'     spacing SinglePhase1C;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_1PH-2_ACSRxx4_WPAL;\n');
fprintf(fid,'     conductor_A gld_2_ACSR;\n');
fprintf(fid,'     conductor_N gld_4_WPAL;\n');
fprintf(fid,'     spacing SinglePhase1A;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_1PH-xx2/0_ACSR1/0_TPX;\n');
fprintf(fid,'     conductor_C gld_2/0_ACSR;\n');
fprintf(fid,'     conductor_N gld_1/0_TPX;\n');
fprintf(fid,'     spacing SinglePhase1C;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_2PH_H-2_ACSRx2_ACSR2_ACSR;\n');
fprintf(fid,'     conductor_A gld_2_ACSR;\n');
fprintf(fid,'     conductor_C gld_2_ACSR;\n');
fprintf(fid,'     conductor_N gld_2_ACSR;\n');
fprintf(fid,'     spacing TwoPhase1AC;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_1PH-2_WPALxx2_WPAL;\n');
fprintf(fid,'     conductor_A gld_2_WPAL;\n');
fprintf(fid,'     conductor_N gld_2_WPAL;\n');
fprintf(fid,'     spacing SinglePhase1A;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_1PH-2_ACSRxx4/0_TPX;\n');
fprintf(fid,'     conductor_A gld_2_ACSR;\n');
fprintf(fid,'     conductor_N gld_4/0_TPX;\n');
fprintf(fid,'     spacing SinglePhase1A;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_3PH_H-397_ACSR397_ACSR397_ACSR4_WPAL;\n');
fprintf(fid,'     conductor_A gld_397_ACSR;\n');
fprintf(fid,'     conductor_B gld_397_ACSR;\n');
fprintf(fid,'     conductor_C gld_397_ACSR;\n');
fprintf(fid,'     conductor_N gld_4_WPAL;\n');
fprintf(fid,'     spacing ThreePhase1;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_3PH_H-397_ACSR397_ACSR397_ACSR397_ACSR;\n');
fprintf(fid,'     conductor_A gld_397_ACSR;\n');
fprintf(fid,'     conductor_B gld_397_ACSR;\n');
fprintf(fid,'     conductor_C gld_397_ACSR;\n');
fprintf(fid,'     conductor_N gld_397_ACSR;\n');
fprintf(fid,'     spacing ThreePhase1;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_1PH-xx2_ACSR1/0_TPX;\n');
fprintf(fid,'     conductor_C gld_2_ACSR;\n');
fprintf(fid,'     conductor_N gld_1/0_TPX;\n');
fprintf(fid,'     spacing SinglePhase1C;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_1PH-x4_ACSRx2_WPAL;\n');
fprintf(fid,'     conductor_B gld_4_ACSR;\n');
fprintf(fid,'     conductor_N gld_2_WPAL;\n');
fprintf(fid,'     spacing SinglePhase1B;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_1PH-x4_ACSRx4_DPX;\n');
fprintf(fid,'     conductor_B gld_4_ACSR;\n');
fprintf(fid,'     conductor_N gld_4_DPX;\n');
fprintf(fid,'     spacing SinglePhase1B;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_3PH_H-2_ACSR2_ACSR4_ACSR4_ACSR;\n');
fprintf(fid,'     conductor_A gld_2_ACSR;\n');
fprintf(fid,'     conductor_B gld_2_ACSR;\n');
fprintf(fid,'     conductor_C gld_4_ACSR;\n');
fprintf(fid,'     conductor_N gld_4_ACSR;\n');
fprintf(fid,'     spacing ThreePhase1;\n');
fprintf(fid,'}\n\n');

% Page 4
fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_1PH-4_WPALxx1/0_TPX;\n');
fprintf(fid,'     conductor_A gld_4_WPAL;\n');
fprintf(fid,'     conductor_N gld_1/0_TPX;\n');
fprintf(fid,'     spacing SinglePhase1A;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_1PH-x4_ACSRx1/0_TPX;\n');
fprintf(fid,'     conductor_B gld_4_ACSR;\n');
fprintf(fid,'     conductor_N gld_1/0_TPX;\n');
fprintf(fid,'     spacing SinglePhase1B;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_1PH-4_ACSRxx1/0_3W_CS;\n');
fprintf(fid,'     conductor_A gld_4_ACSR;\n');
fprintf(fid,'     conductor_N gld_1/0_3W_CS;\n');
fprintf(fid,'     spacing SinglePhase1A;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_1PH-x2_ACSRx4_ACSR;\n');
fprintf(fid,'     conductor_B gld_2_ACSR;\n');
fprintf(fid,'     conductor_N gld_4_ACSR;\n');
fprintf(fid,'     spacing SinglePhase1B;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_1PH-x2_ACSRx1/0_3W_CS;\n');
fprintf(fid,'     conductor_B gld_2_ACSR;\n');
fprintf(fid,'     conductor_N gld_1/0_3W_CS;\n');
fprintf(fid,'     spacing SinglePhase1B;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_3PH_H-2/0_ACSR2/0_ACSR2/0_ACSR2/0_ACSR;\n');
fprintf(fid,'     conductor_A gld_2/0_ACSR;\n');
fprintf(fid,'     conductor_B gld_2/0_ACSR;\n');
fprintf(fid,'     conductor_C gld_2/0_ACSR;\n');
fprintf(fid,'     conductor_N gld_2/0_ACSR;\n');
fprintf(fid,'     spacing ThreePhase1;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_1PH-2_ACSRxx1/0_TPX;\n');
fprintf(fid,'     conductor_A gld_2_ACSR;\n');
fprintf(fid,'     conductor_N gld_1/0_TPX;\n');
fprintf(fid,'     spacing SinglePhase1A;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_3PH_H-4_WPAL4_WPAL4_WPAL1/0_TPX;\n');
fprintf(fid,'     conductor_A gld_4_WPAL;\n');
fprintf(fid,'     conductor_B gld_4_WPAL;\n');
fprintf(fid,'     conductor_C gld_4_WPAL;\n');
fprintf(fid,'     conductor_N gld_1/0_TPX;\n');
fprintf(fid,'     spacing ThreePhase1;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_1PH-x4_WPALx2_ACSR;\n');
fprintf(fid,'     conductor_B gld_4_WPAL;\n');
fprintf(fid,'     conductor_N gld_2_ACSR;\n');
fprintf(fid,'     spacing SinglePhase1B;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_3PH_H-2/0_ACSR2/0_ACSR2/0_ACSR2_WPAL;\n');
fprintf(fid,'     conductor_A gld_2/0_ACSR;\n');
fprintf(fid,'     conductor_B gld_2/0_ACSR;\n');
fprintf(fid,'     conductor_C gld_2/0_ACSR;\n');
fprintf(fid,'     conductor_N gld_2_WPAL;\n');
fprintf(fid,'     spacing ThreePhase1;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_1PH-xx4_ACSR2_ACSR;\n');
fprintf(fid,'     conductor_C gld_4_ACSR;\n');
fprintf(fid,'     conductor_N gld_2_ACSR;\n');
fprintf(fid,'     spacing SinglePhase1C;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_1PH-x4_ACSRx4_TPX;\n');
fprintf(fid,'     conductor_B gld_4_ACSR;\n');
fprintf(fid,'     conductor_N gld_4_TPX;\n');
fprintf(fid,'     spacing SinglePhase1B;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_3PH_H-4_ACSR4_ACSR4_ACSR4_TPX;\n');
fprintf(fid,'     conductor_A gld_4_ACSR;\n');
fprintf(fid,'     conductor_B gld_4_ACSR;\n');
fprintf(fid,'     conductor_C gld_4_ACSR;\n');
fprintf(fid,'     conductor_N gld_4_TPX;\n');
fprintf(fid,'     spacing ThreePhase1;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_1PH-4_ACSRxx6_WPAL;\n');
fprintf(fid,'     conductor_A gld_4_ACSR;\n');
fprintf(fid,'     conductor_N gld_6_WPAL;\n');
fprintf(fid,'     spacing SinglePhase1A;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_1PH-xx4_ACSR4_TPX;\n');
fprintf(fid,'     conductor_C gld_4_ACSR;\n');
fprintf(fid,'     conductor_N gld_4_TPX;\n');
fprintf(fid,'     spacing SinglePhase1C;\n');
fprintf(fid,'}\n\n');

% Page 5
fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_3PH_H-397_ACSR397_ACSR397_ACSR2/0_WPAL;\n');
fprintf(fid,'     conductor_A gld_397_ACSR;\n');
fprintf(fid,'     conductor_B gld_397_ACSR;\n');
fprintf(fid,'     conductor_C gld_397_ACSR;\n');
fprintf(fid,'     conductor_N gld_2/0_WPAL;\n');
fprintf(fid,'     spacing ThreePhase1;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_1PH-2/0_ACSRxx2_ACSR;\n');
fprintf(fid,'     conductor_A gld_2/0_ACSR;\n');
fprintf(fid,'     conductor_N gld_2_ACSR;\n');
fprintf(fid,'     spacing SinglePhase1A;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_3PH_H-2/0_ACSR2/0_ACSR2/0_ACSR4_ACSR;\n');
fprintf(fid,'     conductor_A gld_2/0_ACSR;\n');
fprintf(fid,'     conductor_B gld_2/0_ACSR;\n');
fprintf(fid,'     conductor_C gld_2/0_ACSR;\n');
fprintf(fid,'     conductor_N gld_4_ACSR;\n');
fprintf(fid,'     spacing ThreePhase1;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_1PH-xx4_WPAL1/0_TPX;\n');
fprintf(fid,'     conductor_C gld_4_WPAL;\n');
fprintf(fid,'     conductor_N gld_1/0_TPX;\n');
fprintf(fid,'     spacing SinglePhase1C;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_1PH-xx6_WPAL6_WPAL;\n');
fprintf(fid,'     conductor_C gld_6_WPAL;\n');
fprintf(fid,'     conductor_N gld_6_WPAL;\n');
fprintf(fid,'     spacing SinglePhase1C;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_1PH-x2_ACSRx4_TPX;\n');
fprintf(fid,'     conductor_B gld_2_ACSR;\n');
fprintf(fid,'     conductor_N gld_4_TPX;\n');
fprintf(fid,'     spacing SinglePhase1B;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_3PH_H-4_ACSR4_ACSR4_ACSR2_WPAL;\n');
fprintf(fid,'     conductor_A gld_4_ACSR;\n');
fprintf(fid,'     conductor_B gld_4_ACSR;\n');
fprintf(fid,'     conductor_C gld_4_ACSR;\n');
fprintf(fid,'     conductor_N gld_2_WPAL;\n');
fprintf(fid,'     spacing ThreePhase1;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_1PH-x4_ACSRx1/0_3W_CS;\n');
fprintf(fid,'     conductor_B gld_4_ACSR;\n');
fprintf(fid,'     conductor_N gld_1/0_3W_CS;\n');
fprintf(fid,'     spacing SinglePhase1B;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_1PH-xx2_ACSR4_DPX;\n');
fprintf(fid,'     conductor_C gld_2_ACSR;\n');
fprintf(fid,'     conductor_N gld_4_DPX;\n');
fprintf(fid,'     spacing SinglePhase1B;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_3P_1/0_AXNJ_DB;\n');
fprintf(fid,'     conductor_A gld_1/0_ACSR; //These are not the correct values,\n'); 
fprintf(fid,'     conductor_B gld_1/0_ACSR; //but are used to approximate for 3P & 1P.\n'); 
fprintf(fid,'     conductor_C gld_1/0_ACSR;\n'); 
fprintf(fid,'     conductor_N gld_1/0_ACSR;\n');
fprintf(fid,'     spacing ThreePhase1;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_1P_1/0_AXNJ_DB_A;\n');
fprintf(fid,'     conductor_A gld_1/0_ACSR;\n');
fprintf(fid,'     conductor_N gld_1/0_ACSR;\n');
fprintf(fid,'     spacing SinglePhase1A;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_1P_1/0_AXNJ_DB_B;\n');
fprintf(fid,'     conductor_B gld_1/0_ACSR;\n');
fprintf(fid,'     conductor_N gld_1/0_ACSR;\n');
fprintf(fid,'     spacing SinglePhase1B;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_1P_1/0_AXNJ_DB_C;\n');
fprintf(fid,'     conductor_C gld_1/0_ACSR;\n');
fprintf(fid,'     conductor_N gld_1/0_ACSR;\n');
fprintf(fid,'     spacing SinglePhase1C;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name CAP_LINE;      //Also known as 1PH-Connector.\n');
fprintf(fid,'     conductor_A gld_600_CU; //These are not the correct values, but\n');
fprintf(fid,'     conductor_B gld_600_CU; //will be used to approx. low loss lines.\n');
fprintf(fid,'     conductor_C gld_600_CU;\n');
fprintf(fid,'     conductor_N gld_600_CU;\n');
fprintf(fid,'     spacing ThreePhase1;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object line_configuration {\n');
fprintf(fid,'     name gld_3PH-Connector;\n');
fprintf(fid,'     conductor_A gld_600_CU;\n');
fprintf(fid,'     conductor_B gld_600_CU;\n');
fprintf(fid,'     conductor_C gld_600_CU;\n');
fprintf(fid,'     conductor_N gld_600_CU;\n');
fprintf(fid,'     spacing ThreePhase1;\n');
fprintf(fid,'}\n\n');

%% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%Create Triplex Line and Conductor Configurations
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

fprintf(fid,'object triplex_line_conductor {\n');
fprintf(fid,'     name gld_4/0triplex;\n');
fprintf(fid,'     resistance 1.535;\n');
fprintf(fid,'     geometric_mean_radius 0.0111;\n');
fprintf(fid,'     rating.summer.emergency 315 A;\n');
fprintf(fid,'     rating.summer.continuous 315 A;\n');
fprintf(fid,'     rating.winter.emergency 315 A;\n');
fprintf(fid,'     rating.winter.continuous 315 A;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object triplex_line_configuration {\n');
fprintf(fid,'     name gld_4/0Triplex;\n');
fprintf(fid,'     conductor_1 gld_4/0triplex;\n'); 
fprintf(fid,'     conductor_2 gld_4/0triplex;\n');
fprintf(fid,'     conductor_N gld_4/0triplex;\n');
fprintf(fid,'     insulation_thickness 0.08;\n');
fprintf(fid,'     diameter 0.368;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object triplex_line_configuration {\n');
fprintf(fid,'     name gld_750_Triplex;       //These values are not correct, but\n');
fprintf(fid,'     conductor_1 gld_4/0triplex; //there are only four of them.\n');
fprintf(fid,'     conductor_2 gld_4/0triplex;\n');
fprintf(fid,'     conductor_N gld_4/0triplex;\n');
fprintf(fid,'     insulation_thickness 0.08;\n');
fprintf(fid,'     diameter 0.368;\n');
fprintf(fid,'}\n\n');


%% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%Create line objects
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

fprintf(fid,'// Overhead Lines\n\n');

for i=1:EndLines
    if (~isempty(findstr(char(RawLines{1}(i)),'CAP')))
        % if it's a capacitor line don't create a line - 
        %  create capacitor lines by hand to combine the three phasees
    elseif (~isempty(findstr(char(RawLines{1}(i)),'_sw')))
        %switches
        if (~isempty(findstr(char(RawLines{1}(i)),'WF586_48332_sw')) || ~isempty(findstr(char(RawLines{1}(i)),'V7995_48332_sw')) || ~isempty(findstr(char(RawLines{1}(i)),'WD701_48332_sw')))
            % do nothing - these are open switches connecting two different
            % phases - doesn't work in NR right now
        else
            fprintf(fid,'object switch {\n');
            fprintf(fid,'     phases %sN;\n',char(RawLines{3}(i)));
            fprintf(fid,'     name %s;\n',gld_strict_name(char(RawLines{1}(i))));
            fprintf(fid,'     from %s;\n',gld_strict_name(char(RawLines{2}(i))));
            fprintf(fid,'     to %s;\n',gld_strict_name(char(RawLines{4}(i))));
            status = strtrim(char(RawLines{9}(i)));
            if (~isempty(findstr(status,'open')))
                fprintf(fid,'     status OPEN;\n');
            else
                fprintf(fid,'     status CLOSED;\n');
            end
            fprintf(fid,'}\n\n');
        end
    elseif (~isempty(findstr(char(RawLines{8}(i)),'1P_1/0_AXNJ_DB')))
        fprintf(fid,'object overhead_line {\n');
        fprintf(fid,'     phases %sN;\n',char(RawLines{3}(i))); 
        fprintf(fid,'     name %s;\n',char(RawLines{1}(i)));
        fprintf(fid,'     from %s;\n',gld_strict_name(char(RawLines{2}(i))));
        fprintf(fid,'     to %s;\n',gld_strict_name(char(RawLines{4}(i))));
        fprintf(fid,'     length %f%s;\n',LengthLines(i),char(RawLines{7}(i)));
        k = strtrim(char(RawLines{8}(i)));
        fprintf(fid,'     configuration %s;\n',gld_strict_name(strcat(k,'_',char(RawLines{3}(i)))));
        fprintf(fid,'}\n\n');
    else
        % normal lines
        fprintf(fid,'object overhead_line {\n');
        fprintf(fid,'     phases %sN;\n',char(RawLines{3}(i)));
        % one odd ball line had a node name, so add LN to it
        if (strcmp(char(RawLines{1}(i)),'293471'))
            fprintf(fid,'     name LN%s;\n',char(RawLines{1}(i)));
        else
            fprintf(fid,'     name %s;\n',char(RawLines{1}(i)));
        end
        fprintf(fid,'     from %s;\n',gld_strict_name(char(RawLines{2}(i))));
        fprintf(fid,'     to %s;\n',gld_strict_name(char(RawLines{4}(i))));
        fprintf(fid,'     length %f%s;\n',LengthLines(i),char(RawLines{7}(i)));
          k = strtrim(char(RawLines{8}(i)));
        fprintf(fid,'     configuration %s;\n',gld_strict_name(k));
        fprintf(fid,'}\n\n');
        
    end
end
fprintf(fid,'object overhead_line {\n');
fprintf(fid,'     phases ABCN;\n'); 
fprintf(fid,'     name CAP_1;\n');
fprintf(fid,'     from Q16642;\n');
fprintf(fid,'     to Q16642_CAP;\n');
fprintf(fid,'     length 0.01km;\n');
fprintf(fid,'     configuration CAP_LINE;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object overhead_line {\n');
fprintf(fid,'     phases ABCN;\n'); 
fprintf(fid,'     name CAP_2;\n');
fprintf(fid,'     from Q16483;\n');
fprintf(fid,'     to Q16483_CAP;\n');
fprintf(fid,'     length 0.001km;\n');
fprintf(fid,'     configuration CAP_LINE;\n');
fprintf(fid,'}\n\n');

fprintf(fid,'object overhead_line {\n');
fprintf(fid,'     phases ABCN;\n'); 
fprintf(fid,'     name CAP_3;\n');
fprintf(fid,'     from L2823592;\n');
fprintf(fid,'     to L2823592_CAP;\n');
fprintf(fid,'     length 0.01km;\n');
fprintf(fid,'     configuration CAP_LINE;\n');
fprintf(fid,'}\n\n');

%% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%Create Triplex-Line objects
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

fprintf(fid,'// Triplex Lines\n\n');
disp('Printing triplex lines...');
for i=1:EndTripLines
    fprintf(fid,'object triplex_line {\n');
    fprintf(fid,'     name %s;\n',char(RawTripLines{1}(i)));
    Tp = char(RawTripLines{4}(i));
    Tphase = Tp(10);
    fprintf(fid,'     phases %sS;\n',Tphase);
    fprintf(fid,'     from %s;\n',gld_strict_name(char(RawTripLines{2}(i))));
    fprintf(fid,'     to %s;\n',gld_strict_name(char(RawTripLines{4}(i))));
%    fprintf(fid,'     length %2.0fft;\n',RawTripLines{7}(i));
    fprintf(fid,'     length 100ft;\n');
    fprintf(fid,'     configuration %s;\n',gld_strict_name(char(RawTripLines{6}(i))));
    fprintf(fid,'}\n\n');
end

fprintf(fid,'//object group_recorder {\n');
fprintf(fid,'//	group "class=capacitor";\n');
fprintf(fid,'//	property switchA;\n');
fprintf(fid,'//	interval 15;\n');
fprintf(fid,'//	file capsA.csv;\n');
fprintf(fid,'//};\n');
fprintf(fid,'//object group_recorder {\n');
fprintf(fid,'//	group "class=capacitor";\n');
fprintf(fid,'//	property switchB;\n');
fprintf(fid,'//	interval 15;\n');
fprintf(fid,'//	file capsB.csv;\n');
fprintf(fid,'//};\n');
fprintf(fid,'//object group_recorder {\n');
fprintf(fid,'//	group "class=capacitor";\n');
fprintf(fid,'//	property switchC;\n');
fprintf(fid,'//	interval 15;\n');
fprintf(fid,'//	file capsC.csv;\n');
fprintf(fid,'//};\n');
fprintf(fid,'//\n');
fprintf(fid,'//object group_recorder {\n');
fprintf(fid,'//	group "class=regulator";\n');
fprintf(fid,'//	property tap_A;\n');
fprintf(fid,'//	interval 15;\n');
fprintf(fid,'//	file regsA.csv;\n');
fprintf(fid,'//};\n');
fprintf(fid,'//object group_recorder {\n');
fprintf(fid,'//	group "class=regulator";\n');
fprintf(fid,'//	property tap_B;\n');
fprintf(fid,'//	interval 15;\n');
fprintf(fid,'//	file regsB.csv;\n');
fprintf(fid,'//};\n');
fprintf(fid,'//object group_recorder {\n');
fprintf(fid,'//	group "class=regulator";\n');
fprintf(fid,'//	property tap_C;\n');
fprintf(fid,'//	interval 15;\n');
fprintf(fid,'//	file regsC.csv;\n');
fprintf(fid,'//};\n');

if ( strcmp(houses,'y')~=0 )
    fprintf(fid,'// Nominal peak load = %.1f + j%.1f kVA\n', 0.001*total_reload, 0.001*total_imload);
    fprintf(fid,'// Houses: %d from %.1f to %.1f sq feet, total area %.1f sq ft\n', ...
        total_houses, floor_area_small, floor_area_large, total_floor_area);
    fprintf(fid,'// Electric water heaters: %d totaling %.1f kW\n', total_wh_num, total_wh_kw);
    fprintf(fid,'// Air conditioners:       %d totaling %.1f kW\n', total_ac_num, total_ac_kw);
    fprintf(fid,'// Solar:                  %d totaling %.1f kW\n', total_solar_num, total_solar_kw);
    fprintf(fid,'// Storage:                %d totaling %.1f kW\n', total_battery_num, total_battery_kw);
    fprintf(fid,'// Waterheater load is resistive\n');
    fprintf(fid,'// HVAC load ZIP=0.2,0.0,0.8 with variable power factor as input\n');
    fprintf(fid,'//   (the fan load ZIP=0.2534,0.7332,0.0135 and pf=0.96)\n');
    fprintf(fid,'// The non-responsive ZIP load is input all constant current, pf=0.95\n');
end


fclose('all');
disp('File generation completed.');
clear;
