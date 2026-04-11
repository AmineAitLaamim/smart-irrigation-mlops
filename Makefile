.PHONY: env validate-env

# Generate .env from .env.example (only if it doesn't exist)
env:
	@bash scripts/init_env.sh

# Validate required env vars are present before starting containers
validate-env:
	@bash scripts/validate_env.sh
