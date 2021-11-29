FROM registry.centos.org/centos:8

COPY snafu/image_resources/centos8-appstream.repo /etc/yum.repos.d/centos8-appstream.repo
RUN dnf install -y epel-release && dnf install -y --nodocs redis python3 python3-pip openssl-devel ck-devel yum-plugin-copr gcc && \
    dnf copr enable @dnsoarc/dnsperf -y && \
    dnf install dnsperf -y && \
    dnf clean all && rm -rf /var/cache/yum
RUN curl -L https://mirror.openshift.com/pub/openshift-v4/clients/ocp/latest/openshift-client-linux.tar.gz | tar xz -C /usr/bin/ oc && ln -s /usr/bin/python3 /usr/bin/python
RUN mkdir -p /opt/snafu/
COPY . /opt/snafu/
RUN pip3 install --upgrade pip
RUN pip3 install -e /opt/snafu/
