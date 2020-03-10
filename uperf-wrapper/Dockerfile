FROM registry.access.redhat.com/ubi8:latest

RUN dnf copr enable ndokos/pbench -y
RUN dnf install -y --nodocs git python3-pip python3-numpy python3-requests python3-numpy pbench-uperf
COPY image_resources/centos8-appstream.repo /etc/yum.repos.d/centos8-appstream.repo
RUN dnf install -y --nodocs redis --enablerepo=centos8-appstream
RUN dnf install -y --nodocs procps-ng iproute net-tools ethtool nmap iputils
RUN ln -s /usr/bin/python3 /usr/bin/python
RUN mkdir -p /opt/snafu/
COPY . /opt/snafu/
RUN pip3 install --upgrade-strategy=only-if-needed -r /opt/snafu/requirements.txt
