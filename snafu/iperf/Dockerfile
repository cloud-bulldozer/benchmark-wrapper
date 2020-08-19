FROM registry.access.redhat.com/ubi8:latest

COPY snafu/image_resources/centos8-appstream.repo /etc/yum.repos.d/centos8-appstream.repo
RUN dnf install -y --nodocs iperf3 --enablerepo=centos8-appstream
RUN dnf install -y --nodocs procps-ng iproute net-tools ethtool nmap iputils
