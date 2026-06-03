# Sue ↔ Monte Cristo PHP Bridge — containerized
# Runs in the SAME docker-in-WSL2 stack as SearXNG/Whoogle → inherits their permanence.
FROM php:8.3-cli-alpine

# tools the bridge is allowed to shell out to (git, curl, bash for worker repair)
RUN apk add --no-cache bash git curl docker-cli

WORKDIR /bridge
COPY bridge.php /bridge/bridge.php

# the bridge binds 0.0.0.0 INSIDE the container; only cloudflared (same network) reaches it
EXPOSE 8899
CMD ["php", "-S", "0.0.0.0:8899", "/bridge/bridge.php"]
