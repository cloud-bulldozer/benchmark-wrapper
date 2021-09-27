FROM registry.fedoraproject.org/fedora:34
USER root
RUN dnf install -y --nodocs python39 python3-devel numactl-devel perl \
    procps-ng iproute net-tools ethtool nmap iputils \
	rt-tests dumb-init wget tmux stress-ng \
	&& dnf clean all && rm -rf /var/cache/yum
COPY . /opt/snafu
RUN pip3 install --upgrade pip
RUN pip3 install -e /opt/snafu/
