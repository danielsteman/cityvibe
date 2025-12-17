#!/bin/bash
# Helper script to add a new contributor's Age public key to SOPS configuration
# Usage: ./add-contributor.sh <contributor-name> <age-public-key>

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

if [ $# -lt 2 ]; then
    echo "Usage: $0 <contributor-name> <age-public-key>"
    echo ""
    echo "Example:"
    echo "  $0 alice age1l3at9ug0aeew6245j4zy47ayvnejnv8vst2e9qe89t8n753zvcmsc0tlwx"
    echo ""
    echo "The contributor should run: age-keygen -y ~/.sops-age-key"
    echo "and share their public key with you."
    exit 1
fi

CONTRIBUTOR_NAME="$1"
PUBLIC_KEY="$2"

# Validate the key format (should start with age1)
if [[ ! "$PUBLIC_KEY" =~ ^age1 ]]; then
    echo "❌ Error: Invalid Age public key format"
    echo "   Age public keys should start with 'age1'"
    exit 1
fi

if [ ! -f ".sops.yaml" ]; then
    echo "❌ Error: .sops.yaml not found"
    exit 1
fi

# Check if key already exists
if grep -q "$PUBLIC_KEY" .sops.yaml; then
    echo "⚠️  Warning: This public key already exists in .sops.yaml"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "➕ Adding contributor: $CONTRIBUTOR_NAME"
echo "🔑 Public key: $PUBLIC_KEY"
echo ""

# Add the key to .sops.yaml (before the closing quote)
# This is a simple approach - in production you might want more robust YAML editing
sed -i.bak "/age: >-$/a\\
      $PUBLIC_KEY  # $CONTRIBUTOR_NAME
" .sops.yaml

# Remove backup file
rm -f .sops.yaml.bak

echo "✅ Added $CONTRIBUTOR_NAME's public key to .sops.yaml"
echo ""
echo "📝 Next steps:"
echo "   1. Review the changes: git diff .sops.yaml"
echo "   2. Re-encrypt .env.encrypted with all keys:"
echo "      sops .env.encrypted"
echo "      (or: sops -e .env > .env.encrypted)"
echo "   3. Commit both files:"
echo "      git add .sops.yaml .env.encrypted"
echo "      git commit -m 'Add $CONTRIBUTOR_NAME to SOPS configuration'"
