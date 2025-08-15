FROM registry.access.redhat.com/ubi9:latest

RUN dnf install -y --nodocs https://download.postgresql.org/pub/repos/yum/reporpms/EL-8-x86_64/pgdg-redhat-repo-latest.noarch.rpm
RUN dnf install -y --nodocs python3-pip python3-devel gcc postgresql11
RUN dnf install -y --nodocs redis RUN dnf install -y --nodocs procps-ng iproute net-tools ethtool nmap iputils
RUN ln -s /usr/bin/python3 /usr/bin/python
RUN ln -s /usr/pgsql-11/bin/pgbench /usr/bin/pgbench
RUN mkdir -p /opt/snafu/
COPY . /opt/snafu/
RUN pip3 install --upgrade pip
RUN pip3 install -e /opt/snafu/
