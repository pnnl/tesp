FROM temcderm/tesp_foundation
LABEL maintainer="Thomas.McDermott@pnnl.gov"

ADD tesp-0.6.3-linux-x64-installer.run /tmp/installer.run
RUN /tmp/installer.run --mode unattended
RUN rm /tmp/installer.run

VOLUME /data
