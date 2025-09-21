# HashiCorp Vault - Minimal Configuration for JEEX Plan

# Storage backend
storage "file" {
  path = "/vault/data"
}

# HTTP listener
listener "tcp" {
  address = "0.0.0.0:8200"
  tls_disable = 1
}

# UI
ui = true

# Disable mlock for containerized environment
disable_mlock = true

# Cluster configuration
cluster_addr = "http://vault:8201"
api_addr = "http://0.0.0.0:8200"

# Log level
log_level = "INFO"