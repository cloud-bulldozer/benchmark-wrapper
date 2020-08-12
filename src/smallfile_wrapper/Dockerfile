FROM registry.access.redhat.com/ubi8:latest

RUN dnf install -y --nodocs git python3-pip
RUN dnf install -y --nodocs procps-ng iproute net-tools ethtool nmap iputils
RUN ln -s /usr/bin/python3 /usr/bin/python
ADD https://api.github.com/repos/distributed-system-analysis/smallfile/git/refs/heads/master /tmp/bustcache
RUN git clone https://github.com/distributed-system-analysis/smallfile /opt/smallfile --depth 1
RUN ln -sv /opt/smallfile/smallfile_cli.py /usr/local/bin/
RUN ln -sv /opt/smallfile/smallfile_rsptimes_stats.py /usr/local/bin/
# assumption: docker build -f smallfile_wrapper/Dockerfile .
COPY . /opt/snafu/
RUN pip3 install -e /opt/snafu/
