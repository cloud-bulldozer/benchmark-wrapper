FROM registry.access.redhat.com/ubi9:latest

# install requirements
RUN dnf -y install --nodocs git wget procps python3 vim python3-pip python3-devel pciutils gcc && dnf clean all
RUN dnf install -y --nodocs hostname iproute net-tools ethtool nmap iputils https://dl.fedoraproject.org/pub/epel/epel-release-latest-9.noarch.rpm && dnf clean all

# install trex server
RUN mkdir -p /opt/trex
WORKDIR /opt/trex
RUN wget --no-check-certificate https://trex-tgn.cisco.com/trex/release/v2.87.tar.gz
RUN tar -xzf v2.87.tar.gz

# download trex library
RUN git clone -b v2.87 https://github.com/cisco-system-traffic-generator/trex-core.git
ENV PYTHONPATH="/opt/trex/trex-core/scripts/automation/trex_control_plane/interactive"

# copy script
COPY snafu/trex_wrapper/scripts/ /usr/local/bin/
RUN chmod +x /usr/local/bin/run*

# copy snafu script
RUN ln -s /usr/bin/python3 /usr/bin/python
RUN mkdir -p /opt/snafu/
COPY . /opt/snafu/
RUN pip3 install --upgrade pip
RUN pip3 install -e /opt/snafu/

WORKDIR /opt/trex/v2.87
