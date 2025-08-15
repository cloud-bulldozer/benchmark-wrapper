FROM registry.access.redhat.com/ubi9:latest

RUN curl -L https://github.com/brianfrankcooper/YCSB/releases/download/0.15.0/ycsb-0.15.0.tar.gz | tar xz && mv ycsb-0.15.0 ycsb
RUN dnf install -y --nodocs https://dl.fedoraproject.org/pub/epel/epel-release-latest-9.noarch.rpm
RUN dnf install -y --nodocs git java python3 python2 python3-pip python3-devel gcc procps-ng iproute net-tools ethtool nmap iputils && dnf clean all
RUN ln -s /usr/bin/python3 /usr/bin/python
COPY . /opt/snafu/
RUN pip3 install --upgrade --no-cache-dir pip
RUN pip3 install -e /opt/snafu/
