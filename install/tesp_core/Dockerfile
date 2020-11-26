FROM temcderm/tesp_foundation:1.0.1
LABEL maintainer="Thomas.McDermott@pnnl.gov"

ADD tesp-1.0.0-linux-x64-installer.run /tmp/installer.run
RUN /tmp/installer.run --mode unattended
RUN rm /tmp/installer.run

VOLUME /data
