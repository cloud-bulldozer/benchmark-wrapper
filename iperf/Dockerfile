FROM ubi8:latest

COPY image_resources/centos8-appstream.repo /etc/yum.repos.d/centos8-appstream.repo
RUN dnf install --nodocs -y iperf3 --enablerepo=centos8-appstream
