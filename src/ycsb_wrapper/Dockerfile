FROM registry.access.redhat.com/ubi8:latest

RUN curl -L https://github.com/brianfrankcooper/YCSB/releases/download/0.15.0/ycsb-0.15.0.tar.gz | tar xzf -
RUN mv ycsb-0.15.0 ycsb
RUN dnf install -y --nodocs https://dl.fedoraproject.org/pub/epel/epel-release-latest-8.noarch.rpm
RUN dnf install -y --nodocs git java python3 python2 python3-pip
RUN dnf install -y --nodocs procps-ng iproute net-tools ethtool nmap iputils
RUN ln -s /usr/bin/python3 /usr/bin/python
COPY . /opt/snafu/
RUN pip3 install -e /opt/snafu/
