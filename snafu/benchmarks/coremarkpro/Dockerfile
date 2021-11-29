FROM registry.access.redhat.com/ubi8:latest
MAINTAINER Ed Chong <edchong@redhat.com>

RUN dnf install -y --nodocs make git gcc && dnf clean all
RUN git clone https://github.com/eembc/coremark-pro.git && cd coremark-pro && ls util/make && make TARGET=linux64 build
WORKDIR /output/

RUN dnf install -y --nodocs python3.8 python38-devel procps-ng iproute net-tools ethtool nmap iputils && dnf clean all
RUN ln -s /usr/bin/python3 /usr/bin/python
RUN pip3 install --upgrade pip
COPY . /opt/snafu
RUN pip3 install -r /opt/snafu/requirements/py38-reqs/install.txt -e /opt/snafu
