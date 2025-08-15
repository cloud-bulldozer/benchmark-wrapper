ARG BASE_IMAGE=quay.io/cloud-bulldozer/nighthawk-base:latest
FROM ${BASE_IMAGE}
RUN apt-get update && apt-get install -y software-properties-common gcc && \
    add-apt-repository -y ppa:deadsnakes/ppa
RUN apt-get update && apt-get install -y python3.11 python3-distutils python3-pip python3-apt
RUN apt-get update && apt-get install -y redis-server
RUN ln -s /usr/bin/python3 /usr/bin/python
RUN mkdir -p /opt/snafu/
COPY . /opt/snafu/
RUN pip3 install --upgrade pip
RUN pip3 install -e /opt/snafu/
