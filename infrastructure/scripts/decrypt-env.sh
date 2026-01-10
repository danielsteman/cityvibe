#!/bin/bash
# Decrypt .env.encrypted to .env using SOPS

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

if [ ! -f ".env.encrypted" ]; then
    echo "❌ Error: .env.encrypted file not found"
    echo "💡 If this is your first time, create .env from .env.example"
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
elif [ -z "$SOPS_AGE_KEY_FILE" ] && [ -z "$SOPS_AGE_KEY" ]; then
    echo "⚠️  Warning: Age key file not found at ~/.sops-age-key"
    echo "💡 SOPS will look for keys in standard locations"
    echo "💡 You can set SOPS_AGE_KEY_FILE or SOPS_AGE_KEY environment variables"
fi

echo "🔓 Decrypting .env.encrypted to .env..."

# Use explicit dotenv input/output types to handle dotenv format files
sops -d --input-type dotenv --output-type dotenv .env.encrypted > .env

if [ $? -eq 0 ]; then
    echo "✅ Successfully decrypted .env.encrypted to .env"
    echo "⚠️  Remember: .env is in .gitignore and should never be committed"
else
    echo "❌ Decryption failed"
    echo "💡 Make sure your SOPS key is set up correctly:"
    echo "   1. Your Age private key is at ~/.sops-age-key, OR"
    echo "   2. Set SOPS_AGE_KEY_FILE or SOPS_AGE_KEY environment variable"
    echo "   3. Your public key is in .sops.yaml"
    echo "   See docs/SOPS.md for more details"
    exit 1
fi
