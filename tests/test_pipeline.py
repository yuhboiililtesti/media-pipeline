#!/usr/bin/env python3
import os, sys, json, re

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

def test_structure():
    assert os.path.exists(f"{REPO}/discovery/engine.py"), "Missing discovery/engine.py"
    assert os.path.exists(f"{REPO}/safeguards/rules.json"), "Missing safeguards/rules.json"
    assert os.path.exists(f"{REPO}/config.yaml"), "Missing config.yaml"
    assert os.path.exists(f"{REPO}/.env.example"), "Missing .env.example"
    for s in ["anti-dupe.py", "auto-dedup.py", "complete-media.py", "torrent-doctor.sh"]:
        assert os.path.exists(f"{REPO}/scripts/{s}"), f"Missing: {s}"
    return True

def test_python_syntax():
    import py_compile
    for dirpath, _, files in os.walk(REPO):
        if '.git' in dirpath:
            continue
        for f in files:
            if f.endswith('.py') and 'test_' not in f:
                py_compile.compile(f"{dirpath}/{f}", doraise=True)
    return True

def test_config():
    with open(f"{REPO}/safeguards/rules.json") as f:
        rules = json.load(f)
    assert isinstance(rules, dict), "rules.json is not valid JSON"
    return True

def test_env_example():
    with open(f"{REPO}/.env.example") as f:
        content = f.read()
    for key in ["TMDB_KEY", "RADARR_API_KEY", "MEDIA_20TB"]:
        assert key in content, f"Missing key in .env.example: {key}"
    return True

def test_no_secrets():
    secret_patterns = [
        "YOUR_RADARR_API_KEY",
        "YOUR_SONARR_API_KEY",
        "YOUR_PROWLARR_API_KEY",
        "YOUR_QBIT_PASSWORD",
    ]
    for dirpath, _, files in os.walk(REPO):
        if '.git' in dirpath or 'tests' in dirpath:
            continue
        for f in files:
            if f.endswith(('.py', '.sh', '.md', '.conf', '.json')):
                with open(f"{dirpath}/{f}") as fh:
                    content = fh.read()
                for pattern in secret_patterns:
                    if pattern in content:
                        raise AssertionError(f"Secret found in {f}: {pattern[:8]}...")
    return True

if __name__ == "__main__":
    results = []
    for name, func in [
        ("structure", test_structure),
        ("python syntax", test_python_syntax),
        ("config", test_config),
        ("env example", test_env_example),
        ("no secrets", test_no_secrets),
    ]:
        try:
            func()
            results.append(f"  PASS {name}")
        except Exception as e:
            results.append(f"  FAIL {name}: {e}")
    for r in results:
        print(r)
    failures = [r for r in results if "FAIL" in r]
    if failures:
        print(f"\n{failures} tests failed")
        exit(1)
    else:
        print("\nAll tests passed")

def test_config_validation():
    """Test that config validation catches real errors."""
    import tempfile, yaml
    
    # Valid config should pass
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump({
            "pipeline": {"mode": {"max_active_downloads": 50}},
            "storage": {"drives": [{"path": "/tmp", "warn_pct": 90}]},
            "paths": {"media_20tb": "/tmp", "media_8tb": "/tmp", "downloads": "/tmp", "encode_cache": "/tmp"},
            "services": {"radarr": {}, "sonarr": {}, "prowlarr": {}, "plex": {}, "qbit_overflow": {}},
            "timers": {"torrent_doctor": 5}
        }, f)
        tmp_path = f.name
    
    # Import and run
    sys.path.insert(0, f"{REPO}/scripts")
    from validate_config import validate_config
    errors = validate_config(tmp_path)
    os.unlink(tmp_path)
    assert len(errors) == 0, f"Valid config should have 0 errors, got: {errors}"
    
    # Missing config should fail
    errors = validate_config("/nonexistent/config.yaml")
    assert len(errors) > 0, "Missing config should produce errors"
