FROM registry.access.redhat.com/ubi8:latest

# install requirements
COPY snafu/image_resources/centos8.repo /etc/yum.repos.d/centos8.repo
COPY snafu/image_resources/centos8-appstream.repo /etc/yum.repos.d/centos8-appstream.repo
COPY snafu/image_resources/epel.repo /etc/yum.repos.d/epel.repo
COPY snafu/image_resources/RPM-GPG-KEY-EPEL-8 /etc/pki/rpm-gpg/RPM-GPG-KEY-EPEL-8
RUN dnf install -y --enablerepo=centos8 --enablerepo=centos8-appstream --enablerepo=epel --nodocs stress-ng python3-pip python3-requests
RUN dnf install -y --enablerepo=centos8 --enablerepo=centos8-appstream --nodocs procps-ng iproute net-tools ethtool nmap iputils

RUN dnf clean all
COPY . /opt/snafu
RUN pip3 install -e /opt/snafu/
RUN ln -s /usr/bin/python3 /usr/bin/python

# Download and install the hammer suite
#COPY snafu/hammerdb/uid_entrypoint /usr/local/bin/
#RUN chmod g+w /etc/passwd
#RUN chmod 755 /usr/local/bin/uid_entrypoint
#RUN /usr/local/bin/uid_entrypoint

