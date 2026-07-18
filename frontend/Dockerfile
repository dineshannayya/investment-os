# ============================================================================
# Investment OS Frontend
# Ubuntu 24.04 LTS
# ============================================================================

FROM ubuntu:24.04

LABEL maintainer="Dinesh Annayya <dinesh.annayya@gmail.com>"
LABEL application="Investment OS Frontend"

ENV DEBIAN_FRONTEND=noninteractive
ENV NODE_ENV=development
ENV TZ=Asia/Kolkata

# ----------------------------------------------------------------------------
# Install NodeJS 22 LTS
# ----------------------------------------------------------------------------

RUN apt-get update && \
    apt-get install -y curl ca-certificates gnupg && \
    mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | \
    gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg && \
    echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] \
    https://deb.nodesource.com/node_22.x nodistro main" \
    > /etc/apt/sources.list.d/nodesource.list && \
    apt-get update && \
    apt-get install -y nodejs git vim nano && \
    rm -rf /var/lib/apt/lists/*

ENV PATH="/opt/investment-os/node_modules/.bin:${PATH}"

WORKDIR /opt/investment-os

COPY package*.json ./

RUN npm install

COPY . .

EXPOSE 3000

CMD ["npm","run","dev"]
