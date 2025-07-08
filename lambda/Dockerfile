FROM python:3.12.0-slim-bullseye

# Install system deps + Mullvad repo and CLI
# Install system deps + Mullvad repo and CLI (prevent services from auto-starting)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        apt-transport-https \
        gnupg \
        policykit-1 \
    && curl -fsSLo /usr/share/keyrings/mullvad-keyring.asc \
         https://repository.mullvad.net/deb/mullvad-keyring.asc \
    && echo "deb [signed-by=/usr/share/keyrings/mullvad-keyring.asc \
              arch=$(dpkg --print-architecture)] \
              https://repository.mullvad.net/deb/stable stable main" \
         > /etc/apt/sources.list.d/mullvad.list \
    \
    # Prevent any package from attempting to start daemons
    && printf '#!/bin/sh\nexit 101' > /usr/sbin/policy-rc.d \
    && chmod +x /usr/sbin/policy-rc.d \
    \
    # Now install Mullvad VPN CLI
    && apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
         mullvad-vpn \
    \
    # Clean up
    && rm -f /usr/sbin/policy-rc.d \
    && rm -rf /var/lib/apt/lists/*


# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code and entrypoint
COPY . .
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Expose the application port
ENV PORT=${PORT:-8080}

# Use the entrypoint script
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# Default CMD is defined in entrypoint
CMD []