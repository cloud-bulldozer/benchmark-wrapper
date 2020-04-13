FROM registry.access.redhat.com/ubi8:latest as builder

RUN dnf install -y --nodocs git autoconf automake gcc make
COPY image_resources/centos8.repo /etc/yum.repos.d/centos8.repo
RUN dnf install -y --enablerepo=centos8 lksctp-tools-devel
RUN ln -s /usr/bin/python3 /usr/bin/python
RUN git clone https://github.com/uperf/uperf /tmp/uperf
RUN pushd /tmp/uperf && autoreconf --install &&  ./configure --enable-cpc --enable-debug;make

FROM registry.access.redhat.com/ubi8:latest
COPY --from=builder /tmp/uperf/src/uperf /usr/local/bin/uperf
RUN dnf install -y --nodocs python3-pip python3-numpy python3-requests python3-numpy
COPY image_resources/centos8-appstream.repo /etc/yum.repos.d/centos8-appstream.repo
RUN dnf install -y --nodocs redis lksctp-tools --enablerepo=centos8-appstream
RUN dnf install -y --nodocs procps-ng iproute net-tools ethtool nmap iputils
RUN ln -s /usr/bin/python3 /usr/bin/python
RUN mkdir -p /opt/snafu/
COPY . /opt/snafu/
RUN pip3 install --upgrade-strategy=only-if-needed -r /opt/snafu/requirements.txt
