FROM registry.access.redhat.com/ubi9:latest

# install requirements
COPY snafu/image_resources/centos9.repo /etc/yum.repos.d/centos9.repo
RUN dnf config-manager --set-enabled ubi-9-codeready-builder-rpms
RUN dnf install -y --nodocs tcl unixODBC python3-pip python3-requests python3-devel gcc
RUN dnf install -y --nodocs procps-ng iproute net-tools ethtool nmap iputils
RUN dnf -y install --enablerepo=centos9 --nodocs mysql-libs mysql-common mysql-devel mysql-errmsg libpq

RUN curl https://packages.microsoft.com/config/rhel/8/prod.repo -o /etc/yum.repos.d/mssql-release.repo
RUN ACCEPT_EULA=Y dnf -y install --skip-broken --nodocs msodbcsql17
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
