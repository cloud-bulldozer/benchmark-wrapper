FROM centos/tools

USER root
WORKDIR /root/
RUN yum install git epel-release -y
RUN yum install python2-elasticsearch python2-numpy python2-configparser python2-redis -y
RUN git clone https://github.com/distributed-system-analysis/smallfile
RUN mv smallfile smallfile-master
RUN mkdir -p /opt/snafu/
COPY . /opt/snafu/
