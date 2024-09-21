# Getting Started

This Getting_Started.md file was written as a quick-start guide to using TESP, specifically for DSOT.

## What you will need (as a windows user)

- mobaxterm: https://mobaxterm.mobatek.net/
	- Download and install
- vscode (code): 
	- From the command line in mobaxterm: 
		- `sudo apt install snapd`
		- `sudo snap install --classic code`
	- To launch: `code`
	- To kill sessions: `killall code`
- An ssh session of mobaxterm into one of the following computing resources:
	- Boomer, gage, graham-sim, maxwell, tapteal-ubu
		- Note that you need to request access individually.
		- Session -> new session -> user@boomer.pnl.gov
        - Enter pnnl password

## Set up an environment and install TESP

The TESP Read The Docs page walks through this process: https://tesp.readthedocs.io/en/latest/Installing_Building_TESP.html

When you've successfully completed this step, you should be able to activate the environment from your home dierctory. Remember to activate your environment before attempting to run anything within TESP. Activate environment: `source tesp`


## Where you will be working:

TESP\examples\analysis\dsot\code
- 8_hi_system_case_config.json
- generate_case.py
- prepare_case_dsot.py

These are the main files to edit in order to generate new runs. Note that TESP expects python3, so any python scripts are run like: 

`python3 prepare_case_dsot.py`

The main files behind tesp, running the market, the agents, the substations, are located within TESP/src/tesp_support/tesp_support/dsot

## Before starting any runs, get necessary data:

Start by downloading supporting data that is not stored in the repository due to its size and static nature. This will add a “data” folder alongside the existing “code” folder from the repository. 

`cd tesp/repository/tesp/examples/analysis/dsot/code`

`./dsotData.sh`

## Prepare a run

Edit the following files to setup your case:
- 8_hi_system_case_config.json
  - Market
  - Start Time
  - End Time
  - Tmax (this is the alloted time based on your simulation window. Existing definitions stored based on number of days, e.g., 7Tmax for 7 days)

- generate_case.py (For generating a year's worth of runs, one month at a time)
  - Looks at prepare_case_dsot.py for most of its config

- prepare_case_dsot.py (For generating a run of duration set in 8_hi_system_case_config.json)
  - RECS_data = True
  - Set agent flags, pv, bt, ev, and fl to 1 or 0
  - Select whether to use 8 or 200 node test case

`python3 prepare_case_dsot.py`

## Shell scripts to navigate runs (execute within the generated run folder):

Preferable to execute these from the terminal in mobaxterm rather than VSCode, as sometimes they don't queue correctly.	
- ./run.sh --> runs a run
- ./kill.sh --> kills a run
- ./clean.sh --> cleans up run files if you need to restart a killed run

## Check on status of runs for any errors. From mobaxterm command line:

- Check for errors (from the run folder):
	- `cat *.log | grep -i err`
	- `cat */*.log | grep -i err` 

- Check processes with `htop`. If very little computing power is being used, likely no runs are active. This also shows each process. Can be sorted by user, time, CPU%, etc.

- Check what is running `ps -a`. Used to make sure tesp install is successful. Occasionally gridlabd may not install correctly. If it is not listed after you've executed a run, it didn't install correctly.

- Refresh file directory and check size of opf.csv and pf.csv (within run directory). These should be growing in size as things are written.

- After run is completed, check tso.log (within run directory) for any errors. Scroll to bottom to see that it finished successfully or exited with an error. 

## Run postprocessing on a successful run:

`python3 ../run_case_postprocessing.py > postprocessing.log&`

## Move run files over to a sharefolder:

1. Navigate to folder one directory above the run folder you'd like to move
2. `sudo mount -t cifs //pnnlfs09.pnl.gov/sharedata37_op$/DSOT  /mnt/dsot -o username=[USER]`
3. `sudo cp -r [run_folder] /mnt/dsot/run_outputs/Rates_Scenario/.`

*Note instructions will change based on mount location, folder, and target directory.*

If choosing to delete run folders to clear up room, do so from the mobaxterm terminal rather than VSCode to ensure they are cleared from the disk.

## Troubleshooting Runs
- Prepare case or generate case fails: 
  - Did you update RECS parameters? If so, remember to re-run recs_gld_house_parameters.py.
- Address already in use:
  - Are you already running something? Make sure it's finished. I.e., don't try to postprocess and run something new at the same time.
- Infeasible solution/ No RT starting point:
  - genPowerLevel needs to be adjusted in 8_hi_system_case_config.json
    - Defines the initial power output for generators when running the very first timestep. This allows them to be put in such a state that, when respecting ramp rates, they can reach a reasonable dispatch.
    - 0.6 - 0.7 usually works, for high-demand months, might need to go up to 0.85.
