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
## download, compile python 3.7
RUN dnf install -y \
        bzip2-devel \
        gcc \
        libffi-devel \
        make \
        openssl-devel \
        xz-devel \
        zlib-devel && \
    curl https://www.python.org/ftp/python/3.7.7/Python-3.7.7.tgz -o /opt/Python-3.7.7.tgz && \
    tar xzf /opt/Python-3.7.7.tgz --directory /opt

RUN dnf install -y \
        git \
        redis && \
        curl -L https://mirror.openshift.com/pub/openshift-v4/clients/ocp/latest/openshift-client-linux.tar.gz | tar xz -C /usr/bin/ oc

WORKDIR /opt/Python-3.7.7

RUN ./configure --enable-optimizations && \
    make altinstall && \
    ln -s /usr/local/bin/python3.7 /usr/local/bin/python && \
    python -m pip install -U pip && \
    mkdir --parent /opt/snafu

COPY . /opt/snafu

RUN python -m pip install -e /opt/snafu
