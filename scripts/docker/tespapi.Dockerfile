# Build runtime image
FROM cosim-python:latest AS cosim-tespapi

USER root

ARG COSIM_USER
ENV COSIM_HOME=/home/$COSIM_USER

# Compile exports

# Copy files

# Set as user
USER $COSIM_USER
WORKDIR $COSIM_HOME

# Add directories and files
RUN echo "Building CoSim TESP api" && \
  echo "Activate the python virtual environment" && \
  . venv/bin/activate && \
  pip install --no-cache-dir tesp-support >> pypi.log && \
  tesp_component -c 1
