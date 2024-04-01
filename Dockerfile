# Use a base image with Python 3 and necessary build tools
FROM debian:bookworm

ARG DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
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

# Create a non-root user for running OnionPerf
#RUN #useradd -ms /bin/bash onionperf
#RUN chown -R onionperf:onionperf /home/onionperf

# Switch to the non-root user
#USER onionperf
WORKDIR /home/onionperf

# Clone and build Anon
RUN git clone https://github.com/ATOR-Development/ator-protocol.git \
    && cd ator-protocol \
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

# Clone and install OnionPerf
COPY . onionperf

RUN cd onionperf \
    && pip install --no-cache-dir -r requirements.txt \
    && python setup.py install

# Set environment variables and working directory
ENV TOR_PATH="/home/onionperf/ator-protocol/src/app/anon"
ENV TGEN_PATH="/home/onionperf/tgen/build/src/tgen"
WORKDIR /home/onionperf

# Expose ORPort, DirPort
EXPOSE 9510 9520
# Start OnionPerf when the container runs
CMD ["onionperf", "measure", "--onion-only", "--tgen", "/home/onionperf/tgen/build/src/tgen", "--tor", "/home/onionperf/ator-protocol/src/app/anon", "--tgen-listen-port", "9510", "--tgen-connect-port", "9520"]