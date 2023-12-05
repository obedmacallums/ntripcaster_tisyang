


FROM ubuntu:18.04

ARG USERS=test
ARG PASS=test
ARG MOUNT_POINTS=*

WORKDIR /usr/src/app

RUN apt-get update && apt-get install -y libev-dev
RUN apt-get install -y python3 python3-pip

COPY create_config_from_env.py ./

RUN export USERS=${USERS} && export PASS=${PASS} && export MOUNT_POINTS=${MOUNT_POINTS} && python3 create_config_from_env.py

COPY ntripcaster ./


RUN chmod +x ntripcaster

CMD ./ntripcaster ok.json