FROM registry.centos.org/centos:8

COPY snafu/image_resources/centos8-appstream.repo /etc/yum.repos.d/centos8-appstream.repo

# dnsperf dependencies
RUN dnf install -y --nodocs epel-release && \
    dnf install -y --nodocs \
        ck-devel \
        openssl-devel \
        yum-plugin-copr && \
    dnf copr enable @dnsoarc/dnsperf -y && \
    dnf install dnsperf -y && \
    dnf clean all && \
    rm -fr /var/cache/yum

# snafu dependencies
RUN dnf install -y python38 && \
    ln -s /usr/local/bin/python3 /usr/local/bin/python && \
    python -m pip install -U pip && \
    mkdir --parent /opt/snafu

COPY . /opt/snafu

RUN python -m pip install -e /opt/snafu
