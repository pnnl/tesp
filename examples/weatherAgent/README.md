# Weather Agent

Copyright (c) 2017-20, Battelle Memorial Institute

This weather agent needs an environment variable WEATHER_CONFIG to be set and point to the WeatherConfig.json file.

It reads in the csv weather data and the example data file is provided in this folder. If it is hourly data, the agent can do quadratic interpolation.

The WeatherConfig.json sets the following parameters:  
	- *"name": string, has to be "weather",  
	- *"StartTime": string, start of the simulation, for example "2000-01-01 00:00:00",  
	- *"time_stop": string, length of the simulation, unit can be "d, day, days, h, hour, hours, m, min, minute, minutes, s, sec, second, seconds", for example "70m",  
	- *"time_delta": string, this is the time step that fncs broker registers and uses to find peer time for other federates, peer time is registered at handshake and cannot be changed by fncs::update_time_delta() function call, unit can be "d, day, days, h, hour, hours, m, min, minute, minutes, s, sec, second, seconds", for example "1s",  
	- *"publishInterval": string, how often the agent publishes weather data, for example "5m",  
	- *"Forecast": integer, 1: true for forecast; 0, NO forecast,  
	- *"ForecastLength": string, how far into the future the forecast should be, for example "24h",  
	- *"PublishTimeAhead": string, how much time ahead of the supposed publish time to publish the data, unit can be "d, day, days, h, hour, hours, m, min, minute, minutes, s, sec, second, seconds", for example "8s",  
	- *"AddErrorToForecast": integer, 1: true; 0: false,  
	- *"broker": string, has to be "tcp://localhost:5570",  
	- *"forecastPeriod": integer, this is the period/cycle used in weather forecast to calculate the error, for example 48,  
	- *"parameters": are parameters needed in the weather forecast to add error, each weather factor could have different parameters, for now, only the parameters for temperature is set, the other ones do not have a good tested parameters  
		- *"temperature": name of the factor, we also have humidity, solar_direct, solar_diffuse, pressure, wind_speed  
			- *"distribution": 0: Uniform distribution; 1: Triangular distribution; 2: Truncated normal distribution  
			- *"P_e_bias": pu maximum bias at first hour, for example: 0.5,   
			- *"P_e_envelope": pu maximum error from mean values, for example: 0.08,  
			- *"Lower_e_bound": pu of the maximum error at the first hour, for example: 0.5  

The following topics are published by the agent:  
	- *weather/temperature  
	- *weather/humidity  
	- *weather/solar_direct  
	- *weather/solar_diffuse  
	- *weather/pressure  
	- *weather/wind_speed  
	- *weather/temperature/forecast  
	- *weather/humidity/forecast  
	- *weather/solar_direct/forecast  
	- *weather/solar_diffuse/forecast  
	- *weather/pressure/forecast  
	- *weather/wind_speed/forecast  
