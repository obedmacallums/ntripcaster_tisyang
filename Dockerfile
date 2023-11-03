FROM ubuntu:18.04

EXPOSE 2101

WORKDIR /usr/src/app

COPY ntripcaster.json ./

COPY ntripcaster ./

RUN apt-get update && apt-get install -y libev-dev

RUN chmod +x ntripcaster

CMD ./ntripcaster