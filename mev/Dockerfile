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
    netcat \
    procps

# Docker in Docker!!
RUN curl -fsSL https://download.docker.com/linux/debian/gpg | apt-key add - && \
    add-apt-repository \
    "deb [arch=amd64] https://download.docker.com/linux/debian \
    $(lsb_release -cs) \
    stable" && \
    apt-get update && \
    apt-get install -y docker-ce

# Install Python 3.7.6:
RUN mkdir /opt/software && \
  cd /opt/software && \
  wget https://www.python.org/ftp/python/3.7.6/Python-3.7.6.tgz && \
  tar -xzf Python-3.7.6.tgz && \
  cd Python-3.7.6 && \
  ./configure && \
  make && \
  make install

# Copy the source files over
ADD ./api /www/api
ADD ./resource_types /www/resource_types
ADD ./helpers /www/helpers
ADD ./mev /www/mev
ADD ./startup.sh /www/startup.sh
ADD ./manage.py /www/manage.py
ADD ./requirements.txt /www/requirements.txt
COPY ./supervisor/celery_worker.conf /etc/supervisor/conf.d/
COPY ./supervisor/celery_beat.conf /etc/supervisor/conf.d/
COPY ./supervisor/supervisord.conf /etc/supervisor/supervisord.conf

# Install the python dependencies, as given from the repository:
RUN pip3 install -U pip && \
    pip3 install --no-cache-dir -r /www/requirements.txt

# setup some static environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

# create the mev user
#RUN addgroup --system mev && adduser --system --group mev
#RUN usermod -aG docker mev

# Give that user ownership of the code directory and the logging directory
RUN mkdir /var/log/mev && \
    mkdir /www/static/
    #mkdir /www/static/ && \
    #chown -R mev:mev /www /var/log/mev /var/log/supervisor /etc/supervisor/conf.d

# Give ownership and add execution permissions for startup script
#RUN chown mev:mev /www/startup.sh && chmod +x /www/startup.sh

# switch to the mev user
#USER mev

ENTRYPOINT ["/www/startup.sh"]
