FROM debian:stretch

RUN apt-get update \
    && apt-get install -y \
    build-essential \
    python3-dev \
    python3-pip \
    wget

RUN mkdir /opt/software
ADD upload.py /opt/software/

ENTRYPOINT ["/bin/bash"]
