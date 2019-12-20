FROM ubi8:latest

RUN dnf install --nodocs -y git python3-pip python3-numpy python3-requests python3-scipy
RUN pip3 install --upgrade-strategy=only-if-needed "elasticsearch>=6.0.0,<=7.0.2" redis pyyaml
RUN ln -s /usr/bin/python3 /usr/bin/python
COPY . /opt/snafu/
ADD https://api.github.com/repos/parallel-fs-utils/fs-drift/git/refs/heads/master /tmp/bustcache
RUN git clone https://github.com/parallel-fs-utils/fs-drift /opt/fs-drift --depth 1
RUN ln -sv /opt/fs-drift/fs-drift.py /usr/local/bin/
RUN ln -sv /opt/fs-drift/rsptime_stats.py /usr/local/bin/
