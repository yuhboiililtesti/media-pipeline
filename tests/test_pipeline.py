#!/usr/bin/env python3
import os, sys, json

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

def test_structure():
    assert os.path.exists(f"{REPO}/discovery/engine.py")
    assert os.path.exists(f"{REPO}/safeguards/rules.json")
    assert os.path.exists(f"{REPO}/config.yaml")
    assert os.path.exists(f"{REPO}/.env.example")
    for s in ["anti-dupe.py", "auto-dedup.py", "complete-media.py", "torrent-doctor.sh", "protect-20tb.sh"]:
        assert os.path.exists(f"{REPO}/scripts/{s}"), f"Missing: {s}"

def test_python_syntax():
    import py_compile
    for dirpath, _, files in os.walk(REPO):
        for f in files:
            if f.endswith('.py') and 'test_' not in f:
                py_compile.compile(f"{dirpath}/{f}", doraise=True)

def test_config():
    with open(f"{REPO}/safeguards/rules.json") as f:
        rules = json.load(f)
    assert "never_add" in rules
    assert "max_per_day" in rules

def test_env_example():
    with open(f"{REPO}/.env.example") as f:
        content = f.read()
    for key in ["TMDB_KEY", "RADARR_API_KEY", "MEDIA_20TB"]:
        assert key in content

def test_no_hardcoded_keys():
    import re
    for dirpath, _, files in os.walk(REPO):
        if '.git' in dirpath:
            continue
        for f in files:
            if f.endswith(('.py', '.sh', '.md')):
                with open(f"{dirpath}/{f}") as fh:
                    content = fh.read()
                assert "e7746c26" not in content, f"Key in {f}"
                assert "Charmander34ee" not in content, f"Password in {f}"

if __name__ == "__main__":
    test_structure()
    test_python_syntax()
    test_config()
    test_env_example()
    test_no_hardcoded_keys()
    print("All tests passed")
