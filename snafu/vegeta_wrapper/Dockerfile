FROM registry.access.redhat.com/ubi9:latest

RUN dnf install -y --nodocs python3 python3-pip python3-devel procps-ng iproute net-tools ethtool nmap iputils gcc && dnf clean all
RUN dnf install -y --nodocs redis && dnf clean all
RUN curl -L https://github.com/tsenart/vegeta/releases/download/v12.8.3/vegeta-12.8.3-linux-amd64.tar.gz | tar xz -C /usr/bin/ vegeta
RUN ln -s /usr/bin/python3 /usr/bin/python
RUN mkdir -p /opt/snafu/
COPY . /opt/snafu/
RUN pip3 install --upgrade pip
RUN pip3 install -e /opt/snafu/
