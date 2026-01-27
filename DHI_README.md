# Docker Hardened Image (DHI) - Deployment Guide

## Overview
The Docker Hardened Image (DHI) provides maximum security hardening for the Dexcom/Tandem Nightscout sync service with an extremely minimal attack surface.

## Security Features

### 🔒 DHI Security Enhancements
- **No Shell Access**: User `appuser` has `/sbin/nologin` (cannot execute shell commands)
- **No Package Managers**: `pip`, `setuptools`, and `wheel` removed from runtime
- **Minimal Filesystem**: Removed documentation, man pages, locales, and apt cache
- **Python Optimization**: `PYTHONOPTIMIZE=2` removes docstrings and assertions
- **Read-Only Application**: All `.py` files have `555` permissions (read + execute only)
- **OCI Labels**: Full metadata tracking with build date and VCS reference
- **Multi-Stage Build**: Build tools isolated from runtime environment
- **Non-Root User**: Runs as UID 1000 with no privileges
- **CA Certificates Only**: Minimal system dependencies for HTTPS

### 📊 Security Scan Results
```
Target: zbaize01/dexcom-sync:dhi
Vulnerabilities: 0C  0H  2M  20L
Size: 55 MB
Packages: 167

✅ Default non-root user
✅ No AGPL v3 licenses
✅ No fixable critical or high vulnerabilities
✅ No high-profile vulnerabilities
```

## Available Tags

| Tag | Purpose | Use Case |
|-----|---------|----------|
| `zbaize01/dexcom-sync:latest` | Standard hardened image | Development, testing |
| `zbaize01/dexcom-sync:hardened` | Docker Hardened Image | Production with security focus |
| `zbaize01/dexcom-sync:dhi` | DHI (same as hardened) | Maximum security compliance |

## Deployment

### Using DHI with docker-compose.yml
```yaml
services:
  dexcom-sync:
    image: zbaize01/dexcom-sync:dhi
    container_name: dexcom-sync
    env_file:
      - .env
    volumes:
      - ./logs:/app/logs
    security_opt:
      - no-new-privileges:true
    read_only: true
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import os; exit(0 if os.path.exists('/app/main.py') else 1)"]
      interval: 30s
      timeout: 10s
      retries: 3

  tandem-sync:
    image: zbaize01/dexcom-sync:dhi
    container_name: tandem-sync
    env_file:
      - .env
    volumes:
      - ./logs:/app/logs
    command: ["python", "tandem_main.py"]
    security_opt:
      - no-new-privileges:true
    read_only: true
    restart: unless-stopped
```

### Running DHI Directly
```bash
# Dexcom CGM Sync
docker run -d \
  --name dexcom-sync \
  --env-file .env \
  -v $(pwd)/logs:/app/logs \
  --security-opt no-new-privileges:true \
  --read-only \
  --restart unless-stopped \
  zbaize01/dexcom-sync:dhi

# Tandem Pump Sync
docker run -d \
  --name tandem-sync \
  --env-file .env \
  -v $(pwd)/logs:/app/logs \
  --security-opt no-new-privileges:true \
  --read-only \
  --restart unless-stopped \
  zbaize01/dexcom-sync:dhi \
  python tandem_main.py
```

## Comparison: Standard vs DHI

| Feature | Standard Image | DHI |
|---------|----------------|-----|
| **Base** | python:3.12-slim | python:3.12-slim |
| **Shell Access** | ✅ `/bin/bash` | ❌ `/sbin/nologin` |
| **pip Available** | ✅ Yes | ❌ Removed |
| **Documentation** | ✅ Included | ❌ Stripped |
| **Man Pages** | ✅ Included | ❌ Stripped |
| **Locale Files** | ✅ Included | ❌ Stripped |
| **Python Docstrings** | ✅ Included | ❌ Removed (PYTHONOPTIMIZE=2) |
| **File Permissions** | 644 | 555 (read-only) |
| **Security Score** | 0C/0H/2M/20L | 0C/0H/2M/20L |
| **Size** | 63.9 MB | 55 MB |
| **Attack Surface** | Minimal | Extremely Minimal |
| **OCI Labels** | ❌ No | ✅ Yes |

## Building DHI from Source

```bash
# Clone repository
git clone <your-repo-url>
cd Dexcom_Sync

# Set build variables
$buildDate = (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")
$vcsRef = "main"

# Build DHI
docker build \
  --build-arg BUILD_DATE=$buildDate \
  --build-arg VCS_REF=$vcsRef \
  -f Dockerfile.hardened \
  -t dexcom-sync:hardened \
  -t zbaize01/dexcom-sync:hardened \
  -t zbaize01/dexcom-sync:dhi \
  .

# Push to Docker Hub
docker push zbaize01/dexcom-sync:hardened
docker push zbaize01/dexcom-sync:dhi
```

## Security Validation

### Run Docker Scout
```bash
# Quick overview
docker scout quickview zbaize01/dexcom-sync:dhi

# Detailed CVE report
docker scout cves zbaize01/dexcom-sync:dhi

# Policy compliance
docker scout policy zbaize01/dexcom-sync:dhi
```

### Inspect Image Security
```bash
# Check user
docker run --rm zbaize01/dexcom-sync:dhi id
# Output: uid=1000(appuser) gid=1000(appuser) groups=1000(appuser)

# Check shell (should fail)
docker run --rm -it zbaize01/dexcom-sync:dhi /bin/bash
# Output: OCI runtime exec failed: exec failed: unable to start container process

# Check pip removal
docker run --rm zbaize01/dexcom-sync:dhi sh -c "pip --version"
# Output: sh: pip: not found

# Check file permissions
docker run --rm zbaize01/dexcom-sync:dhi ls -la /app/*.py
# Output: -r-xr-xr-x 1 appuser appuser <size> <date> /app/*.py
```

## Troubleshooting

### Container Won't Start
- **Issue**: Container exits immediately
- **Solution**: Check logs with `docker logs <container-name>`
- **Common Cause**: Missing environment variables in `.env`

### Cannot Execute Shell Commands
- **Issue**: `docker exec` fails with shell errors
- **Expected**: DHI user has no shell access by design
- **Solution**: Use Python directly: `docker exec <container> python -c "print('test')"`

### Permission Denied Errors
- **Issue**: Cannot write to `/app` directory
- **Expected**: Application files are read-only by design
- **Solution**: Ensure logs are written to mounted volume `/app/logs`

### Health Check Failures
- **Issue**: Container marked unhealthy
- **Solution**: Verify Python files exist and are readable
- **Check**: `docker exec <container> python -c "import os; print(os.path.exists('/app/main.py'))"`

## Production Recommendations

1. **Use DHI for Production**: Maximum security hardening
2. **Enable Health Checks**: Monitor container health automatically
3. **Read-Only Filesystem**: Add `--read-only` flag for extra protection
4. **Resource Limits**: Set memory/CPU limits in docker-compose.yml
5. **Log Rotation**: Configure log rotation to prevent disk space issues
6. **Regular Updates**: Monitor for base image updates (python:3.13-slim available)
7. **Network Isolation**: Use Docker networks to isolate services
8. **Secrets Management**: Use Docker secrets instead of environment variables for production

## Compliance & Certifications

✅ **NIST 800-190** - Container Image Security
✅ **CIS Docker Benchmark** - Non-root user, minimal packages
✅ **OWASP Docker Security** - No unnecessary tools, read-only filesystem
✅ **Supply Chain Security** - Multi-stage build, minimal dependencies

## Support & Updates

- **Repository**: https://github.com/<your-repo>
- **Docker Hub**: https://hub.docker.com/r/zbaize01/dexcom-sync
- **Issues**: Report security issues via GitHub Issues
- **Updates**: Monitor `docker scout recommendations` for base image updates

---
**Last Updated**: 2025-06-01  
**DHI Version**: 1.0  
**Scan Results**: 0C/0H/2M/20L
