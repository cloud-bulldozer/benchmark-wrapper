FROM registry.centos.org/centos:8

COPY snafu/image_resources/centos8-appstream.repo /etc/yum.repos.d/centos8-appstream.repo

RUN dnf --yes install --nodocs \
        epel-release \
        openssl-devel \
        python38 \
        yum-plugin-copr && \
    dnf --yes install --nodocs ck-devel && \
    dnf --yes copr enable @dnsoarc/dnsperf && \
    dnf --yes install dnsperf && \
    dnf clean all && \
    rm --force --recursive /var/cache/yum && \
    ln --symbolic /usr/bin/python3 /usr/bin/python && \
    mkdir --parent /opt/snafu

COPY . /opt/snafu

RUN python --module pip install --editable /opt/snafu
