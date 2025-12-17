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

echo "🔓 Decrypting .env.encrypted to .env..."

sops -d .env.encrypted > .env

if [ $? -eq 0 ]; then
    echo "✅ Successfully decrypted .env.encrypted to .env"
    echo "⚠️  Remember: .env is in .gitignore and should never be committed"
else
    echo "❌ Decryption failed"
    echo "💡 Make sure your SOPS key is set up correctly (see docs/SOPS.md)"
    exit 1
fi
