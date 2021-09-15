FROM registry.access.redhat.com/ubi8:latest

RUN dnf install -y --nodocs git python39 && dnf clean all
COPY snafu/image_resources/centos8-appstream.repo /etc/yum.repos.d/centos8-appstream.repo
RUN dnf install -y --nodocs redis --enablerepo=centos8-appstream && dnf clean all
RUN dnf install -y --nodocs hostname procps-ng iproute net-tools ethtool nmap iputils https://dl.fedoraproject.org/pub/epel/epel-release-latest-8.noarch.rpm && dnf clean all
RUN dnf install -y uperf && dnf clean all
RUN ln -s /usr/bin/python3 /usr/bin/python
COPY . /opt/snafu/
RUN pip3 install --upgrade pip
RUN pip3 install -e /opt/snafu/
