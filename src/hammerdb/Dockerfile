FROM registry.access.redhat.com/ubi8:latest

# install requirements
RUN dnf install -y --nodocs tcl unixODBC python3-pip
RUN dnf install -y --nodocs procps-ng iproute net-tools ethtool nmap iputils

RUN curl https://packages.microsoft.com/config/rhel/8/prod.repo -o /etc/yum.repos.d/mssql-release.repo
COPY /src/image_resources/centos8.repo /etc/yum.repos.d/centos8.repo
RUN ACCEPT_EULA=Y dnf -y install --nodocs msodbcsql17 --enablerepo=centos8
RUN dnf clean all
COPY . /opt/snafu
RUN pip3 install -e /opt/snafu/
RUN ln -s /usr/bin/python3 /usr/bin/python

# Download and install the hammer suite
RUN curl -L 'https://downloads.sourceforge.net/project/hammerdb/HammerDB/HammerDB-3.2/HammerDB-3.2-Linux-x86-64-Install?r=https%3A%2F%2Fsourceforge.net%2Fprojects%2Fhammerdb%2Ffiles%2FHammerDB%2FHammerDB-3.2%2FHammerDB-3.2-Linux-x86-64-Install%2Fdownload&ts=1564587940&use_mirror=autoselect' -o hammer_installer
RUN mkdir /hammer
RUN chmod 755 hammer_installer
RUN ./hammer_installer --prefix /hammer --mode silent
COPY src/hammerdb/uid_entrypoint /usr/local/bin/
RUN chmod g+w /etc/passwd
RUN chmod 755 /usr/local/bin/uid_entrypoint
RUN /usr/local/bin/uid_entrypoint
