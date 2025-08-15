FROM registry.access.redhat.com/ubi9:latest
MAINTAINER Ed Chong <edchong@redhat.com>

RUN dnf install -y --nodocs make git gcc && dnf clean all
RUN git clone https://github.com/eembc/coremark-pro.git && cd coremark-pro && ls util/make && make TARGET=linux64 build
WORKDIR /output/

RUN dnf install -y --nodocs python3.11 python3.11-devel procps-ng iproute net-tools ethtool nmap iputils && dnf clean all
RUN ln -s /usr/bin/python3 /usr/bin/python
RUN pip3 install --upgrade pip
COPY . /opt/snafu
RUN pip3 install -e /opt/snafu
