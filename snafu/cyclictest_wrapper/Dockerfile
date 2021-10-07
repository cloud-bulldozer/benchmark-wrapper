FROM registry.fedoraproject.org/fedora:34
USER root
RUN dnf install -y --nodocs python3 python3-pip python3-devel numactl-devel perl \
    procps-ng iproute net-tools ethtool nmap iputils \
    rt-tests dumb-init wget tmux stress-ng \
    && dnf clean all && rm -rf /var/cache/yum
COPY . /opt/snafu
RUN pip install --upgrade pip
RUN pip install -e /opt/snafu/
