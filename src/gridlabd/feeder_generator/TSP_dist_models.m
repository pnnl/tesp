%	Copyright (C) 2017 Battelle Memorial Institute
clear;
clc;

%% User defined paramters
num_models = 1;
rng_seed = 401; % Seeds the random number generator that will be used to 
                % provide seeds for the Feeder_Generator_TSP_function.m
                % random number generator.
PV_penetration_factors = [0.0]; % Length should equal num_models
ES_penetration_factors = [0.0]; % Length should equal num_models
input_directory = './Input_feeders/'; %Directory of unpopulated feeders
output_directory = './Output_feeders/'; %Directory for populated feeders

rng(rng_seed,'twister');
rand_val = floor(rand * 10000);
for idx=1:num_models
    %% Feeder Generator function parameters
    % 1 - Random number seed for individual houses
    % 2 - PV pentration factor
    % 3 - ES (energy storage) penetration factor
    % 4 - Number of three-phase commercial structures to add. 
    %       Largest value limited by existing three-phase commercial
    %       loads in unpopulated feeder
    % 5 - Directory of unpopulated feeders
    % 6 - Directory for populated feeders
    Feeder_Generator_TSP_function(rand_val, PV_penetration_factors,...
        ES_penetration_factors, 1, input_directory, output_directory);
end