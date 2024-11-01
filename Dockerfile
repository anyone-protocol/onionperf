# Use a base image with Python 3 and necessary build tools
FROM debian:bookworm

ARG DEBIAN_FRONTEND=noninteractive

ARG ANON_ENV=live

WORKDIR /home/onionperf

# Install system dependencies
RUN apt-get update && apt-get install -y \
    automake \
    build-essential \
    cmake \
    git \
    libglib2.0-dev \
    libevent-dev \
    libigraph-dev \
    libssl-dev \
    zlib1g-dev \
    python3-dev \
    python3-venv \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get -y update \
    && echo "anon anon/terms boolean true" | debconf-set-selections \
    && apt-get -y install wget apt-transport-https \
    && . /etc/os-release \
    && wget -qO- https://deb.en.anyone.tech/anon.asc | tee /etc/apt/trusted.gpg.d/anon.asc \
    && echo "deb [signed-by=/etc/apt/trusted.gpg.d/anon.asc] https://deb.en.anyone.tech anon-$ANON_ENV-$VERSION_CODENAME main" > /etc/apt/sources.list.d/anon.list \
    && apt-get -y update \
    && apt-get -y install anon

# Clone and build TGen
RUN git clone https://github.com/shadow/tgen.git \
    && cd tgen \
    && mkdir build \
    && cd build \
    && cmake .. \
    && make

# Create and activate a Python virtual environment
RUN python3 -m venv /home/onionperf/venv
ENV PATH="/home/onionperf/venv/bin:$PATH"

# Copy and install OnionPerf
COPY . onionperf

RUN cd onionperf \
    && pip install --no-cache-dir -r requirements.txt \
    && python setup.py install \
    && mv docker-entrypoint.sh .. \
    && cd .. && rm -rf onionperf    

# Expose Listen and Connect Ports
EXPOSE 9510 9520

# Start OnionPerf when the container runs
ENTRYPOINT [ "sh", "docker-entrypoint.sh" ]
