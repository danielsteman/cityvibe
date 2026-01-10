#!/bin/bash
# Encrypt .env file to .env.encrypted using SOPS

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found"
    echo "💡 Create .env from .env.example first: cp .env.example .env"
    exit 1
fi

if [ ! -f ".sops.yaml" ]; then
    echo "❌ Error: .sops.yaml not found"
    echo "💡 Configure SOPS first (see docs/SOPS.md)"
    exit 1
fi

# Check for Age key file and set environment variable if found
if [ -f "$HOME/.sops-age-key" ]; then
    export SOPS_AGE_KEY_FILE="$HOME/.sops-age-key"
fi

echo "🔐 Encrypting .env to .env.encrypted..."

# Use explicit dotenv output type for .env files
sops -e --output-type dotenv .env > .env.encrypted

if [ $? -eq 0 ]; then
    echo "✅ Successfully encrypted .env to .env.encrypted"
    echo "💡 You can now commit .env.encrypted to git"
    echo "⚠️  Remember: Never commit the unencrypted .env file"
else
    echo "❌ Encryption failed"
    exit 1
fi
