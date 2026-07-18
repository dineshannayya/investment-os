# ============================================================================
# Investment OS Backend
# Ubuntu 24.04 LTS
# ============================================================================

FROM ubuntu:24.04

LABEL maintainer="Dinesh Annayya <dinesh.annayya@gmail.com>"
LABEL application="Investment OS Backend"

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV TZ=Asia/Kolkata

# ----------------------------------------------------------------------------
# Install OS Packages
# ----------------------------------------------------------------------------

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    git \
    curl \
    wget \
    unzip \
    vim \
    nano \
    ca-certificates \
    pkg-config \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# ----------------------------------------------------------------------------
# Working Directory
# ----------------------------------------------------------------------------

WORKDIR /opt/investment-os

# ----------------------------------------------------------------------------
# Python Virtual Environment
# ----------------------------------------------------------------------------

RUN python3 -m venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH"

# ----------------------------------------------------------------------------
# Upgrade pip
# ----------------------------------------------------------------------------

RUN pip install --upgrade pip setuptools wheel

# ----------------------------------------------------------------------------
# Install Python Dependencies
# ----------------------------------------------------------------------------

COPY requirements/base.txt requirements/

RUN pip install -r requirements/base.txt

# ----------------------------------------------------------------------------
# Copy Source
# ----------------------------------------------------------------------------

COPY . .

# ----------------------------------------------------------------------------
# Expose API
# ----------------------------------------------------------------------------

EXPOSE 8000

# ----------------------------------------------------------------------------
# Default Command
# ----------------------------------------------------------------------------

CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000","--reload"]
