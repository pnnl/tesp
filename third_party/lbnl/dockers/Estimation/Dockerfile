FROM ubuntu-1604_jmodelica_trunk

######################
# EnergyPlus Docker
######################

USER root

MAINTAINER xxx

# This is not ideal. The tarballs are not named nicely and EnergyPlus versioning is strange
ENV ENERGYPLUS_VERSION 8.9.0
ENV ENERGYPLUS_TAG v8.9.0
ENV ENERGYPLUS_SHA 40101eaafd

# This should be x.y.z, but EnergyPlus convention is x-y-z
ENV ENERGYPLUS_INSTALL_VERSION 8-9-0

# Downloading from Github
# e.g. https://github.com/NREL/EnergyPlus/releases/download/v8.9.0/EnergyPlus-8.9.0-40101eaafd-Linux-x86_64.sh
ENV ENERGYPLUS_DOWNLOAD_BASE_URL https://github.com/NREL/EnergyPlus/releases/download/$ENERGYPLUS_TAG
ENV ENERGYPLUS_DOWNLOAD_FILENAME EnergyPlus-$ENERGYPLUS_VERSION-$ENERGYPLUS_SHA-Linux-x86_64.sh
ENV ENERGYPLUS_DOWNLOAD_URL $ENERGYPLUS_DOWNLOAD_BASE_URL/$ENERGYPLUS_DOWNLOAD_FILENAME


# Collapse the update of packages, download and installation into one command
# to make the container smaller & remove a bunch of the auxiliary apps/files
# that are not needed in the container

RUN apt-get update && apt-get install -y ca-certificates curl \
    && rm -rf /var/lib/apt/lists/* \
    && curl -SLO $ENERGYPLUS_DOWNLOAD_URL \
    && chmod +x $ENERGYPLUS_DOWNLOAD_FILENAME \
    && echo "y\r" | ./$ENERGYPLUS_DOWNLOAD_FILENAME \
    && rm $ENERGYPLUS_DOWNLOAD_FILENAME \
    && cd /usr/local/EnergyPlus-$ENERGYPLUS_INSTALL_VERSION \
    && rm -rf DataSets Documentation ExampleFiles WeatherData MacroDataSets PostProcess/convertESOMTRpgm \
    PostProcess/EP-Compare PreProcess/FMUParser PreProcess/ParametricPreProcessor PreProcess/IDFVersionUpdater

# Remove the broken symlinks
RUN cd /usr/local/bin \
    && find -L . -type l -delete

# Add in the test files
#ADD test /usr/local/EnergyPlus-$ENERGYPLUS_INSTALL_VERSION/test_run
#RUN cp /usr/local/EnergyPlus-$ENERGYPLUS_INSTALL_VERSION/Energy+.idd \
#        /usr/local/EnergyPlus-$ENERGYPLUS_INSTALL_VERSION/test_run/

# Add a symbolink to Energy+.idd
RUN ["ln", "-s", "/usr/local/EnergyPlus-8-9-0/Energy+.idd", "/usr/local/Energy+.idd"]

VOLUME /var/simdata
WORKDIR /var/simdata


CMD [ "/bin/bash" ]

######################
# MPCPy Docker
######################
ENV ROOT_DIR /usr/local

USER root

RUN apt-get update && apt-get install -y \
	libgeos-dev \
	git

USER developer
WORKDIR $HOME

RUN pip install --user \
	pandas==0.20.3 \
	python-dateutil==2.6.1 \
	pytz==2017.2 \
	scikit-learn==0.18.2 \
	sphinx==1.6.3 \
	numpydoc==0.7.0 \
	tzwhere==2.3

RUN mkdir git && cd git && \
    mkdir mpcpy && cd mpcpy && git clone https://github.com/lbl-srg/MPCPy && cd .. && \
    mkdir estimationpy-ka && cd estimationpy-ka && git clone https://github.com/krzysztofarendt/EstimationPy-KA && cd .. && \
    mkdir buildings && cd buildings && git clone https://github.com/lbl-srg/modelica-buildings.git

WORKDIR $ROOT_DIR

ENV JMODELICA_HOME $ROOT_DIR/JModelica
ENV IPOPT_HOME $ROOT_DIR/Ipopt-3.12.4
ENV SUNDIALS_HOME $JMODELICA_HOME/ThirdParty/Sundials
ENV SEPARATE_PROCESS_JVM /usr/lib/jvm/java-8-openjdk-amd64/
ENV JAVA_HOME /usr/lib/jvm/java-8-openjdk-amd64/
ENV PYTHONPATH $PYTHONPATH:$HOME/git/estimationpy-ka/EstimationPy-KA:$HOME/git/mpcpy/MPCPy:$JMODELICA_HOME/Python:$JMODELICA_HOME/Python/pymodelica
ENV MODELICAPATH $MODELICAPATH:$HOME/git/buildings/modelica-buildings

######################
# Estimation Docker
######################

USER root

RUN apt-get update && apt-get install -y \
	libgeos-dev \
	git

RUN pip install gitpython

#WORKDIR $HOME