FROM docker.io/centos:8

RUN dnf install --nodocs -y python3-dnf-plugins-core
RUN dnf copr enable ndokos/pbench -y
RUN dnf install -y --nodocs git python3-pip python3-numpy python3-requests python3-numpy python3-pyyaml pbench-uperf redis
RUN pip3 install --upgrade-strategy=only-if-needed "elasticsearch>=6.0.0,<=7.0.2"
RUN ln -s /usr/bin/python3 /usr/bin/python
RUN mkdir -p /opt/snafu/
COPY . /opt/snafu/
