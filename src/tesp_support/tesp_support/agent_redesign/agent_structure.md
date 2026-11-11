# What is an agent?

Fundamentally, the device agent is responsible for probing the device, retreiving the physical device state, and then using that information to define the agent's available flexibility to bid into the market. 

The customer preference curve and the price/quantity bid curve should not depend on the specific device, and should therefore be separate functions from the agents themselves. So the device agent really only needs to do two things, *1. Observe*, and *2. Define Flexibility*. The output flexibility can then be sent to the preference curve agent, which sends its output to the price/quantity bid curve agent. 

## Agent Function 1: Observe 
*Send signal to device to retrieve current physical state*

### Possible Methods:

 -| Physics-Based (Full) |	Stub
-- | -- | --
Function | reads GridLAB-D object state | "reads" approximate physical model of device or defines statistical approximation
Method | HELICS/FNCS messager to retrieve GridLAB-D Object State	| 1. Agent-based approximation, or <br/> 2. Statistical approximation (i.e., ReStock)

### Required Inputs:

Device |	Observations
-- | --
HVAC | Indoor air temp, COOL/HEAT ON, thermostat setpoint, `hvac_kw` (real power consumption)
Water Heater | 	Tank setpoint, tank temperature (upper/lower), element status, draw rate, `wh_kw` (real power consumption)
EV Charger	| SoC, charge rate, power draw, arrival time
Battery	| SoC, capacity, charge/discharge rate, device temp
PV	| `pv_kw` (real power generation)


## Agent Function 2: Define Flexibility 
*Given (1. Observe), define possible operating profile and corresponding amenity*

Contains an approximate physical model of the device to project possible outputs based on the current observed state. True regardless of whether simulation uses full physical model or approximation to perform observations.

### Required Inputs: 

1. Observations and...

Device |	Definitions/Constraints
-- | --
HVAC	| Slider setting, deadband, thermal mass, fuel type, air exchange
Water Heater	| Tank volume, fuel type, efficiency
EV Charger	| Max/Min power draw, EV capacity, schedule
Battery	| Min/Max SoC, charge/discharge efficiency, operating mode (reserve, bill savings, etc.), 
PV	| Array size, generating efficiency, etc.

### Outputs:
*Universal regardless of agent device*

Parameter	| Definition
-- | --
Quantity range [Q_min, Q_max] | 	 the minimum and maximum electrical power the device could consume in the upcoming market interval.
Amenity mapping |	A function or table mapping each feasible power level to an amenity metric (e.g., predicted indoor temperature deviation from setpoint).
Baseline operating point |	The power level the device would consume if it were simply tracking the customer's desired amenity setpoint with no price consideration.



## Previous Work

Looking first at the HVAC agent, we have a few agent designs to compare and build from as a foundation. They are 1. the original DSOT agent, 2. Trevor's redesign from last FY, and 3. Nathan's AI-agent redesign of the full TESP functionality. 

*An AI-summary of the comparison between the original DSOT agent and Trevor's redesign:*

Attribute | hvac_agent.py (original) | 	hvac_new_agent.py (redesign)
-- | -- | --
Structure |	One HVACDSOT class, about 2,600 lines. Every attribute and method sits on self.	| About 18 classes joined by composition: HVACDSOTAgent holds Temperatures, Schedule, Forecasts, Asset and BiddingStrategy. Asset holds State, Structure, AssetModel (with EnvironmentModel inside) and System. BiddingStrategy holds the DA and RT strategies, market interfaces and DSOT4pointBid.
Configuration | 	Constructor takes hvac_dict and house_properties, plus many hard-coded constants (COP and capacity coefficients, latent load fraction 0.3, window-to-wall ratio 0.15, door area 19.5, mass gain fractions 0.5, windowLength=48, R-value limits) | 	A nested config dict, applied by init_class_attributes() (hvac_new_agent.py:52). Unknown keys raise an error and attributes left as None log a warning. Almost all constants come from config.
Modes and types | 	Strings: 'Cooling', 'HEAT_PUMP', 'GAS'	| Enums: ThermostatMode, HeatingSystemType, WindowFrameType and others
Physics	| One large calc_etp_model(). The heat flows and ETP matrices are built inline inside formulate_bid_rt(). | 	Small single-purpose methods: calc_UA/CA/HM/CM, calc_Qh/Qi/Qs/Qa/Qm, calc_all_heat_flows, calc_AEI, simulate_time_step
Logging	| `log.log(model_diag_level, ...)` | 	Standard `logging.getLogger(__name__)`
Docs | 	One very large class docstring listing every attribute |	A docstring per method, a units header, and ASCII diagrams of the ETP model and heat flows
Dead code |	Removed in the redesign: the PuLP linear branch, the unused use_DA_curve / use_leg_clearing flags, commented-out debugging, and eval() on HELICS messages | 	

*Some AI-observations*:

### Physics that changed during the port (probably unintentionally)
* UA no longer includes air infiltration. The original adds Vterm * ac_per_hr (hvac_agent.py:1253), but calc_UA() (hvac_new_agent.py:1017) leaves it out. airchange_per_hour is still read but never used.
* The design cooling capacity formula has different parentheses. In the original, the oversizing and latent factors multiply the whole load, including internal and solar gains (hvac_agent.py:1263). In the new code they only multiply the UA·ΔT term (hvac_new_agent.py:1975).
The heat pump heating capacity isn't rounded. It copies the local, unrounded cooling value (:1983).
The cooling Qh divisor changed from 1 + 0.1 + … (i.e. 1.1) to 1.01 + … (:1420). This looks like a typo.
* solar_heatgain_factor stays at 0. calc_solar_heatgain_factor() is never called during initialization (:710-714). The open-questions document also says the planned rename to total_solar_aperture hasn't been done.
Two window glazing treatments are missing. The WindowGlazingTreatment enum has no LOW_S or HIGH_S (treatments 4 and 5 in the original, hvac_agent.py:1135-1181).
* The forecast eps and latent_factor are never computed. The original sets them at :756 and :2385. In the new code eps stays 0 and latent_factor stays an empty list, so the DA estimates divide by an empty list.
* ProfitMargin_slope is now a config value (0) instead of being derived from slider (hvac_agent.py:766).
* The RT interpolation counter never resets. formulate_da_bid resets RT_minute_count_interpolation on the DA strategy object (:2561), but the RT strategy reads its own copy (:2608). After the first hour, the 0- and 30-minute interpolation branches never run again.

### Functionality not ported yet
* Turning a cleared price into a setpoint: inform_bid and bid_accepted. This is the original's step 4, "market control mapping", and it's the step that actually controls the thermostat.
Clearing a DA bid: set_da_cleared_quantity.
Deciding the thermostat mode and whether the house participates: done in set_air_temp, hvac_agent.py:1880-1891.
* All the HELICS-facing setters (set_temperature, set_hvac_load, set_hvac_state, and so on). helics_topic_map is just a stub.
* The DA sequence. The original runs DA_model_parameters → DA_optimal_quantities → formulate_bid_da. The new code has the pieces but nothing calls them in order or sets optimized_Quantity or TIME.
* Recomputing the RT state before each bid. The original rebuilds capacities, heat flows and A_ETP/B_ETP at the start of every formulate_bid_rt. The new form_rt_bid() assumes the caller has already done this, and the testbed never calls calc_AEI().

### Bugs that stop the new agent from running

#### Construction:
* init_class_attributes() returns None, but its result is assigned to self.agent, self.asset and self.market (:115, :530, :2019). Every later self.agent.temp... call fails.
* HVACDSOTAsset passes its whole dict to init_class_attributes, and that dict contains sub-dicts with keys the class doesn't have, so it raises KeyError.
* Enums and nested classes are instantiated with no arguments: ThermostatMode() (:532), HeatingSystemType() (:1143) and HVACDSOTEnvironmentModel() (:539, :1145).
* HVACDSOTAssetModel reads asset.env_model before it exists. It also uses a fresh, all-zero ETPStructureParams() instead of the structure model's computed one (:1142), so np.linalg.inv(A_ETP) gets a singular matrix.
* HVACDSOTDABiddingStrategy and HVACDSOTRTBiddingStrategy inherit from HVACDSOTBiddingStrategy. They call super().__init__ with the wrong arguments, before self.agent is set (:2153, :2584). If that call worked it would recurse forever, because the parent constructs both children. These should hold a reference to the parent, not inherit from it.
* HVACDSOTSystemModel resets design_cooling_capacity to None after the config has been applied (:1838). calc_heating_COP and calc_cooling_COP assign by index into empty lists, which raises IndexError.
* The testbed config doesn't match the code:
    * structure_model and system_model are nested under asset_model in the config.
    * There's no bidding_strategy key.
    * The config uses windowLength_hr, but the code expects windowLength.
    * window_exterior_transmission_coefficient isn't a declared attribute, so it raises KeyError.
    * The testbed imports a ThermoStatMode that doesn't exist and passes a name= keyword that the constructor doesn't accept.

#### Methods:
* Wrong arguments:
    * Several methods are called on the class instead of an instance (HVACSchedule.get_scheduled_setpoint(...), HVACDSOTSystemModel.calc_cooling_capacity(), and others).
    * calc_Qh receives 5 arguments but takes 4, and calc_Qs() is called with no arguments.
    * change_basepoint passes model_diag_level (0) as the slider argument (:334). That sets flexibility to zero.
* Logic errors:
    * get_scheduled_setpoint compares day_of_week against hour boundaries (:275-287).
    * generate_forecast_times appends the same timestamp every time through the loop (:474).
    * The length check in calc_solar_gain_forecast uses and where it needs or.
* Range checks that can never fire: validate_attributes uses lower > x >= upper (:776-792, :1848). The glazing check is compared against the air-change limits, and the exterior_wall_fraction == 0 branch does nothing.
* Solar gain: sim_time.hour() is called as a method, and 15 * sim_time.utcoffset() multiplies a timedelta (:1755-1758).
* Pyomo model:
    * The variable is declared as hvac_quant but read as quan_hvac (:2416, :2505).
    * obj_rule and formulate_da_bid still compare against the strings 'Cooling', 'Heating' and 'HEAT_PUMP' instead of the enums. The "gas heating → zero bid" shortcut therefore never triggers.
    * self.solver and forecasts.price_forecast don't exist.
* mid_point can be unbound when it reaches the return statements at :405 and :2245.

#### Where the port is faithful
The core algorithms carry over almost line for line:
* the RT 5-point temperature/quantity curve simulation (estimate_hvac_energy_in_rt_period)
* the 4-point RT and DA bid construction
* the DA optimization objective and constraints
* the window R-value and transmission lookups
* the CA, HM and CM formulas
* the solar flux maths

Once the wiring is fixed, these are good places for regression tests against the original.

#### Design Observations
*With Nathan's redesigned agent added for context, additional observations based on the desired structure defined in the first section of this document:*

* **Observation is a swappable component; flexibility is not.** The agent always defines flexibility with its own light physics model, whichever observer produced the state. Only "where did this state come from?" changes between GridLAB-D, the physics stub and the statistical stub.
* **What's measured is kept separate from what's configured.** The current HVACState (data_types.py:21) mixes per-step measurements (air temperature, hvac_on) with fixed house parameters (UA, Ca, COP). Your spec already separates "Observations" from "Definitions/Constraints", and the code should too. Otherwise a statistical stub would have to invent UA values just to fill in an observation.
* **The output carries an amenity map that any device can produce.** The preference-curve and bid-curve scripts are meant to work for every device, so they should only ever see (kW, amenity value, metric name). They should never see anything HVAC-specific.

#### Defining flexibility
* Short-circuit when there's no flexibility. If the mode is OFF, the heating fuel is gas, or the device isn't participating, return q_min = q_max = q_baseline = measured kW. This covers the "gas heating → zero bid" case in DSOT.
* Set the comfort band from the slider: [sp − range_low_limit·slider, sp + range_high_limit·slider]. This is how DSOT does it (hvac_agent.py:912).
Find the most power the unit can draw: Q_cap = capacity(T_out) / COP(T_out) / 3412. The temperature-adjusted COP and capacity functions in HVACModel can be reused as they are.
* Exploit linearity. Hold the HVAC power at an average level q over the interval. Because the ETP model is linear, the end-of-interval indoor temperature is then affine in q: T_end(q) = T_end(0) + s·q. Two simulations, at q = 0 and q = Q_cap, give the whole relationship. From that:
    * q_baseline = the q that ends the interval at the customer setpoint
    * q_min and q_max = the q values that end the interval at the two edges of the comfort band
    * all three are clipped to [0, Q_cap]
* Build the amenity map by sampling (q, T_end(q) − setpoint) on a grid. For this model the map is a straight line, but the table format still works if the statistical stub later produces something non-linear.

I prefer this to the 5-setpoint deadband sweep in HVACModel.estimate_flexibility (device_models.py:480), which in turn ports DSOT formulate_bid_rt, for four reasons:

* The amenity map is monotone. The sweep can come out non-monotone.
Power isn't quantized. With 10 Euler steps the sweep can only produce duty cycles in 10% steps.
* It costs two simulations instead of six.
* It's literally "power level → amenity", which is how your spec phrases it.

I'd still keep the sweep as an optional method="setpoint_sweep" so the results can be checked against DSOT.

#### Things to fix rather than copy
* The current GridLAB-D read path would report every HVAC as OFF.
    * read_hvac_state works out the mode by looking for COOL or HEAT in power_state (gridlabd_interface.py:112). TESP publishes power_state as ON/OFF. DSOT only used it for hvac_on and worked out the mode from air temperature against the setpoint midpoint (hvac_agent.py:1884). As written, the mode is always "off", so flexibility is always zero.
    * It also divides hvac_load by 1000. DSOT treats hvac_load as kW already (hvac_agent.py:1831).
    * I'd confirm the other house property names (Ca, Hm and so on) against the GridLAB-D house_e schema as well.
* Use the original DSOT physics. That means infiltration in UA and the original design-capacity formula, not hvac_new_agent.py, which drops both.
* Leave out power_to_setpoint, setpoint_to_power and update_internal_state. They translate market results into control actions, which is a different step from your two tasks. They should live in a separate control-translation module.
* The statistical stub can't observe mass temperature. The flexibility model should accept mass_temp=None and estimate it, either from the indoor air temperature or by tracking it from step to step.
* Running the stub and the flexibility model on the same ETP gives them a perfect forecast. Stub-mode results will look better than GridLAB-D mode. I'd add an option to perturb the stub's parameters (for example ±10% on UA and CM) so the agent's model isn't exactly the "true" device.
* Decide where the slider belongs. Here the slider sets how wide the comfort band is. If the preference-curve script also uses it (or uses k for the same purpose), the customer's preference gets counted twice. It should be clear which script owns what.
* Fit the output into the existing types. I'd add an optional amenity_map field to the shared FlexibilityEnvelope rather than create a separate type. Existing consumers like PreferenceCurve keep working, and the Q_min_p50/p90/p99 fields are already there for when the statistical stub supplies uncertainty.


# Redesign Decisions

### Weather and house inputs are separate.
* WeatherForecast holds outdoor temperature, humidity and solar flux. It's shared by every device at a location.
* HouseForecast holds internal gains and the customer's cooling and heating setpoints. HouseForecast.from_schedule() builds the setpoints from the standard DSO+T thermostat schedule.
* Both work regardless of where the observation came from. If a forecast is finer or coarser than the market interval, the code averages over each interval, and it raises an error if the horizon runs past the end of a forecast.

### The horizon is day-ahead now and real-time later.
* MarketHorizon.day_ahead(t) gives 48 one-hour intervals. HVACAgentStub.update(sim_time, weather, house) observes the device and then defines flexibility, and you call it every hour with fresh forecasts.
* MarketHorizon.real_time(t) gives one 5-minute interval and runs through the same code.
* Each hour's flexibility assumes the earlier hours run at their baseline. Effects that span hours, like pre-cooling and then coasting, aren't modelled. The docstring says so.

### The amenity metric is configurable.
* HVACFlexibilityModel("end_of_interval_deviation") is the default, measured in °F.
* HVACFlexibilityModel("degree_minutes_outside_band") is the other built-in option, measured in °F·min.
* You can also subclass AmenityMetric for your own research design; there's a test showing one.

### Observers.
* GridLABDHVACObserver reads the GridLAB-D house.
* PhysicsStubHVACObserver runs its own small house model with deadband cycling. parameter_scaling (for example {"UA": 1.1}) makes it differ from the agent's model so the agent isn't predicting a house it knows perfectly.
* StatisticalStubHVACObserver is an interface only until the ResStock data is imported.

### Choices I made that you should check
* The amenity map covers the whole range [0, capacity], not just [Q_min, Q_max]. My first version covered only the feasible range. That made the degree-minutes map all zeros, and the end-of-interval map just repeated the two comfort-band edges every hour. The map now always includes exact points at Q_min, the baseline and Q_max. Points outside the feasible range show what it costs to leave the comfort band. An example for one afternoon hour (the "Penalty" column is degree-minutes outside the band):

Power (kW)	| 0.0	| 1.22 (Q_min)	| 1.66 (baseline)	| 1.92 (Q_max)	| 3.99 (capacity)
-- | -- | -- | -- | -- | -- |
End-of-hour deviation (°F)	| +5.8	| +1.55	| 0.0	| −0.93	| −8.2
Degree-minutes outside band	| 132	| 0	| 0	| 0	| 254

* What counts as feasible. The range is every power level whose comfort violation is within the metric's tolerance of the smallest achievable violation. If the band can't be reached at all, for example starting at 95°F in a 5-minute interval, the range collapses to the least-bad power and the interval is marked comfort_feasible=False.

* The comfort band follows DSO+T: the slider scales range_*_limit, and the cooling and heating bands are kept from overlapping. The deadband is only used for thermostat cycling in the physics stub. Make sure the preference-curve script doesn't apply the slider again.

* Heat pump COP deliberately differs from DSO+T. I use the actual outdoor temperature below 80°F. DSO+T holds its COP curve at the 80°F value for every colder temperature, so its heat pump COP never changes with weather.

#### What I verified and found
* Parity with DSO+T. UA, CA, CM, HM, the solar factor and both design capacities match the original HVACDSOT exactly for gas, heat pump and resistance heating. The test pins those values.
dsot/hvac_agent.py can't be imported at all. obj_rule is annotated with ConcreteModel, which the file never imports (line 2430). I worked around it only in a throwaway script to get the reference numbers.
* The existing curve_and_agent/gridlabd_interface.py has the problems I suspected. I confirmed them with gridlabd --modhelp, and the new observer avoids all three:
hvac_load is already in kW, so the /1000 there is wrong.
power_state is only ON/OFF, so the mode it derives is always "off". system_mode is the right property.
* The capacitance and conductance properties are actually named air_heat_capacity, mass_heat_capacity, mass_heat_coeff and UA, so its reads always fall back to defaults.



