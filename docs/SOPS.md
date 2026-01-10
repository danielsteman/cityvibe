# SOPS Secrets Management

This project uses [SOPS](https://github.com/getsops/sops) (Secrets Operations) to encrypt and manage `.env` files containing sensitive configuration like database passwords and API keys.

## Can Other Contributors Use `.env.encrypted`?

**Yes, but they need to be added first.** Here's how it works:

1. **Each contributor** generates their own Age keypair
2. **Their public key** is added to `.sops.yaml` (alongside existing keys)
3. **The `.env.encrypted` file is re-encrypted** with all contributors' keys
4. **All contributors can then decrypt** the file using their own private key

**Important**: Simply adding a key to `.sops.yaml` isn't enough - the encrypted file must be re-encrypted with all keys. See [Adding Team Members](#adding-team-members) below for the complete process.

## Why SOPS?

- **Version Control Safe**: Encrypted secrets can be committed to git
- **Team Collaboration**: Multiple team members can decrypt with their own keys
- **Audit Trail**: All changes to secrets are tracked in git history
- **Simple**: Works with Age (modern) or GPG (traditional) encryption

## Setup

### 1. Install SOPS

**macOS:**

```bash
brew install sops
```

**Linux:**

```bash
# Using the official binary
wget https://github.com/getsops/sops/releases/latest/download/sops-v3.8.0.linux
sudo mv sops-v3.8.0.linux /usr/local/bin/sops
sudo chmod +x /usr/local/bin/sops
```

**Other platforms:** See [SOPS Installation](https://github.com/getsops/sops#installation)

### 2. Generate Age Keypair (Recommended)

Age is simpler and faster than GPG:

```bash
# Generate a keypair
age-keygen -o ~/.sops-age-key

# Export your public key (you'll add this to .sops.yaml)
age-keygen -y ~/.sops-age-key
```

**Important**: Keep `~/.sops-age-key` secure and backed up. This is your private key.

### 3. Configure SOPS

1. Copy your public key from step 2
2. Edit `.sops.yaml` and replace `REPLACE_WITH_YOUR_AGE_PUBLIC_KEY` with your public key
3. Commit `.sops.yaml` to the repository

### 4. Encrypt Your .env File

```bash
# Encrypt .env to .env.encrypted
sops -e .env > .env.encrypted

# Or use the helper script
./scripts/encrypt-env.sh
```

The encrypted file (`.env.encrypted`) can be safely committed to git.

## Usage

### Decrypting for Local Development

```bash
# Decrypt .env.encrypted to .env
sops -d .env.encrypted > .env

# Or use the helper script
./infrastructure/scripts/decrypt-env.sh
```

**Note**: The decrypted `.env` file is in `.gitignore` and should never be committed.

### Editing Encrypted Files

You can edit encrypted files directly:

```bash
# Edit .env.encrypted (SOPS will decrypt, let you edit, then re-encrypt)
sops .env.encrypted
```

### Adding Team Members

To allow team members to decrypt secrets, you need to:

1. **Each team member generates their own Age keypair:**

   ```bash
   age-keygen -o ~/.sops-age-key
   age-keygen -y ~/.sops-age-key  # Share this public key
   ```

2. **Add all public keys to `.sops.yaml`** (one per line):

   ```yaml
   creation_rules:
     - path_regex: \.env(\.encrypted)?$
       age: >-
         age1yourkeyhere...
         age1teammate1keyhere...
         age1teammate2keyhere...
   ```

3. **Re-encrypt the `.env.encrypted` file** with all keys:

   ```bash
   # Edit the encrypted file (SOPS will use all keys from .sops.yaml)
   sops .env.encrypted
   # Or re-encrypt from decrypted .env:
   sops -e .env > .env.encrypted
   ```

4. **Commit the updated `.sops.yaml` and `.env.encrypted`** to git.

**Important**: After adding new keys, you must re-encrypt the file so it's encrypted with all team members' keys. Simply editing `.sops.yaml` isn't enough - the encrypted file itself needs to be re-encrypted.

**With GPG** (alternative):

```yaml
creation_rules:
  - path_regex: \.env(\.encrypted)?$
    pgp: >-
      YOUR_FINGERPRINT
      TEAMMATE_FINGERPRINT
```

### CI/CD Integration

For CI/CD pipelines, you'll need to provide the decryption key:

**GitHub Actions Example:**

```yaml
- name: Decrypt secrets
  env:
    SOPS_AGE_KEY: ${{ secrets.SOPS_AGE_KEY }}
  run: |
    sops -d .env.encrypted > .env
```

Store the private key (`~/.sops-age-key` contents) as a GitHub secret.

## Helper Scripts

We provide helper scripts in `infrastructure/scripts/`:

- `encrypt-env.sh` - Encrypt `.env` to `.env.encrypted`
- `decrypt-env.sh` - Decrypt `.env.encrypted` to `.env`
- `add-contributor.sh` - Add a new contributor's Age public key to `.sops.yaml`

### Adding a New Contributor

Use the helper script to add a contributor:

```bash
# Contributor shares their public key (they run: age-keygen -y ~/.sops-age-key)
./infrastructure/scripts/add-contributor.sh alice age1l3at9ug0aeew6245j4zy47ayvnejnv8vst2e9qe89t8n753zvcmsc0tlwx

# Then re-encrypt with all keys
sops .env.encrypted  # Edit and save, or:
sops -e .env > .env.encrypted

# Commit the changes
git add .sops.yaml .env.encrypted
git commit -m "Add alice to SOPS configuration"
```

## Workflow

1. **Initial Setup**: Create `.env` from `.env.example`, add your secrets
2. **Encrypt**: Run `sops -e .env > .env.encrypted`
3. **Commit**: Commit `.env.encrypted` (never commit `.env`)
4. **Team**: Team members decrypt with `sops -d .env.encrypted > .env`
5. **Updates**: Edit encrypted file directly with `sops .env.encrypted`

## Security Best Practices

- ✅ **DO**: Commit encrypted files (`.env.encrypted`)
- ✅ **DO**: Keep your private key secure and backed up
- ✅ **DO**: Use different keys for different environments (dev/staging/prod)
- ❌ **DON'T**: Commit unencrypted `.env` files
- ❌ **DON'T**: Share private keys via insecure channels
- ❌ **DON'T**: Store private keys in the repository

## Troubleshooting

### "no decryption key available"

Make sure:

1. Your private key is at `~/.sops-age-key` (for Age) or imported to GPG
2. Your public key is in `.sops.yaml`
3. You're using the correct key format

### "failed to get the data key required to decrypt"

The encrypted file was created with a different key. You need to be added to the `.sops.yaml` configuration.

## Alternative: GPG

If you prefer GPG over Age:

1. Generate GPG key: `gpg --full-generate-key`
2. Get fingerprint: `gpg --list-secret-keys --keyid-format LONG`
3. Update `.sops.yaml` to use `pgp` instead of `age`
4. Encrypt: `sops -e --pgp YOUR_FINGERPRINT .env > .env.encrypted`

## References

- [SOPS Documentation](https://github.com/getsops/sops)
- [Age Encryption](https://github.com/FiloSottile/age)
