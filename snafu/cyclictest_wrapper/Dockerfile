FROM registry.centos.org/centos:8
USER root
RUN dnf install -y --nodocs python3 python3-pip python3-devel numactl-devel perl \
    epel-release procps-ng iproute net-tools ethtool nmap iputils
RUN dnf -y install https://www.rpmfind.net/linux/centos/8-stream/AppStream/x86_64/os/Packages/rt-tests-1.8-11.el8.x86_64.rpm
RUN dnf -y --enablerepo=extras install --nodocs wget tmux \
    && dnf install -y --nodocs stress-ng \
    && dnf clean all && rm -rf /var/cache/yum \
    && wget -O /root/dumb-init https://github.com/Yelp/dumb-init/releases/download/v1.2.2/dumb-init_1.2.2_amd64 \
    && chmod 777 /root/dumb-init

