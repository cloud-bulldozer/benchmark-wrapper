FROM centos/tools

# install requirements
RUN rpm -ivh https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm
RUN yum install -y expect wget tcl unixODBC-devel unixODBC

RUN curl https://packages.microsoft.com/config/rhel/7/prod.repo > /etc/yum.repos.d/mssql-release.repo
RUN ACCEPT_EULA=Y yum -y install msodbcsql17
RUN ACCEPT_EULA=Y yum -y install msodbcsql
RUN yum remove -y unixODBC-utf16 unixODBC-utf16-devel && yum -y clean all
RUN yum clean all -y 

RUN yum install -y git python-pip
RUN pip install --upgrade pip
RUN pip install "elasticsearch>=6.0.0,<=7.0.2"

# clone the snafu repo 
RUN cd /opt/; git clone https://github.com/mkarg75/snafu.git
#RUN cd /opt/; git clone https://github.com/cloud-bulldozer/snafu.git

# Download and install the hammer suite
RUN wget 'https://downloads.sourceforge.net/project/hammerdb/HammerDB/HammerDB-3.2/HammerDB-3.2-Linux-x86-64-Install?r=https%3A%2F%2Fsourceforge.net%2Fprojects%2Fhammerdb%2Ffiles%2FHammerDB%2FHammerDB-3.2%2FHammerDB-3.2-Linux-x86-64-Install%2Fdownload&ts=1564587940&use_mirror=autoselect' -O hammer_installer
RUN mkdir /hammer
RUN chmod 755 hammer_installer
RUN ./hammer_installer --prefix /hammer --mode silent

COPY createdb.tcl /hammer
COPY run_test.tcl /hammer
COPY uid_entrypoint /usr/local/bin/
COPY script.exp /hammer
COPY test.exp /hammer
COPY entrypoint /usr/local/bin/

RUN chmod g+w /etc/passwd
RUN chmod 755 /hammer/script.exp
RUN chmod 755 /hammer/test.exp
RUN chmod 755 /usr/local/bin/uid_entrypoint
RUN chmod 755 /usr/local/bin/entrypoint
RUN /usr/local/bin/uid_entrypoint




