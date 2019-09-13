FROM centos/tools

USER root
RUN rpm -ivh https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm
RUN yum install -y yum-plugin-copr
RUN yes | yum copr enable ndokos/pbench
RUN yum install -y pbench-uperf
RUN yum install -y redis
RUN yum install -y git python-pip
RUN pip install --upgrade pip
RUN pip install "elasticsearch>=6.0.0,<=7.0.2"
RUN yum install -y numpy
COPY snafu /opt/snafu
