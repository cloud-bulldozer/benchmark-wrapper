FROM registry.centos.org/centos:8

RUN dnf -y install --nodocs \
        epel-release \
        openssl-devel \
        python38 \
        yum-plugin-copr && \
    dnf -y install --nodocs ck-devel && \
    dnf -y copr enable @dnsoarc/dnsperf && \
    dnf -y install dnsperf && \
    dnf clean all && \
    rm --force --recursive /var/cache/yum && \
    ln --symbolic /usr/bin/python3 /usr/bin/python && \
    mkdir --parent /opt/snafu/snafu

COPY . /opt/snafu
RUN python -m pip install --editable /opt/snafu
