Using Constance in TESP simulations for the first time. Using you favorite ssh or scp app to login in constance to connect. 
For instance using a terminal and connect something like this
	
	>ssh d3j331@constance

After you have logged in. Will we need to load some modules

	>module load sbank/1.2
	>module load python/anaconda3.6

Download TESP and tesp_support

	>mkdir grid
	>cd grid
	>mkdir repository
	>cd repository
	>git config --global user.name "your user name"
	>git config --global user.email "your email"
	>git clone -b master https://github.com/pnnl/tesp.git
	>pip intall --upgrade --user pip
	>pip install tesp_support --user

Make script directory for run the simulations

	>cd
	>mkdir scripts
	>cd scripts

Make the 'environment' script using emacs/vi. The export 'runLocation' and 'experimentName' is where the $runLocation/$experimentName files are zipped, the directory must be empty when case the is run. The INSTDIR is the was built by Mitch Pelton(d3j331) and used with out you having to build your own.

	#Running
	export REPO_DIR=$HOME/grid/repository
	export INSTDIR=/people/d3j331/grid/installed

	export FNCS_INCLUDE_DIR=$INSTDIR/include
	export FNCS_LIBRARY=$INSTDIR/lib

	export PATH=$INSTDIR/bin:$HOME/.local/bin:$PATH
	export GLPATH=$INSTDIR/lib/gridlabd:$INSTDIR/share/gridlabd
	export LD_LIBRARY_PATH=$INSTDIR/lib:$LD_LIBRARY_PATH
	export TESPDIR=$REPO_DIR/tesp

	export FNCS_FATAL=yes
	export FNCS_LOG_STDOUT=yes
	export FNCS_LOG_LEVEL=DEBUG1
	export FNCS_LAUNCHER_LOG_LEVEL=INFO

	export experimentName=case_8m
	export runLocation=$TESPDIR/ercot

Make the 'tesp_laucher.cfg' file. This is a sample your will need to replace 'd3j331' for your login id somel like 'mcde601'.  For each line is seperate process in the launcher, one per core. There can not be any extra lines in the file. Line args as stated

[path]:		/people/d3j331/grid/repository/tesp/ercot/case8 -> The first is the path is the for the file in your case. 
[config]:	FNCS_LOG_LEVEL=WARNING -> Configure paramaters, multiples can defined seperated by space
'nice':		Affects process scheduling.
[value]:	-5 -> Niceness values range from -20 (most favorable to the process) to 19 (least favorable to the process). 
[process]:	gridlabd -> Process to execute
[parameter]:	-D USE_FNCS Bus1.glm -> The remainer of the parmeters are for the executble, seperated by spaces, '=' cannot be used

Example .cfg file

	/people/d3j331/grid/repository/tesp/ercot/case8 FNCS_LOG_LEVEL=WARNING nice -5 gridlabd -D USE_FNCS Bus1.glm
	/people/d3j331/grid/repository/tesp/ercot/case8 FNCS_LOG_LEVEL=WARNING nice -5 gridlabd -D USE_FNCS Bus2.glm
	/people/d3j331/grid/repository/tesp/ercot/case8 FNCS_LOG_LEVEL=WARNING nice -5 gridlabd -D USE_FNCS Bus3.glm
	/people/d3j331/grid/repository/tesp/ercot/case8 FNCS_LOG_LEVEL=WARNING nice -5 gridlabd -D USE_FNCS Bus4.glm
	/people/d3j331/grid/repository/tesp/ercot/case8 FNCS_LOG_LEVEL=WARNING nice -5 gridlabd -D USE_FNCS Bus5.glm
	/people/d3j331/grid/repository/tesp/ercot/case8 FNCS_LOG_LEVEL=WARNING nice -5 gridlabd -D USE_FNCS Bus6.glm
	/people/d3j331/grid/repository/tesp/ercot/case8 FNCS_LOG_LEVEL=WARNING nice -5 gridlabd -D USE_FNCS Bus7.glm
	/people/d3j331/grid/repository/tesp/ercot/case8 FNCS_LOG_LEVEL=WARNING nice -5 gridlabd -D USE_FNCS Bus8.glm
	/people/d3j331/grid/repository/tesp/ercot/case8 FNCS_LOG_LEVEL=WARNING FNCS_CONFIG_FILE=pypower8.yaml FNCS_LOG_STDOUT=yes nice -5 python fncsERCOT.py


Make slurm batch file called 'tesp_sbatch.sh'. This is a sample your will need to replace 'd3j331' for your login id somel like 'mcde601'.

	#!/bin/csh

	# Account Name
	#SBATCH -A TESP 
	# time_limit
	# 180 min or less for short partition
	#SBATCH -t 180
	# number_of_nodes
	#SBATCH -N 1
	# number_of_cores
	#SBATCH -n 24
	# job_name
	#SBATCH -J ercot
	# job_output_filename(stdout)
	#SBATCH -o ercot.out
	# job_errors_filename(stderr)
	#SBATCH -e ercot.err


	#First make sure the module commands are available.
	#. /etc/profile.d/modules.csh 

	#Set up your environment you wish to run in with module commands.
	module purge
	module load use.own
	module load gcc/6.1.0
	module load python/anaconda3.6
	module load openmpi/3.0.1

	#Next unlimit system resources, and set any other environment variables you need.
	unlimit

	#Is extremely useful to record the modules you have loaded, your limit settings, 
	#your current environment variables and the dynamically load libraries that your executable 
	#is linked against in your job output file.
	echo
	echo "== Loaded Modules"
	module list >& _modules.lis_
	cat _modules.lis_
	/bin/rm -f _modules.lis_

	echo
	echo "== Limits"
	limit

	echo
	echo "== Environment Variables"
	printenv

	echo
	echo "== Host List"
	hostlist -e $SLURM_NODELIST         
	echo

	echo "== Running experiment on each node"
	echo 

	mpirun --map-by node:PE=24 -n $SLURM_NNODES -mca orte_abort_on_non_zero_status 0 fncs_launcher /people/d3j331/scripts/tesp_launcher.cfg $runLocation/$experimentName

	echo
	echo "== All Done!"


If everthing is correct and the gods are smiling then at command line type

	>. environment
less than 3 hour time limit
	>sbatch -p short tesp_batch.sh
or more than 3 hour
	>sbatch tesp_batch.sh
	>squeue -u d3j331

If the squeue is empty the job is done. If no output is in the $runLocation/$experimentName you can look out the ercot.err and ercot.out files in the 'scripts' directory. If you want to do multiple runs the job/err/out files are defined in the tesp_sbatch.sh file. 

	# job_name
	#SBATCH -J ercot
	# job_output_filename(stdout)
	#SBATCH -o ercot.out
	# job_errors_filename(stderr)
	#SBATCH -e ercot.err

Other commands
>sbank balance statement -N -a tesp



