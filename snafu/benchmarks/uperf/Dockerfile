FROM registry.access.redhat.com/ubi9:latest

RUN dnf install -y --nodocs git gcc python3-pip python3-devel && dnf clean all
RUN dnf install -y --nodocs redis && dnf clean all
RUN dnf install -y --nodocs hostname procps-ng iproute net-tools ethtool nmap iputils https://dl.fedoraproject.org/pub/epel/epel-release-latest-9.noarch.rpm && dnf clean all
RUN dnf install -y uperf && dnf clean all
RUN ln -s /usr/bin/python3 /usr/bin/python
RUN mkdir -p /opt/snafu/
COPY . /opt/snafu/
RUN pip3 install --upgrade pip
RUN pip3 install -e /opt/snafu/
