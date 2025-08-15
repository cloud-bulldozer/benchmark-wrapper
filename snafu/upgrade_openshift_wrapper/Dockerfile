FROM registry.access.redhat.com/ubi9:latest

RUN dnf install -y --nodocs python3 python3-pip python3-devel gcc && dnf clean all
RUN dnf install -y --nodocs redis && dnf clean all
RUN curl -L https://mirror.openshift.com/pub/openshift-v4/clients/ocp/latest/openshift-client-linux.tar.gz | tar xz -C /usr/bin/ oc
RUN ln -s /usr/bin/python3 /usr/bin/python
RUN mkdir -p /opt/snafu/
COPY . /opt/snafu/
RUN pip3 install --upgrade pip
RUN pip3 install -e /opt/snafu/
