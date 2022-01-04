# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: Dockerfile

FROM temcderm/tesp_foundation:1.0.2
LABEL maintainer="Thomas.McDermott@pnnl.gov"

ADD tesp-1.0.2-linux-x64-installer.run /tmp/installer.run
RUN /tmp/installer.run --mode unattended
RUN rm /tmp/installer.run

VOLUME /data
