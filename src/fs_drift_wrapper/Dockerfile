FROM registry.access.redhat.com/ubi8:latest

RUN dnf install -y --nodocs git python3-pip
RUN dnf install -y --nodocs procps-ng iproute net-tools ethtool nmap iputils
RUN ln -s /usr/bin/python3 /usr/bin/python
COPY . /opt/snafu/
RUN pip3 install -e /opt/snafu/
ADD https://api.github.com/repos/parallel-fs-utils/fs-drift/git/refs/heads/master /tmp/bustcache
RUN git clone https://github.com/parallel-fs-utils/fs-drift /opt/fs-drift --depth 1
RUN ln -sv /opt/fs-drift/fs-drift.py /usr/local/bin/
RUN ln -sv /opt/fs-drift/rsptime_stats.py /usr/local/bin/
