FROM centos/tools
MAINTAINER Ben England <bengland@redhat.com>

RUN rpm -iv https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm
RUN yum install -y git python-elasticsearch6 python-redis python2-numpy
RUN git clone https://github.com/parallel-fs-utils/fs-drift /opt/fs-drift
COPY snafu /opt/snafu
