FROM registry.access.redhat.com/ubi8:latest

RUN dnf install -y --nodocs git python3-pip && dnf clean all
COPY /snafu/image_resources/centos8-appstream.repo /etc/yum.repos.d/centos8-appstream.repo
RUN dnf install -y --nodocs redis --enablerepo=centos8-appstream && dnf clean all

RUN yum -y install wget gcc make --nodocs
RUN dnf -y install python3-pip --nodocs
RUN yum -y install bzip2 --nodocs
RUN yum -y install iputils --nodocs
RUN pip3 install flent
RUN wget https://github.com/HewlettPackard/netperf/archive/netperf-2.7.0.tar.gz && tar -xzf netperf-2.7.0.tar.gz
RUN sed -i 's/inline void demo_interval_display(double actual_interval)/void demo_interval_display(double actual_interval)/g' /netperf-netperf-2.7.0/src/netlib.c && sed -i 's/inline void demo_interval_tick(uint32_t units)/void demo_interval_tick(uint32_t units)/g' /netperf-netperf-2.7.0/src/netlib.c
RUN cd netperf-netperf-2.7.0 && ./configure --enable-demo && make && make install

#RUN dnf install -y --nodocs hostname procps-ng iproute net-tools ethtool nmap iputils https://dl.fedoraproject.org/pub/epel/epel-release-latest-8.noarch.rpm && dnf clean all
#RUN dnf install -y uperf && dnf clean all
#RUN ln -s /usr/bin/python3 /usr/bin/python
RUN mkdir -p /opt/snafu/
COPY . /opt/snafu/
RUN pip3 install -e /opt/snafu/

WORKDIR /
RUN yum -y install gcc-c++
RUN yum update -y
RUN git clone https://git.code.sf.net/p/iperf2/code iperf2-code
WORKDIR /iperf2-code
RUN ./configure && make && make install
WORKDIR /
