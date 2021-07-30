FROM registry.access.redhat.com/ubi8:latest
MAINTAINER Sai Sindhur Malleni <smalleni@redhat.org>

RUN dnf install -y --nodocs https://dl.fedoraproject.org/pub/epel/epel-release-latest-8.noarch.rpm
RUN dnf install -y --nodocs sysbench && dnf clean all

RUN dnf install -y --nodocs python3-pip procps-ng iproute net-tools ethtool nmap iputils && dnf clean all
RUN ln -s /usr/bin/python3 /usr/bin/python
COPY . /opt/snafu
RUN pip3 install --upgrade # benchmark-wrapper fails to install otherwise
RUN pip3 install -e /opt/snafu/
