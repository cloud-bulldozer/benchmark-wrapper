FROM centos/tools

USER root
RUN rpm -ivh https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm
RUN rpm -ivh https://download.postgresql.org/pub/repos/yum/reporpms/EL-7-x86_64/pgdg-redhat-repo-latest.noarch.rpm
RUN yum -y update
RUN yum install -y postgresql11
RUN yum install -y redis
RUN yum install -y git python-pip
RUN pip install --upgrade pip
RUN pip install "elasticsearch>=6.0.0,<=7.0.2"
RUN yum install -y numpy
RUN ln -s /usr/pgsql-11/bin/pgbench /usr/bin/pgbench
COPY snafu /opt/snafu
