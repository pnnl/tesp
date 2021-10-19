IMG_NAME=ubuntu-1604_jmodelica_trunk

COMMAND_RUN=docker run \
	  --name jmodelica \
	  --detach=false \
	  -e DISPLAY=${DISPLAY} \
	  -v /tmp/.X11-unix:/tmp/.X11-unix \
	  --rm \
	  -v `pwd`/shared:/mnt/shared \
	  -i \
          -t \
	  ${IMG_NAME} /bin/bash -c


COMMAND_START=docker run \
	  --name jmodelica \
	  --detach=false \
	  --rm \
	  --interactive \
	  -t \
	  -v `pwd`/shared:/mnt/shared \
	  ${IMG_NAME} \
	  /bin/bash -c -i

build:
	docker build --no-cache --rm -t ${IMG_NAME} .

push:
	docker push ${IMG_NAME}


remove-image:
	docker rmi ${IMG_NAME}

start_bash:
	$(COMMAND_START) \
	   "export MODELICAPATH=/usr/local/JModelica/ThirdParty/MSL:. && \
            cd /mnt/shared && bash"

start_ipython:
	$(COMMAND_START) \
	   "export MODELICAPATH=/usr/local/JModelica/ThirdParty/MSL:. && \
            cd /mnt/shared && \
	    /usr/local/JModelica/bin/jm_ipython.sh"

clean_output:
	rm `pwd`/shared/{*.txt,*.fmu}

run_bash:
	$(COMMAND_RUN) \
	   "export MODELICAPATH=/usr/local/JModelica/ThirdParty/MSL:. && \
            cd /mnt/shared && bash"
