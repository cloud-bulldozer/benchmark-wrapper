FROM registry.access.redhat.com/ubi9:latest
MAINTAINER Ed Chong <edchong@redhat.com>

RUN dnf install -y --nodocs https://dl.fedoraproject.org/pub/epel/epel-release-latest-9.noarch.rpm
RUN dnf install -y --nodocs sysbench && dnf clean all

RUN dnf install -y --nodocs python3.11 python3.11-devel procps-ng iproute net-tools ethtool nmap iputils gcc && dnf clean all
RUN ln -s /usr/bin/python3 /usr/bin/python
RUN pip3 install --upgrade pip # benchmark-wrapper fails to install otherwise
COPY . /opt/snafu
RUN pip3 install -e /opt/snafu
