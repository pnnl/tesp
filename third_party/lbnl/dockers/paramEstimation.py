#########################
# PYTHON DEPENDENCIES
# jinja2
# 1. Run pip install -r requirements.txt to install dependencies
# 2. Run python paramEstimation.py to run the parameter estimation

# This script automates the process of creating docker images which are needed
# for paremeter estimation, and estimating parameters for RC models using EnergyPlus.
# This script requires a JModelica installation image
# with the name michaelwetter/ubuntu-1604_jmodelica_trunk_2.
# If the image doesn't exist, then the user must
# enable the compilation of JModelica by setting BUILD_JMODELICA to True
# The script runs a parameter estimation case and writes the results
# in the Estimation folder directory. The output folder's format is
# name_model_run + "_" + name_of_IDF used for the parameter estimation
# An image will be generated which shows how well the comparison between RC and detailed
# model was.
### IMPORTANT:
# EDIT workflow which is in Estimation/develop/w_energyplus to specify
# the number of RCs as well as any paths which are needed for the estimation
import os
import subprocess as sp
import jinja2 as jja2
import shutil
import sys

#############################
# This script uses a version of E+ which should be compatible with the IDF used for the detailed model.
# To create the EnergyPlus image which will run the IDF file, the user needs to provide following information.
# ENERGYPLUS_VERSION 8.9.0 (Version of EnergyPlus to be used with Emulator model)
# ENERGYPLUS_TAG v8.9.0 (Tags of EnergyPlus to be used with Emulator model)
# ENERGYPLUS_SHA 40101eaafd (SHA to be seen at in the link to download the release as can be seen below)
# https://github.com/NREL/EnergyPlus/releases/download/v8.9.0/EnergyPlus-8.9.0-40101eaafd-Linux-x86_64.sh
ep_vers="8.9.0"
ep_tag="v8.9.0"
ep_sha="40101eaafd"

# Enable or disabled the compilation of JModelica
BUILD_JMODELICA=True

# Enable or disabled the compilation of Estimator
BUILD_ESTIMATOR=True

def print_output(process):
    '''s
    This function prints the output of
    subprocess on the stdout.
    '''
    while True:
        nextline = process.stdout.readline()
        if nextline == '' and process.poll() is not None:
            break
        sys.stdout.write(nextline)
        sys.stdout.flush()

    output = process.communicate()[0]
    exitCode = process.returncode

# Get the script path
script_path=os.path.dirname(os.path.realpath(__file__))

jmodelica_path=os.path.join(script_path, 'JModelica')
estimation_path=os.path.join(script_path, 'Estimation')

# INSTALL ubuntu-1604_jmodelica_trunk if it image doesn't exist
cmd = ['make', 'build']
if BUILD_JMODELICA:
    os.chdir(jmodelica_path)

    process = sp.Popen(cmd, stdout=sp.PIPE)
    print_output(process)
    print("Building JModelica image is completed")

# Install estimation_master if image doesn't exist
if BUILD_ESTIMATOR:
    template_path=os.path.join(estimation_path, 'Dockerfile.template')
    loader = jja2.FileSystemLoader(template_path)
    env = jja2.Environment(loader=loader)
    template = env.get_template('')

    output_res=template.render(ep_vers=ep_vers, ep_tag=ep_tag,
      ep_sha=ep_sha, ep_versm=ep_vers.replace('.', '-'))
    output_file = 'Dockerfile' + '.output'
    with open(output_file, 'w') as fh:
        fh.write(output_res)
    fh.close()

    # Copy Dockerfile to be used to create the containers
    shutil.move(output_file, os.path.join(estimation_path, 'Dockerfile'))

    os.chdir(estimation_path)
    process = sp.Popen(cmd, stdout=sp.PIPE)
    print_output(process)
    print("Building Estimator image is completed")

os.chdir(estimation_path)

# Get the path to script which runs the container
runConPat=os.path.join(estimation_path, "runContainer.sh")

# Command to run the container
cmd = ["sh", runConPat]
# /bin/bash -c && cd /mnt/shared && python /mnt/shared/develop/w_energyplus/workflow.py"
print_output(process = sp.Popen(cmd, stdout=sp.PIPE))
print("Parameter estimation is completed")
