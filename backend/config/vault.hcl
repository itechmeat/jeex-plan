# Development Vault Configuration - Simpler setup
storage "file" {
  path = "/vault/data"
}

listener "tcp" {
  address     = "0.0.0.0:8200"
  tls_disable = "true"
}

api_addr = "http://0.0.0.0:8200"
cluster_addr = "http://0.0.0.0:8201"

# Disable mlock for development
disable_mlock = true

# Enable UI for development
ui = true

# Set default lease TTLs
default_lease_ttl = "768h"
max_lease_ttl = "768h"