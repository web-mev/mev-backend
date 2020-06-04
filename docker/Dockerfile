FROM debian:stretch

# Basic setup
RUN apt-get update \
    && apt-get install -y \
    build-essential \
    apt-transport-https \
    ca-certificates \
    gnupg2 \
    software-properties-common \
    zlib1g-dev \
    libssl-dev \
    libncurses5-dev \
    libreadline-dev \
    libbz2-dev \
    libffi-dev \
    liblzma-dev \
    libsqlite3-dev \
    libpq-dev \
    wget \
    supervisor \
    nano \
    git \
    curl \
    pkg-config \
    procps

# Docker in Docker!!
RUN curl -fsSL https://download.docker.com/linux/debian/gpg | apt-key add - && \
    add-apt-repository \
    "deb [arch=amd64] https://download.docker.com/linux/debian \
    $(lsb_release -cs) \
    stable" && \
    apt-get update && \
    apt-get install -y docker-ce

# Install postgresql:
RUN echo "deb http://apt.postgresql.org/pub/repos/apt/ stretch-pgdg main" > /etc/apt/sources.list.d/pgdg.list && \
  wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add && \
  apt-get update && \
  apt-get install -y postgresql-12

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

RUN ls /opt

# Pull the source code:
RUN git clone https://github.com/qbrc-cnap/mev-backend /www

# Install the python dependencies, as given from the repository:
RUN pip3 install -U pip && \
    pip3 install --no-cache-dir -r /www/requirements.txt

# Copy over the supervisor conf files:
#COPY gunicorn.conf /etc/supervisor/conf.d/
RUN cp /www/supervisor/redis.conf /etc/supervisor/conf.d/ && \
    cp /www/supervisor/celery_worker.conf /etc/supervisor/conf.d/ && \
    cp /www/supervisor/celery_beat.conf /etc/supervisor/conf.d/ && \
    cp /www/supervisor/supervisord.conf /etc/supervisor/supervisord.conf

# setup some static environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

# create the mev user
RUN addgroup --system mev && adduser --system --group mev

# Give that user ownership of the code directory and the logging directory
RUN mkdir /var/log/mev && \
    chown -R mev:mev /www /var/log/mev /var/log/supervisor /etc/supervisor/conf.d

# Give ownership and add execution permissions for startup script
RUN chown mev:mev /www/docker/startup.sh && chmod +x /www/docker/startup.sh

# switch to the mev user
USER mev


ENTRYPOINT ["/www/docker/startup.sh"]
