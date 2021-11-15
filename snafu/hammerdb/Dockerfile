FROM registry.access.redhat.com/ubi8:latest

# install requirements
COPY snafu/image_resources/centos8.repo /etc/yum.repos.d/centos8.repo
COPY snafu/image_resources/centos8-appstream.repo /etc/yum.repos.d/centos8-appstream.repo
RUN dnf install -y --enablerepo=centos8 --enablerepo=centos8-appstream --nodocs tcl unixODBC python3-pip python3-requests python3-devel gcc
RUN dnf install -y --enablerepo=centos8 --enablerepo=centos8-appstream --nodocs procps-ng iproute net-tools ethtool nmap iputils
RUN dnf -y install --enablerepo=centos8 --enablerepo=centos8-appstream --nodocs mysql-libs mysql-common mysql-devel mysql-errmsg libpq

RUN curl https://packages.microsoft.com/config/rhel/8/prod.repo -o /etc/yum.repos.d/mssql-release.repo
RUN ACCEPT_EULA=Y dnf -y install --skip-broken --enablerepo=centos8 --enablerepo=centos8-appstream --nodocs msodbcsql17
RUN dnf clean all
COPY . /opt/snafu
RUN pip3 install --upgrade pip
RUN pip3 install -e /opt/snafu/
RUN ln -s /usr/bin/python3 /usr/bin/python

# Download and install the hammer suite
RUN curl -LO https://github.com/TPC-Council/HammerDB/releases/download/v4.0/HammerDB-4.0-Linux.tar.gz
RUN tar -xf HammerDB-4.0-Linux.tar.gz
RUN mkdir /hammer
RUN mv HammerDB-4.0/* /hammer
COPY snafu/hammerdb/uid_entrypoint /usr/local/bin/
RUN chmod g+w /etc/passwd
RUN chmod 755 /usr/local/bin/uid_entrypoint
RUN /usr/local/bin/uid_entrypoint
