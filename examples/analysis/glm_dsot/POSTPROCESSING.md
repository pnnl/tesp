# glm_dsot Post-Processing Workflow

This guide follows the **How to run Post-Processing** section of the [glm_dsot README](README.md), and expands it using the checked-in scripts and the sample results under `examples/analysis/dsot/code/post_processing`. The archived dsot results are visual examples; they are not inputs to the glm_dsot scripts and may have been produced with different runs or configurations.

## Workflow At A Glance

Post-processing has two required stages and one optional review stage:

1. Run [run_case_postprocessing.py](code/run_case_postprocessing.py) once for each completed monthly simulation. It reads raw monthly GridLAB-D, agent, and AMES outputs and writes monthly meter, comfort, profile, and plot products.
2. Run [run_annual_postprocessing.py](code/run_annual_postprocessing.py) after the monthly outputs for a case are complete. It combines the twelve months, calculates annual load and market statistics, and regenerates bills and cash-flow summaries.
3. Optionally run and configure the comparison helpers in [case_comparison_plots.py](../../../src/tesp_support/tesp_support/dsot/case_comparison_plots.py) to compare cases and prepare review plots. This is not called automatically by either post-processing script.

```text
completed monthly simulation
  -> run_case_postprocessing.py (per month)
       -> monthly meter / amenity / profile data and plots
  -> repeat for the other 11 months
  -> run_annual_postprocessing.py (per annual case)
       -> annual aggregates / market purchases / bills / cash flows
  -> optional case_comparison_plots.py
       -> cross-case plots and comparison summaries
```

Install `tesp_support` in the Python environment used for the run (`pip install -e src/tesp_support` from the repository root, or follow the README's equivalent navigation), install the requirements, and set `TESPDIR` to the repository's top-level `tesp` directory. The scripts also require the shared data files under `examples/analysis/dsot/data`; glm_dsot deliberately reuses this metadata.

## 1. Monthly Post-Processing

### Where and how to run it

The monthly script reads `generate_case_config.json` from the **current working directory**. Run it from the completed monthly case folder, not from the script's directory. For example, in a Windows terminal:

```powershell
python ..\run_case_postprocessing.py
```

From a Bash-style terminal, the equivalent is:

```bash
python3 ../run_case_postprocessing.py > postprocessing.log 2>&1
```

The script calls `post_process()` at module level, so executing the file starts the work immediately. Its configured `case_path` is built from the script directory and the `caseName` in the current folder's `generate_case_config.json`. Keep the working directory and generated case configuration consistent.

### Required monthly inputs

The simulation must have completed far enough to provide the outputs that the selected jobs read. In particular:

- `generate_case_config.json`, including `StartTime`, `EndTime`, `caseName`, `data_path`, the population metadata filename, and references to the industrial and renewable data.
- Active-DSO population metadata, plus the shared commercial metadata and any rate data used by the configured scenario. The script resolves these using `data_path` and the population filename in the case configuration.
- `DSO_<N>/Substation_<N>_agent_dict.json` and the per-DSO retail-agent output (including `retail_site` data) for participation and market information.
- `Substation_<N>/Substation_<N>_glm_dict.json` and GridLAB-D HDF5 outputs for billing meters, houses, and other monitored objects.
- AMES / TSO output needed for generation, market, and forecast plots; reference industrial-load data; and, where used, weather data.

The monthly runner chooses active DSOs from the population metadata (`used == true`). The current defaults analyze simulation days beginning at day 4 and discard one trailing day. These are run-in/incomplete-day guards, not calendar-day numbers; the derived `day_range` controls meter, amenity, profile, and plot reads.

### Function order and products

The runner first builds a job list and executes it with Joblib (`n_jobs=-1`, `loky`). Jobs are parallel, so their individual completion order is not fixed. The month-level aggregation below runs after the parallel jobs finish.

| Work | Main calls | What it does / typical products |
| --- | --- | --- |
| Per-DSO customer and meter work | Local `DSO_specific_cost()` -> `pt.load_json()` -> `pt.customer_meta_data()` -> `pt.load_retail_data()` -> `rm.read_meters()` -> `pt.amenity_loss()` | Loads GLM and agent dictionaries; classifies meters as residential, commercial, or industrial; adds customer participation metadata; reads retail-agent data and daily meter data; computes monthly meter energy and transactive totals; calculates HVAC/water-heater comfort impacts. Writes `energy_metrics_data.h5` (`energy_data`, `energy_sums`) and `transactive_metrics_data.h5` (`trans_data`) under `Substation_<N>`, along with monthly billing data and amenity outputs. |
| DER load stacks | Local `DSO_der_loads()` -> `pt.der_load_stack()` | Reads the per-DSO GLD / DER monitoring data and creates DSO-level DER load-stack data used by the aggregate plot. |
| Building load stacks | Local `DSO_bldg_loads()` -> `pt.bldg_load_stack()` | Aggregates building loads by customer/building class and creates the building-load stack data. |
| Daily market plots | Local `Daily_market_plot()` -> `pt.dso_market_plot()` for every day in `day_range` | Compares DSO quantities and prices with AMES, substation, industrial, and reference-load data. Writes daily market figures under the case's `plots/` directory. |
| Baseline-demand profiles | Local `determine_baseline_demand_profiles()` -> `rm.create_demand_profiles_for_each_meter()` -> `rm.create_baseline_demand_profiles_for_each_meter()` | Builds hourly demand per meter and weekday/weekend baseline profiles when `rate_scenario` is  `Flat` or `TOU`. These are used by workflows requiring a baseline demand reference. |
| Demand profiles | Local `determine_demand_profiles()` -> `rm.create_demand_profiles_for_each_meter()` | Builds and saves hourly per-meter demand profiles when `rate_scenario` is `""`, `"RND"`, or `"EandC"`. |
| Population statistics | `pt.RCI_analysis()` | Produces the monthly residential/commercial/industrial population and, in this call, sets `bill=False`. |
| Bulk generation and system plots | `pt.generation_load_profiles()` twice; `pt.generation_statistics()` twice | Creates generation/load plots (with and without ERCOT fuel-mix data) and AMES / PyPower generation statistics. |
| Aggregate DER and building plots | `pt.der_stack_plot()`; `pt.bldg_stack_plot()` | Combines the DSO stack data into case-wide plots and data files. |
| Forecast statistics | `pt.dso_forecast_stats()` | Compares DSO quantity and price forecasts with actual market/load series; writes forecast CSVs, including `DA_Q_forecast.csv` and `DA_Q_error.csv`, plus error plots. These DA-Q files can feed annual calibration. |

The job toggles near the top of `post_process()` are all enabled in the checked-in script. The baseline-demand and demand-profile jobs are additionally gated by `rate_scenario`; the corresponding toggle can be enabled without the job being scheduled if the scenario string does not match the conditions above.

### Monthly outputs to check

The most useful hand-off products are:

- `Substation_<N>/energy_metrics_data.h5` and `transactive_metrics_data.h5`: read by annual energy aggregation.
- `Substation_<N>/Substation_<N>_glm_dict.json`: billing-meter/building metadata read by monthly and annual analysis.
- Monthly bill HDF5/CSV products, including `bill_dso_<N>_data.h5`, `cust_bill_dso_<N>_data.csv`, and `billsum_dso_<N>_data.csv` (the meter/billing helpers write these as applicable).
- `DER_profiles.h5`, `Building_profiles.h5`, and forecast / market CSVs used for annual aggregation and plots.
- `plots/` with DSO market, generation/load, forecast, DER-stack, and building-stack figures.

Before proceeding, check that the expected files exist for every active DSO and that the run completed successfully. A partial simulation can leave missing daily HDF5 keys; some helpers skip incomplete days, which can otherwise make a later annual result look merely shorter rather than obviously failed.

## 2. Annual Post-Processing

### Inputs and folder layout

Complete monthly simulations and monthly post-processing for all twelve months of each scenario first. The annual script also expects an annual output folder for each case and the shared configuration/metadata below:

- `glm_dsot/data/rates_config.json5` and the selected system config, currently `8_hi_system_config.json5` (`nodes = 8`, `scenario = "hi"` in the script).
- Shared DSO population and commercial metadata under `examples/analysis/dsot/data`.
- Annual output folders under the configured `datapath`, currently `glm_dsot/data/post_processing/{Flat,DSOT,TOU,rob-don,sub}`.
- The twelve monthly case directories named by the script's `month_def` lists, each with `generate_case_config.json` and the monthly products described above.

The script has case-specific naming assumptions. In the checked-in version, Flat monthly folders are looked up beside the annual script under `glm_dsot/code/`; TOU uses `8_2016_<MM>_pv_bt_fl_ev`; other non-Flat/non-TOU cases use `8_rnd_2016_<MM>_pv_bt_fl_ev`. March and April TOU use shifted analysis-day ranges. Confirm these paths and names against the actual run folders before starting.

### Entry points: important current behavior

The annual file supports three wrappers:

- `one_process(case_path)`: processes one annual case (and uses that case as the demand reference if it is Flat; otherwise it uses TOU).
- `batch_process()`: processes Flat plus the `case_list` entries (DSOT, TOU, transactive / `rob-don`, and subscription / `sub`); TOU is the demand reference.
- `base_params_process()`: runs Flat and forces integrated Q-bid calibration on.

At the bottom of the checked-in file, **`base_params_process()` is the active call**. The comments mention changing this call, but running the file unchanged does not invoke `one_process()` or `batch_process()`. To run another workflow, edit/select the corresponding active call and verify the case paths first. `TESPDIR` must resolve to the repository root.

### Annual function order

For every case, `run_annual_postprocessing()` schedules the case twice: pass 1 builds missing annual aggregates, then pass 2 reruns financial reconciliation. The annual energy, amenity, load-statistic, LMP-statistic, generator-statistic, and quadratic-curve steps are guarded by output-file existence checks. Retail, customer CFS, and DSO CFS are deliberately recalculated on both passes. Wholesale purchases are recalculated if any active DSO's market-purchase JSON is missing.

1. **Resolve case metadata and months.** Read the rates config and system config; load the RECS DSO population file; build `dso_range` from active nodes; select the month folder list and analysis window; read each month's `generate_case_config.json` for start/end times. The first month's GLM dictionary is then used for annual meter and amenity aggregation.
2. **Annual meter energy and amenity, per DSO.** `rm.annual_energy()` combines monthly meter-energy and transactive HDF5 files into `energy_dso_<N>_data.h5` and `transactive_dso_<N>_data.h5`. `pt.annual_amenity()` combines monthly comfort metrics into `amenity_dso_<N>_data.h5` and `.csv`.
3. **Annual load and peak statistics.** `pt.dso_load_stats()` combines `DER_profiles.h5` and `Building_profiles.h5` with the monthly timing and reference-load data. It writes `DSO_Total_Loads.csv`, `DSO_load_stats.csv`, and `Qmax.csv` (peak demand and peak time by DSO / system).
4. **Annual LMP/load and generator analysis.** When the annual LMP stats file is absent, `pt.dso_lmp_stats()` combines monthly AMES data, writes annual RT/DA LMP and load series (`Annual_RT_LMP_Load_data.csv`, `Annual_DA_LMP_Load_data.csv`), `opf.csv`, and annual LMP-stat CSVs; the runner calls `pt.plot_lmp_stats()` for each DSO. `pt.generation_statistics()` writes `generator_statistics_AMES.csv` when that output is missing.
5. **Optional integrated Q-bid calibration.** When enabled, `_ensure_annual_da_q_inputs()` combines monthly `DA_Q_forecast.csv` and `DA_Q_error.csv`; `_build_annual_weather_files()` can combine each DSO's monthly `weather.dat`; `reconstruct_actual_da_quantities()` writes `actual_da_q.csv`; then `calibrate_q_bid_forecast_correction()` fits DSO correction coefficients and writes `Q_bid_forecast_correction_calibrated.json`. If auto-merge is enabled, `merge_calibration_into_config()` writes a calibrated config and diff report in the annual case folder. Missing calibration inputs or calibration errors are reported and caught by this optional block.
6. **Fit quadratic price/quantity curves.** If `DSO_quadratic_curves.json` is missing, `qc.DSO_LMPs_vs_Q()` fits the annual LMP-versus-quantity relationship and writes the curves.
7. **Calculate wholesale purchases.** If needed, `ep.Wh_Energy_Purchases()` uses annual market/load results and `Qmax.csv` to write `DSO<N>_Market_Purchases.json` per active DSO.
8. **Recalculate retail bills and revenue.** For each DSO, read its GLM and agent dictionaries; classify each billing meter; join customer participation data with `pt.customer_meta_data()`; then call `rm.DSO_rate_making()`. The call produces DSO cash flows, revenues/energy sales, tariff/bill data, and a revenue-surplus error. The script writes per-DSO JSONs and a sample customer's bill JSON.
9. **Build customer and DSO cash-flow summaries.** `hf.get_customer_df()` builds `Master_Customer_Dataframe.h5/.csv`; `hf.get_mean_for_diff_groups()` creates `Customer_CFS_Summary.csv`; `hf.get_DSO_df()` creates `DSO_CFS_Summary.csv` and per-DSO capital-cost and expense JSONs.
10. **Run population and metadata products.** Each pass calls `pt.RCI_analysis()` and `pt.metadata_dist_plots()` for the configured residential and commercial attributes, writing RCI/population data and histograms.

The output existence checks currently use `energy_dso_8_data.h5` and `amenity_dso_8_data.h5` as the energy/amenity sentinels, even though the aggregation is per DSO. If you are processing a different topology or repairing a partially populated output tree, inspect all active-DSO files rather than relying only on those sentinel checks.

### Annual outputs

Expect annual case folders to contain some or all of the following (which steps run depends on existing files and enabled settings):

- Energy / comfort: `energy_dso_<N>_data.h5`, `transactive_dso_<N>_data.h5`, `amenity_dso_<N>_data.h5`, `amenity_dso_<N>_data.csv`.
- System / market: `DSO_Total_Loads.csv`, `DSO_load_stats.csv`, `Qmax.csv`, `Annual_DA_LMP_Load_data.csv`, `Annual_RT_LMP_Load_data.csv`, `Annual_DA_LMP_stats.csv`, `Annual_RT_LMP_stats.csv`, `opf.csv`, `generator_statistics_AMES.csv`, `DSO_quadratic_curves.json`.
- Billing / finance: `DSO<N>_Market_Purchases.json`, `DSO<N>_Cash_Flows.json`, `DSO<N>_Revenues_and_Energy_Sales.json`, customer bill and metadata JSONs, `Master_Customer_Dataframe.h5/.csv`, `Customer_CFS_Summary.csv`, `DSO_CFS_Summary.csv`, and per-DSO capital-cost / expense JSONs.
- Calibration, when enabled: annualized DA-Q inputs, `actual_da_q.csv`, `annual_weather/weather_dso_<N>.csv`, `Q_bid_forecast_correction_calibrated.json`, `rates_config_calibrated.json5`, and `rates_config_calibration_diff_report.json`.

In the current checked-in configuration, `integrate_q_bid_calibration = True`, `qbid_auto_discover_weather_dat = True`, and `qbid_auto_merge_to_new_config = True`. Thus the active `base_params_process()` attempts calibration and writes a **new** calibrated config (it does not overwrite `rates_config.json5`). Set the switches deliberately if this is not part of the intended run.

## 3. Optional Case Comparison And Reporting

The README also describes case-comparison plots and tables. These are review products, not a prerequisite for the annual aggregation. The helper [case_comparison_plots.py](../../../src/tesp_support/tesp_support/dsot/case_comparison_plots.py) has a `rates_plots()` driver that, in order:

1. Makes selected August DER load-stack plots for Flat, TOU, and DSOT.
2. Calls `plot_annual_stats()` for DA LMP, total load, and the hybrid load/LMP view.
3. Calls `pt.generation_load_profiles()` for the baseline case.
4. Calls `dso_cfs_delta()` to compare DSO cost/benefit components, including waterfall and benefit plots.
5. Calls `customer_cfs_delta()` to compare customer bills, energy use, and savings, and writes `Customer_pop_stats.csv` plus customer-population plots.

The checked-in `rates_plots()` paths point to `examples/analysis/dsot/data/post_processing`, not glm_dsot's `data/post_processing`. Before using it for glm_dsot, configure its paths, case names, metadata, selected days, and comparison pairs for the glm_dsot results. Its `__main__` block runs `rates_plots()` when the module is executed directly.

The archived figures below show representative outputs from the sibling dsot post-processing tree. They are useful for recognizing plot types; they are not expected outputs from every glm_dsot run.

### Annual system-load comparison

This two-panel figure compares monthly total-load distributions and daily load variation by scenario. It is produced by the annual comparison helper, not by the monthly simulation itself.

![Annual total system load and daily variation by case](../dsot/code/post_processing/plots/20250615Case_Compare_Total_Load%20_Annual_Box_Plots-focused-SBS.png)

### DSO cost-and-benefit waterfall

This figure summarizes the annual DSO impact categories, including capacity payments, energy purchases, distribution hardware, operations, software, workspace, and customer asset investments.

![DSO annual cash-flow impact waterfall](../dsot/code/post_processing/DSOT/plots/20250615DSO_CFS_Waterfall.png)

### Customer bill-savings distribution

This customer comparison plot groups annual bill savings by participation status. The companion `dist` image is a normalized histogram; other generated plots group by tariff class, building type, heating, income, DSO, or DER participation.

![Annual customer bill savings by participation](../dsot/code/post_processing/DSOT/plots/20250615Customer_PDF_cust_participating_bill_savings_pctdist.png)

## Validation Checklist

- Confirm every monthly case has `generate_case_config.json`, expected per-DSO HDF5/JSON inputs, and completed simulation logs before running post-processing.
- Confirm all twelve month paths and naming patterns in `month_def` resolve; check the special TOU March/April ranges.
- Confirm monthly hand-off products exist for all active DSOs, especially `energy_metrics_data.h5`, `transactive_metrics_data.h5`, `DER_profiles.h5`, and `Building_profiles.h5`.
- Confirm annual output and metadata paths match the current script (`post_processing` with underscore, shared metadata under `analysis/dsot/data`).
- After annual processing, compare customer populations and date windows across cases; check that DSO revenues, expenses, and capital costs reconcile in the generated cash-flow summaries.
- If calibration is enabled, inspect the calibration JSON, diagnostics, and diff report before using the calibrated config in another run.

For common run failures, check that `TESPDIR` resolves, `tesp_support` is installed in the active environment, generated monthly folders match `month_def`, and all monthly outputs are complete. A failed simulation can cause post-processing to skip incomplete days or fail later when annual aggregation expects those inputs.