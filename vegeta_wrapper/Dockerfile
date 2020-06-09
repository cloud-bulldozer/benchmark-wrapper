FROM registry.access.redhat.com/ubi8:latest

COPY image_resources/centos8-appstream.repo /etc/yum.repos.d/centos8-appstream.repo
RUN dnf install -y --nodocs python3 python3-pip procps-ng iproute net-tools ethtool nmap iputils && dnf clean all
RUN dnf install -y --nodocs redis --enablerepo=centos8-appstream && dnf clean all
RUN curl -L https://github.com/tsenart/vegeta/releases/download/v12.8.3/vegeta-12.8.3-linux-amd64.tar.gz | tar xz -C /usr/bin/ vegeta
RUN mkdir -p /opt/snafu/
COPY requirements.txt /opt/snafu/requirements.txt
RUN pip3 install --upgrade-strategy=only-if-needed -r /opt/snafu/requirements.txt
COPY . /opt/snafu/
