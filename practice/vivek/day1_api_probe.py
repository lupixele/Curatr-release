# PRACTICE — NOT REFERENCE DATA
# Day 1: Setup, Environment, and Safe API Probe
# Goal: Verify Python env and TMDB_TOKEN configuration without leaking secrets.

import os
import sys

# Verify token handling safely without exposing secrets
token = os.environ.get("TMDB_TOKEN", "mock-token-practice")
is_real_token = token != "mock-token-practice" and len(token) > 10

print(f"Python version: {sys.version.split()[0]}")
print(f"TMDB_TOKEN status: {'Configured (masked)' if is_real_token else 'Using mock token for practice'}")

# Fictional simulation of safe request headers and status handling
mock_headers = {"Authorization": f"Bearer {'*' * 8}", "accept": "application/json"}
print(f"Auth header configured safely: {mock_headers['Authorization']}")
print("Environment probe successful.")
