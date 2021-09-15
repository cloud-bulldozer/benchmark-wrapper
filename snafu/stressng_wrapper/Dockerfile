FROM registry.access.redhat.com/ubi8:latest

# install requirements
COPY snafu/image_resources/centos8.repo /etc/yum.repos.d/centos8.repo
COPY snafu/image_resources/centos8-appstream.repo /etc/yum.repos.d/centos8-appstream.repo
RUN dnf install -y https://dl.fedoraproject.org/pub/epel/epel-release-latest-8.noarch.rpm python39 && dnf clean all
RUN dnf install -y --enablerepo=centos8 --enablerepo=centos8-appstream --enablerepo=epel --nodocs stress-ng python39-requests \
    procps-ng iproute net-tools ethtool nmap iputils && dnf clean all

COPY . /opt/snafu
RUN pip3 install --upgrade pip
RUN pip3 install -e /opt/snafu/
RUN ln -s /usr/bin/python3 /usr/bin/python

RUN mkdir /opt/stressng &&  \
    chgrp 0 /opt/stressng && \
    chmod g+w /opt/stressng
WORKDIR /opt/stressng
