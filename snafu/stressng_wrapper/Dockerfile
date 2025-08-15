FROM registry.access.redhat.com/ubi9:latest

# install requirements
RUN dnf install -y https://dl.fedoraproject.org/pub/epel/epel-release-latest-9.noarch.rpm
RUN dnf install -y --enablerepo=epel --nodocs stress-ng python3-pip python3-devel python3-requests gcc
RUN dnf install -y --nodocs procps-ng iproute net-tools ethtool nmap iputils

RUN dnf clean all
COPY . /opt/snafu
RUN pip3 install --upgrade pip
RUN pip3 install -e /opt/snafu/
RUN ln -s /usr/bin/python3 /usr/bin/python

RUN mkdir /opt/stressng && \
 chgrp 0 /opt/stressng && \
 chmod g+w /opt/stressng
WORKDIR /opt/stressng
