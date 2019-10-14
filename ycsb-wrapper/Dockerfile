FROM centos:7

USER root
RUN rpm -ivh https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm
RUN yum install -y java
RUN curl -O --location https://github.com/brianfrankcooper/YCSB/releases/download/0.15.0/ycsb-0.15.0.tar.gz
RUN mkdir ycsb
RUN tar xzf ycsb-0.15.0.tar.gz -C ycsb --strip-components 1
RUN yum install -y redis
RUN yum install -y git python-pip
RUN pip install --upgrade pip
RUN pip install "elasticsearch>=6.0.0,<=7.0.2"
RUN yum install -y numpy
RUN mkdir -p /opt/snafu/
COPY . /opt/snafu/
