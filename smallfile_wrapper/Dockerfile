FROM docker.io/centos:8

RUN dnf install --nodocs -y git python3-pip python3-numpy python3-requests python3-scipy python3-pyyaml tcpdump
RUN pip3 install --upgrade-strategy=only-if-needed "elasticsearch>=6.0.0,<=7.0.2" redis
RUN ln -s /usr/bin/python3 /usr/bin/python
ADD https://api.github.com/repos/distributed-system-analysis/smallfile/git/refs/heads/master /tmp/bustcache
RUN git clone https://github.com/distributed-system-analysis/smallfile /opt/smallfile --depth 1
RUN ln -sv /opt/smallfile/smallfile_cli.py /usr/local/bin/
RUN ln -sv /opt/smallfile/smallfile_rsptimes_stats.py /usr/local/bin/
COPY . /opt/snafu/
