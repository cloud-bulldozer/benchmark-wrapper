FROM quay.io/centos/centos:stream8
USER root
RUN dnf install -y --nodocs python39 python39-devel numactl-devel perl \
    epel-release procps-ng iproute net-tools ethtool nmap iputils dumb-init rt-tests \
	wget tmux && dnf clean all && rm -rf /var/cache/yum
COPY . /opt/snafu
RUN pip3 install --upgrade pip
RUN pip3 install -e /opt/snafu/
RUN ln -s /usr/bin/python3 /usr/bin/python
