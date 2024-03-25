# Build runtime image
FROM cosim-helics:latest AS cosim-python

USER root

ENV SIM_USER=tesp
ENV SIM_HOST=gage.pnl.gov
ENV SIM_WSL_HOST=
ENV SIM_WSL_PORT=
ENV SIM_DIR=/home/tesp/grid/copper

ENV COSIM_DB="copper"
ENV COSIM_USER="worker"
ENV COSIM_PASSWORD="worker"
ENV COSIM_HOME=/home/worker

ENV POSTGRES_HOST="gage.pnl.gov"
ENV POSTGRES_PORT=5432
ENV MONGO_HOST="mongodb://gage.pnl.gov:27017"

# Copy Files
COPY . /home/worker/cosim_toolbox/cosim_toolbox/
COPY --from=cosim-build:latest /home/worker/repo/AMES-V5.0/psst/ /home/worker/psst/psst/
COPY --from=cosim-build:latest /home/worker/repo/AMES-V5.0/README.rst /home/worker/psst
RUN chown -hR worker:worker /home/worker

# Set as user
USER worker
WORKDIR /home/worker

# Add directories and files
RUN echo "===== Building CoSim Python =====" && \
  echo "Pip install for virtual environment" && \
  pip install --upgrade pip > "_pypi.log" && \
  pip install virtualenv >> "_pypi.log" && \
  ".local/bin/virtualenv" venv --prompt TESP && \
  echo "Add python virtual environment to .bashrc" && \
  echo ". venv/bin/activate" >> .bashrc && \
  echo "Activate the python virtual environment" && \
  . venv/bin/activate && \
  pip install --upgrade pip > "pypi.log" && \
  echo "Install Python Libraries" && \
  pip install --no-cache-dir helics >> "pypi.log" && \
  pip install --no-cache-dir helics[cli] >> "pypi.log" && \
  cd /home/worker/cosim_toolbox/cosim_toolbox || exit && \
  pip install --no-cache-dir -e .  >> "/home/worker/pypi.log" && \
  cd /home/worker/psst/psst || exit && \
  pip install --no-cache-dir -e .  >> "/home/worker/pypi.log"
