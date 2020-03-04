FROM registry.access.redhat.com/ubi8:latest
MAINTAINER Sai Sindhur Malleni <smalleni@redhat.org>

RUN dnf install -y --nodocs https://dl.fedoraproject.org/pub/epel/epel-release-latest-8.noarch.rpm
RUN dnf install -y --nodocs sysbench
RUN dnf install -y --nodocs procps-ng iproute net-tools ethtool nmap iputils
