FROM registry.access.redhat.com/ubi8:latest

RUN dnf copr enable ndokos/pbench -y
COPY image_resources/centos8-appstream.repo /etc/yum.repos.d/centos8-appstream.repo
RUN dnf install -y --nodocs pbench-fio --enablerepo=centos8-appstream
RUN dnf install -y --nodocs git python3-pip python3-requests python3-numpy
RUN dnf install -y --nodocs procps-ng iproute net-tools ethtool nmap iputils
RUN pip3 install --upgrade-strategy=only-if-needed pyyaml "elasticsearch>=6.0.0,<=7.0.2"
RUN ln -s /usr/bin/python3 /usr/bin/python
COPY . /opt/snafu/
