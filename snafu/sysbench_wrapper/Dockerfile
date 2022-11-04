FROM registry.access.redhat.com/ubi8:latest
MAINTAINER Ed Chong <edchong@redhat.com>

RUN dnf install -y --nodocs https://dl.fedoraproject.org/pub/epel/epel-release-latest-8.noarch.rpm
RUN dnf install -y --nodocs sysbench && dnf clean all

RUN dnf install -y --nodocs python3.8 python38-devel procps-ng iproute net-tools ethtool nmap iputils gcc && dnf clean all
RUN ln -s /usr/bin/python3 /usr/bin/python
RUN pip3 install --upgrade pip # benchmark-wrapper fails to install otherwise
COPY . /opt/snafu
RUN pip3 install -r /opt/snafu/requirements/py38-reqs/install.txt -e /opt/snafu
