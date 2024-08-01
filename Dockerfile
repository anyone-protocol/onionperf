# Use a base image with Python 3 and necessary build tools
FROM debian:bookworm

ARG DEBIAN_FRONTEND=noninteractive

ARG ANON_ENV=live

# Install system dependencies
RUN apt-get update && apt-get install -y \
    cron \
    automake \
    wget \
    build-essential \
    cmake \
    git \
    libglib2.0-dev \
    libevent-dev \
    libigraph-dev \
    libssl-dev \
    zlib1g-dev \
    python3-dev \
    python3-venv\
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /home/onionperf

# Clone and build Anon
RUN git clone https://github.com/ATOR-Development/ator-protocol.git \
    && cd ator-protocol \
    && ./scripts/ci/update-env.sh ${ANON_ENV} \
    && ./autogen.sh \
    && ./configure --disable-asciidoc \
    && make

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
    && python setup.py install

# Expose Listen and Connect Ports
EXPOSE 9510 9520

# Start OnionPerf when the container runs
CMD [ "onionperf", "measure", "--tgen", "tgen/build/src/tgen", "--tor", "ator-protocol/src/app/anon", "--tgen-listen-port", "9510", "--tgen-connect-port", "9520" ]
