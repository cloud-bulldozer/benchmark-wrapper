FROM docker.io/centos:8

RUN dnf install --nodocs -y python3-dnf-plugins-core
RUN dnf module disable postgresql -y
RUN dnf install -y --nodocs https://download.postgresql.org/pub/repos/yum/reporpms/EL-8-x86_64/pgdg-redhat-repo-latest.noarch.rpm
RUN dnf install -y --nodocs python3-pip python3-numpy python3-requests python3-pyyaml postgresql11 redis tcpdump
RUN pip3 install --upgrade-strategy=only-if-needed "elasticsearch>=6.0.0,<=7.0.2"
RUN ln -s /usr/bin/python3 /usr/bin/python
RUN ln -s /usr/pgsql-11/bin/pgbench /usr/bin/pgbench
RUN mkdir -p /opt/snafu/
COPY . /opt/snafu/
