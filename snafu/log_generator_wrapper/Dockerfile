FROM registry.access.redhat.com/ubi8:latest

COPY snafu/image_resources/centos8-appstream.repo /etc/yum.repos.d/centos8-appstream.repo
RUN dnf install -y --nodocs python3 python3-pip python3-devel gcc && dnf clean all
RUN dnf install -y --nodocs redis --enablerepo=centos8-appstream && dnf clean all
RUN curl -L https://mirror.openshift.com/pub/openshift-v4/clients/ocp/latest/openshift-client-linux.tar.gz | tar xz -C /usr/bin/ oc
RUN ln -s /usr/bin/python3 /usr/bin/python
RUN pip3 install --upgrade --no-cache-dir pip
RUN pip3 install kafka-python
RUN mkdir -p /opt/snafu/
COPY . /opt/snafu/
RUN pip3 install -e /opt/snafu/
