FROM docker://registry.access.redhat.com/ubi8:latest

COPY snafu/image_resources/centos8-appstream.repo /etc/yum.repos.d/centos8-appstream.repo
RUN dnf install -y --nodocs python39 && dnf clean all
RUN dnf install -y --nodocs skopeo redis --enablerepo=centos8-appstream && dnf clean all
RUN ln -s /usr/bin/python3 /usr/bin/python
COPY . /opt/snafu/
RUN pip3 install --upgrade pip
RUN pip3 install -e /opt/snafu/
