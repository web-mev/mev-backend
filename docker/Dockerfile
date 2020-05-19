FROM debian:stretch

# Basic setup
RUN apt-get update \
    && apt-get install -y \
    build-essential \
    zlib1g-dev \
    libssl-dev \
    libncurses5-dev \
    libreadline-dev \
    libbz2-dev \
    libffi-dev \
    libsqlite3-dev \
    wget \
    supervisor \
    nano \
    git \
    curl \
    pkg-config \
    procps

# Install Python 3.7.6:
RUN mkdir /opt/software && \
  cd /opt/software && \
  wget https://www.python.org/ftp/python/3.7.6/Python-3.7.6.tgz && \
  tar -xzf Python-3.7.6.tgz && \
  cd Python-3.7.6 && \
  ./configure && \
  make && \
  make install

# Install redis for queueing and cache
RUN curl -o /tmp/redis-stable.tar.gz http://download.redis.io/redis-stable.tar.gz \
  && cd /tmp \
  && tar -zxf redis-stable.tar.gz \
  && cd redis-stable \
  && make \
  && make install \
  && cp redis.conf /etc/redis.conf

# Pull the source code:
RUN git clone https://github.com/qbrc-cnap/mev-backend /tmp/mev

# Install the python dependencies, as given from the repository:
RUN pip3 install -U pip
RUN pip3 install --no-cache-dir -r /tmp/mev/requirements.txt

RUN rm -rf /tmp/mev

ENTRYPOINT ["/bin/bash"]
