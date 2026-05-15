"""
test_ph3_security.py — PH.3 Security & Compliance Tests

Covers:
  A. InputValidator  — UUID, file path, property type, area, location,
                       execution mode, purpose, batch, sanitize
  B. RateLimiter     — allow/deny, reset, peek, thread-safety
  C. SecretsScanner  — detect/miss patterns, directory scan, summary
"""

from __future__ import annotations

import sys
import time
import threading
from pathlib import Path
from unittest.mock import patch

import pytest

# Make security importable from core_engine/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from security.input_validator import InputValidator, ValidationResult
from security.rate_limiter import RateLimiter, RateLimitResult
from security.secrets_scanner import SecretsScanner, SecretFinding


# ===========================================================================
# A. InputValidator
# ===========================================================================

class TestInputValidator:

    def test_A01_uuid_valid(self):
        r = InputValidator.validate_uuid('550e8400-e29b-41d4-a716-446655440000')
        assert r.is_valid
        assert r.value == '550e8400-e29b-41d4-a716-446655440000'

    def test_A02_uuid_invalid(self):
        r = InputValidator.validate_uuid('not-a-uuid')
        assert not r.is_valid
        assert 'UUID' in r.error

    def test_A03_file_path_traversal_blocked(self):
        r = InputValidator.validate_file_path('../../etc/passwd')
        assert not r.is_valid
        assert 'traversal' in r.error.lower()

    def test_A04_file_path_null_byte_blocked(self):
        r = InputValidator.validate_file_path('file\x00name.txt')
        assert not r.is_valid
        assert 'null' in r.error.lower()

    def test_A05_file_path_extension_whitelist(self):
        ok = InputValidator.validate_file_path('data.csv', allowed_extensions=['.csv', '.xlsx'])
        assert ok.is_valid
        bad = InputValidator.validate_file_path('evil.exe', allowed_extensions=['.csv', '.xlsx'])
        assert not bad.is_valid

    def test_A06_property_type_valid_and_invalid(self):
        assert InputValidator.validate_property_type('residential').is_valid
        r = InputValidator.validate_property_type('spaceship')
        assert not r.is_valid
        assert 'Unknown property type' in r.error

    def test_A07_area_boundaries(self):
        assert InputValidator.validate_area(100.0).is_valid
        assert not InputValidator.validate_area(-1).is_valid
        assert not InputValidator.validate_area(0).is_valid
        assert not InputValidator.validate_area(99_999_999).is_valid

    def test_A08_location_control_char_blocked(self):
        r = InputValidator.validate_location('Riyadh\x01District')
        assert not r.is_valid
        assert 'control' in r.error.lower()

    def test_A09_execution_mode_and_purpose(self):
        assert InputValidator.validate_execution_mode('supervised').is_valid
        assert not InputValidator.validate_execution_mode('god_mode').is_valid
        assert InputValidator.validate_purpose('market_value').is_valid
        assert not InputValidator.validate_purpose('profit_maximise').is_valid

    def test_A10_batch_and_sanitize(self):
        checks = [
            InputValidator.validate_uuid('bad'),
            InputValidator.validate_area(50.0),
        ]
        summary = InputValidator.validate_batch(checks)
        assert not summary['valid']
        assert 'id' in summary['errors']
        # sanitize
        dirty = 'Hello\x01World\x07'
        clean = InputValidator.sanitize_string(dirty)
        assert '\x01' not in clean
        assert '\x07' not in clean


# ===========================================================================
# B. RateLimiter
# ===========================================================================

class TestRateLimiter:

    def test_B01_allows_under_limit(self):
        rl = RateLimiter(limit=5, window_seconds=60)
        for _ in range(5):
            assert rl.is_allowed('user1')

    def test_B02_blocks_over_limit(self):
        rl = RateLimiter(limit=3, window_seconds=60)
        for _ in range(3):
            rl.is_allowed('user2')
        result = rl.check('user2')
        assert not result.allowed
        assert result.retry_after > 0

    def test_B03_reset_clears_window(self):
        rl = RateLimiter(limit=2, window_seconds=60)
        rl.is_allowed('user3')
        rl.is_allowed('user3')
        assert not rl.is_allowed('user3')
        rl.reset('user3')
        assert rl.is_allowed('user3')

    def test_B04_peek_does_not_consume(self):
        rl = RateLimiter(limit=2, window_seconds=60)
        rl.is_allowed('peek_user')
        r = rl.peek('peek_user')
        assert r.allowed
        assert r.current_count == 1  # unchanged

    def test_B05_result_to_dict(self):
        rl = RateLimiter(limit=10, window_seconds=30)
        r = rl.check('dict_user')
        d = r.to_dict()
        assert d['allowed'] is True
        assert d['limit'] == 10
        assert d['window_seconds'] == 30

    def test_B06_thread_safety(self):
        rl = RateLimiter(limit=50, window_seconds=60)
        results = []
        lock = threading.Lock()

        def hammer():
            for _ in range(10):
                ok = rl.is_allowed('shared')
                with lock:
                    results.append(ok)

        threads = [threading.Thread(target=hammer) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        allowed_count = sum(1 for r in results if r)
        assert allowed_count == 50  # exactly the limit


# ===========================================================================
# C. SecretsScanner
# ===========================================================================

class TestSecretsScanner:

    def test_C01_detects_hardcoded_password(self):
        scanner = SecretsScanner(skip_placeholders=False)
        code = 'password = "SuperSecret123!"'
        findings = scanner.scan_string(code)
        assert findings
        assert findings[0].severity == 'HIGH'
        assert 'password' in findings[0].pattern_name.lower()

    def test_C02_detects_aws_key(self):
        scanner = SecretsScanner()
        code = 'key = "AKIAIOSFODNN7EXAMPLE"'
        findings = scanner.scan_string(code)
        assert any(f.pattern_name == 'AWS access key' for f in findings)

    def test_C03_detects_google_api_key(self):
        scanner = SecretsScanner()
        # Use variable name that doesn't match the generic 'Hardcoded API key' pattern
        code = 'GOOG_CRED = "AIzaSyDxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx1"'
        findings = scanner.scan_string(code)
        assert any('Google' in f.pattern_name for f in findings)

    def test_C04_skips_comment_lines(self):
        scanner = SecretsScanner(skip_comments=True)
        code = '# password = "should_not_match"'
        findings = scanner.scan_string(code)
        assert findings == []

    def test_C05_skips_placeholder_values(self):
        scanner = SecretsScanner(skip_placeholders=True)
        code = 'api_key = "your_key_here"'
        findings = scanner.scan_string(code)
        assert findings == []

    def test_C06_min_severity_filter(self):
        scanner = SecretsScanner(skip_placeholders=False, min_severity='HIGH')
        # JWT is MEDIUM — should be filtered out
        code = 'token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV"'
        findings = scanner.scan_string(code)
        assert all(f.severity == 'HIGH' for f in findings)

    def test_C07_scan_file(self, tmp_path):
        f = tmp_path / 'creds.py'
        f.write_text('password = "HardCodedP@ss!"', encoding='utf-8')
        scanner = SecretsScanner(skip_placeholders=False)
        findings = scanner.scan_file(str(f))
        assert findings
        assert findings[0].file_path == str(f)

    def test_C08_scan_directory(self, tmp_path):
        (tmp_path / 'app.py').write_text('api_key = "AKIAIOSFODNN7EXAMPLE"', encoding='utf-8')
        (tmp_path / 'clean.py').write_text('x = 1 + 1', encoding='utf-8')
        scanner = SecretsScanner()
        findings = scanner.scan_directory(str(tmp_path), extensions=['.py'])
        assert any(f.file_path.endswith('app.py') for f in findings)
        assert not any(f.file_path.endswith('clean.py') for f in findings)

    def test_C09_summarize(self):
        findings = [
            SecretFinding('a.py', 1, 'x', 'Hardcoded password', 'HIGH'),
            SecretFinding('b.py', 2, 'y', 'Hardcoded token', 'MEDIUM'),
            SecretFinding('a.py', 3, 'z', 'Generic secret', 'HIGH'),
        ]
        s = SecretsScanner.summarize(findings)
        assert s['total'] == 3
        assert s['high'] == 2
        assert s['medium'] == 1
        assert s['affected_files'] == 2

    def test_C10_finding_to_dict(self):
        f = SecretFinding('x.py', 5, 'password="abc"', 'Hardcoded password', 'HIGH')
        d = f.to_dict()
        assert d['severity'] == 'HIGH'
        assert d['line'] == 5

    def test_C11_scan_unreadable_file_returns_empty(self):
        scanner = SecretsScanner()
        findings = scanner.scan_file('/nonexistent_xyz_abc/no_such_file.py')
        assert findings == []

    def test_C12_private_key_detected(self):
        scanner = SecretsScanner()
        code = '-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA...'
        findings = scanner.scan_string(code)
        assert any('Private key' in f.pattern_name for f in findings)
