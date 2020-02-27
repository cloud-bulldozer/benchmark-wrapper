FROM docker.io/centos:8

# install requirements
RUN dnf install --nodocs -y tcl unixODBC python3-pip python3-requests python3-pyyaml tcpdump

RUN curl https://packages.microsoft.com/config/rhel/8/prod.repo -o /etc/yum.repos.d/mssql-release.repo
RUN ACCEPT_EULA=Y dnf -y install --nodocs msodbcsql17
RUN pip3 install --upgrade-strategy=only-if-needed "elasticsearch>=6.0.0,<=7.0.2"
COPY . /opt/snafu
RUN ln -s /usr/bin/python3 /usr/bin/python

# Download and install the hammer suite
RUN curl -L 'https://downloads.sourceforge.net/project/hammerdb/HammerDB/HammerDB-3.2/HammerDB-3.2-Linux-x86-64-Install?r=https%3A%2F%2Fsourceforge.net%2Fprojects%2Fhammerdb%2Ffiles%2FHammerDB%2FHammerDB-3.2%2FHammerDB-3.2-Linux-x86-64-Install%2Fdownload&ts=1564587940&use_mirror=autoselect' -o hammer_installer
RUN mkdir /hammer
RUN chmod 755 hammer_installer
RUN ./hammer_installer --prefix /hammer --mode silent
COPY hammerdb/uid_entrypoint /usr/local/bin/
RUN chmod g+w /etc/passwd
RUN chmod 755 /usr/local/bin/uid_entrypoint
RUN /usr/local/bin/uid_entrypoint
