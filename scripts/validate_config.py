#!/usr/bin/env python3
"""Validate config.yaml and .env at startup. Run before pipeline starts."""
import os, sys, yaml
from pathlib import Path

REQUIRED_ENV_VARS = [
    "TMDB_KEY", "RADARR_API_KEY", "SONARR_API_KEY",
    "PROWLARR_API_KEY", "PLEX_TOKEN", "QBIT_PASSWORD"
]

REQUIRED_PATHS = [
    "media_20tb", "media_8tb", "downloads", "encode_cache"
]

REQUIRED_SERVICES = [
    "radarr", "sonarr", "prowlarr", "plex", "qbit_overflow"
]

def validate_config(config_path: str = "config.yaml") -> list[str]:
    """Validate config.yaml structure. Returns list of errors."""
    errors = []
    
    if not os.path.exists(config_path):
        return [f"Config file not found: {config_path}"]
    
    try:
        with open(config_path) as f:
            cfg = yaml.safe_load(f)
    except yaml.YAMLError as e:
        return [f"Invalid YAML in {config_path}: {e}"]
    
    if not isinstance(cfg, dict):
        return ["Config root must be a dictionary"]
    
    # Check required sections
    for section in ["pipeline", "storage", "paths", "services", "timers"]:
        if section not in cfg:
            errors.append(f"Missing config section: {section}")
    
    # Check paths
    if "paths" in cfg:
        for p in REQUIRED_PATHS:
            if p not in cfg.get("paths", {}):
                errors.append(f"Missing path: {p}")
    
    # Check services
    if "services" in cfg:
        for s in REQUIRED_SERVICES:
            if s not in cfg.get("services", {}):
                errors.append(f"Missing service config: {s}")
    
    # Check storage thresholds
    if "storage" in cfg:
        for drive in cfg.get("storage", {}).get("drives", []):
            if "warn_pct" not in drive:
                errors.append(f"Drive {drive.get('path', '?')} missing warn_pct")
    
    return errors

def validate_env(env_path: str = ".env") -> list[str]:
    """Validate .env has required variables. Returns list of errors."""
    errors = []
    
    if not os.path.exists(env_path):
        return [f"Env file not found: {env_path} (copy .env.example)"]
    
    with open(env_path) as f:
        content = f.read()
    
    for var in REQUIRED_ENV_VARS:
        if f"{var}=" not in content or f"{var}=your_" in content.lower():
            errors.append(f"Missing or unset env var: {var}")
    
    return errors

def main() -> int:
    all_errors = validate_config() + validate_env()
    
    if all_errors:
        print("CONFIGURATION ERRORS:")
        for e in all_errors:
            print(f"  - {e}")
        print(f"\n{len(all_errors)} error(s) found. Fix before starting pipeline.")
        return 1
    
    print("Configuration valid. Pipeline ready.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
