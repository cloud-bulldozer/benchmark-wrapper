FROM registry.access.redhat.com/ubi9:latest

RUN dnf install -y --nodocs git python3 python3-pip python3-devel gcc && dnf clean all
RUN ln -s /usr/bin/python3 /usr/bin/python
ADD https://api.github.com/repos/distributed-system-analysis/smallfile/git/refs/heads/master /tmp/bustcache
RUN git clone https://github.com/distributed-system-analysis/smallfile /opt/smallfile
RUN ln -sv /opt/smallfile/smallfile_cli.py /usr/local/bin/
RUN ln -sv /opt/smallfile/smallfile_rsptimes_stats.py /usr/local/bin/
COPY . /opt/snafu/
RUN pip3 install --upgrade pip
RUN pip3 install -e /opt/snafu/
