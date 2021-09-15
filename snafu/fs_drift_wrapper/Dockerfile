FROM registry.access.redhat.com/ubi8:latest

RUN dnf install -y --nodocs git python3-pip
RUN ln -s /usr/bin/python3 /usr/bin/python
COPY setup.cfg setup.py version.txt /opt/snafu/
RUN pip3 install -e /opt/snafu/
RUN git clone https://github.com/parallel-fs-utils/fs-drift /opt/fs-drift
RUN ln -sv /opt/fs-drift/fs-drift.py /usr/local/bin/
RUN ln -sv /opt/fs-drift/rsptime_stats.py /usr/local/bin/
COPY . /opt/snafu/
