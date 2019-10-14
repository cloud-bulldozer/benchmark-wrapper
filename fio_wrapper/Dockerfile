FROM centos/tools

USER root
RUN rpm -ivh https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm
RUN yum install -y yum-plugin-copr
RUN yes | yum copr enable ndokos/pbench
RUN yum install -y pbench-fio
RUN yum install -y git python-pip
RUN pip install --upgrade pip
RUN pip install elasticsearch numpy configparser statistics
RUN mkdir -p /opt/snafu/
COPY . /opt/snafu/
