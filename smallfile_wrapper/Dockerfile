FROM centos/tools

RUN yum install git epel-release -y
RUN yum install python2-pip python2-numpy scipy python2-configparser python2-redis -y
RUN pip install --upgrade pip
RUN pip install elasticsearch statistics
RUN git clone https://github.com/distributed-system-analysis/smallfile
RUN mv smallfile /opt/
RUN ln -sv /opt/smallfile/smallfile_cli.py /usr/local/bin/
RUN ln -sv /opt/smallfile/smallfile_rsptimes_stats.py /usr/local/bin/
RUN mkdir -pv /opt/snafu
# assumption: docker build -f smallfile_wrapper/Dockerfile .
COPY . /opt/snafu/
