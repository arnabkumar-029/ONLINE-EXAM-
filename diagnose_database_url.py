# diagnose_database_url.py
"""
SAFE Diagnostic Script for DATABASE_URL parsing and connectivity.

SECURITY MANDATES:
- NEVER logs, displays, or exposes the database password.
- NEVER logs, displays, or exposes the full raw DATABASE_URL.
- NEVER logs or displays connection credentials or secrets.
- Extracts ONLY: scheme, username, hostname, port, database name.
- Tests connectivity safely using SELECT 1.
"""

import os
import sys
import re
from dotenv import load_dotenv

# Load local environment if present
load_dotenv()

from urllib.parse import urlparse
from sqlalchemy.engine import make_url

import db


def safe_mask_string(val: str | None) -> str:
    if not val:
        return "<none>"
    return "******"


def analyze_database_url():
    print("=" * 65)
    print("      DATABASE_URL SAFE DIAGNOSTIC & TRACE REPORT")
    print("=" * 65)

    raw_env_url = os.getenv("DATABASE_URL")
    if not raw_env_url:
        print("\n[INFO] DATABASE_URL is not set in the local environment.")
        print("       (It is configured on the Render Web Service).")
        print("\n[SIMULATION / TRACE ANALYSIS]")
        print("Running diagnostic on the error pattern reported from Render:")
        print("Error observed: host name 'jANA]@db.himmesomrcrpdvatpgas.supabase.co'")
        simulate_error_pattern()
        return

    # A. Pre-flight checks on raw URL structure WITHOUT printing the string
    cleaned = str(raw_env_url).strip().strip('"').strip("'")
    at_count = cleaned.count("@")
    has_brackets = "[" in cleaned or "]" in cleaned

    print("\n1. Safe URL Property Inspection (Zero Credentials Exposed):")
    print(f"   - Starts with postgres:// or postgresql://: {cleaned.startswith(('postgres://', 'postgresql://', 'postgresql+'))}")
    print(f"   - Number of '@' characters detected:         {at_count}")
    print(f"   - Contains '[' or ']' characters:           {has_brackets}")

    # B. How db.py normalizes the URL
    normalized_url = db.normalize_database_url(raw_env_url)

    # C. How SQLAlchemy parses the URL components
    print("\n2. Extracted URL Components (via SQLAlchemy make_url):")
    try:
        parsed = make_url(normalized_url)
        extracted_scheme = parsed.drivername
        extracted_user = parsed.username or "<none>"
        extracted_host = parsed.host or "<none>"
        extracted_port = str(parsed.port) if parsed.port else "<default (5432)>"
        extracted_db = parsed.database or "<none>"

        print(f"   - Scheme:        {extracted_scheme}")
        print(f"   - Username:      {extracted_user}")
        print(f"   - Hostname:      {extracted_host}")
        print(f"   - Port:          {extracted_port}")
        print(f"   - Database:      {extracted_db}")
        print(f"   - Password:      {safe_mask_string(parsed.password)}")

        # Validation against expected Supabase hostname format
        expected_host_pattern = r"^db\.[a-z0-9]+\.supabase\.co$"
        pooler_host_pattern = r"^[a-z0-9\-]+\.pooler\.supabase\.com$"

        if re.match(expected_host_pattern, extracted_host) or re.match(pooler_host_pattern, extracted_host):
            print("\n   [OK] Hostname matches valid Supabase hostname format.")
        else:
            print("\n   [WARNING] Hostname is MALFORMED:")
            print(f"             Extracted: '{extracted_host}'")
            print(f"             Expected format: 'db.<project-ref>.supabase.co'")

    except Exception as parse_err:
        print(f"   [ERROR] SQLAlchemy failed to parse URL: {parse_err}")

    # D. Attempt SELECT 1 using db.test_db_connection()
    print("\n3. Testing Database Connectivity (SELECT 1 via db.py):")
    success, conn_msg = db.test_db_connection()
    if success:
        print(f"   [SUCCESS] Connection verified: {conn_msg}")
    else:
        # Sanitize any passwords from connection message
        sanitized = re.sub(r":([^/@:]+)@", r":****@", str(conn_msg))
        sanitized = re.sub(r"postgres(ql)?(\+[a-z0-9]+)?://[^\s'\"]+", "[PROTECTED_DATABASE_URL]", sanitized)
        print(f"   [FAILURE] {sanitized}")

    print("\n" + "=" * 65)


def simulate_error_pattern():
    """
    Demonstrates how standard URI parsing in SQLAlchemy creates the exact error
    when the password contains an unescaped '@' and placeholder square brackets.
    """
    # Simulated pattern: postgresql://postgres:[somepass@jANA]@db.himmesomrcrpdvatpgas.supabase.co:5432/postgres
    simulated_url = "postgresql://postgres:[example@jANA]@db.himmesomrcrpdvatpgas.supabase.co:5432/postgres"
    parsed = make_url(simulated_url)
    print("\n--- Diagnostic Simulation ---")
    print(f"Extracted Scheme:   {parsed.drivername}")
    print(f"Extracted Username: {parsed.username}")
    print(f"Extracted Hostname: {parsed.host}")
    print(f"Extracted Port:     {parsed.port}")
    print(f"Extracted Database: {parsed.database}")
    print(f"Password Extracted: {safe_mask_string(parsed.password)}")
    print("\nComparison:")
    print(f"Malformed Hostname: '{parsed.host}'")
    print("Expected Hostname:  'db.himmesomrcrpdvatpgas.supabase.co'")
    print(f"Exact match to Render error: {parsed.host == 'jANA]@db.himmesomrcrpdvatpgas.supabase.co'}")
    print("=" * 65)


if __name__ == "__main__":
    analyze_database_url()
