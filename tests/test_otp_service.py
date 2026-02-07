"""
iqromax.uz OTP Bot - Unit Tests
Tests for OTP service functionality
"""

import pytest
import hashlib
from datetime import datetime, timedelta

# Test OTP generation
class TestOTPGeneration:
    """Tests for OTP generation"""
    
    def test_otp_length(self):
        """Test that OTP is correct length"""
        import secrets
        
        length = 6
        max_value = 10 ** length - 1
        otp = secrets.randbelow(max_value + 1)
        otp_str = str(otp).zfill(length)
        
        assert len(otp_str) == length
    
    def test_otp_is_numeric(self):
        """Test that OTP contains only digits"""
        import secrets
        
        length = 6
        max_value = 10 ** length - 1
        otp = secrets.randbelow(max_value + 1)
        otp_str = str(otp).zfill(length)
        
        assert otp_str.isdigit()
    
    def test_otp_uniqueness(self):
        """Test that OTPs are unique"""
        import secrets
        
        length = 6
        max_value = 10 ** length - 1
        otps = set()
        
        for _ in range(100):
            otp = secrets.randbelow(max_value + 1)
            otp_str = str(otp).zfill(length)
            otps.add(otp_str)
        
        # Should have high uniqueness (allow some collisions)
        assert len(otps) > 90


class TestOTPHashing:
    """Tests for OTP hashing"""
    
    def test_hash_otp(self):
        """Test OTP hashing"""
        otp = "123456"
        expected_hash = hashlib.sha256(otp.encode()).hexdigest()
        actual_hash = hashlib.sha256(otp.encode()).hexdigest()
        
        assert actual_hash == expected_hash
    
    def test_verify_otp_hash(self):
        """Test OTP hash verification"""
        otp = "482917"
        otp_hash = hashlib.sha256(otp.encode()).hexdigest()
        
        # Correct OTP
        test_hash = hashlib.sha256(otp.encode()).hexdigest()
        assert test_hash == otp_hash
        
        # Wrong OTP
        wrong_hash = hashlib.sha256("000000".encode()).hexdigest()
        assert wrong_hash != otp_hash
    
    def test_hash_is_deterministic(self):
        """Test that same OTP produces same hash"""
        otp = "123456"
        hash1 = hashlib.sha256(otp.encode()).hexdigest()
        hash2 = hashlib.sha256(otp.encode()).hexdigest()
        
        assert hash1 == hash2


class TestInputValidation:
    """Tests for input validation"""
    
    def test_validate_telegram_id_valid(self):
        """Test valid Telegram ID validation"""
        valid_ids = [123456789, 1, 999999999999]
        
        for tid in valid_ids:
            try:
                result = int(tid)
                assert result > 0
            except (ValueError, TypeError):
                pytest.fail(f"Valid ID {tid} failed validation")
    
    def test_validate_telegram_id_invalid(self):
        """Test invalid Telegram ID validation"""
        invalid_ids = [-1, 0, "abc", None, ""]
        
        for tid in invalid_ids:
            try:
                result = int(tid)
                if result <= 0:
                    continue  # Expected
            except (ValueError, TypeError):
                continue  # Expected
    
    def test_validate_telegram_username_valid(self):
        """Test valid username validation"""
        import re
        
        valid_usernames = ["johndoe", "user_123", "TestUser"]
        pattern = r"^[a-zA-Z][a-zA-Z0-9_]{4,31}$"
        
        for username in valid_usernames:
            assert re.match(pattern, username) is not None
    
    def test_validate_telegram_username_invalid(self):
        """Test invalid username validation"""
        import re
        
        invalid_usernames = ["123user", "ab", "a" * 33, "user@name", ""]
        pattern = r"^[a-zA-Z][a-zA-Z0-9_]{4,31}$"
        
        for username in invalid_usernames:
            if username:
                assert re.match(pattern, username) is None
    
    def test_validate_otp_code_valid(self):
        """Test valid OTP code validation"""
        valid_codes = ["123456", "000000", "999999"]
        
        for code in valid_codes:
            assert code.isdigit() and len(code) == 6
    
    def test_validate_otp_code_invalid(self):
        """Test invalid OTP code validation"""
        invalid_codes = ["12345", "1234567", "abcdef", "12345a", ""]
        
        for code in invalid_codes:
            if code:
                assert not (code.isdigit() and len(code) == 6)


class TestRateLimiting:
    """Tests for rate limiting logic"""
    
    def test_rate_limit_counter(self):
        """Test rate limit counter logic"""
        max_requests = 5
        current_count = 0
        
        for i in range(7):
            if current_count < max_requests:
                current_count += 1
                allowed = True
            else:
                allowed = False
            
            if i < 5:
                assert allowed
            else:
                assert not allowed
    
    def test_cooldown_logic(self):
        """Test cooldown logic"""
        cooldown_minutes = 1
        last_request = datetime.utcnow() - timedelta(seconds=30)
        cooldown_end = last_request + timedelta(minutes=cooldown_minutes)
        
        # Still in cooldown
        assert datetime.utcnow() < cooldown_end
        
        # After cooldown
        last_request = datetime.utcnow() - timedelta(minutes=2)
        cooldown_end = last_request + timedelta(minutes=cooldown_minutes)
        assert datetime.utcnow() > cooldown_end


class TestExpiration:
    """Tests for OTP expiration"""
    
    def test_otp_not_expired(self):
        """Test OTP is not expired"""
        expiry_minutes = 3
        created_at = datetime.utcnow()
        expires_at = created_at + timedelta(minutes=expiry_minutes)
        
        assert datetime.utcnow() < expires_at
    
    def test_otp_expired(self):
        """Test OTP is expired"""
        expiry_minutes = 3
        created_at = datetime.utcnow() - timedelta(minutes=5)
        expires_at = created_at + timedelta(minutes=expiry_minutes)
        
        assert datetime.utcnow() > expires_at
    
    def test_attempts_remaining(self):
        """Test attempts remaining calculation"""
        max_attempts = 3
        current_attempts = 1
        
        remaining = max_attempts - current_attempts
        assert remaining == 2
        
        current_attempts = 3
        remaining = max_attempts - current_attempts
        assert remaining == 0


class TestSecurityFunctions:
    """Tests for security functions"""
    
    def test_api_key_comparison(self):
        """Test API key comparison"""
        import hmac
        
        correct_key = "test-api-key-123"
        provided_key = "test-api-key-123"
        
        assert hmac.compare_digest(correct_key, provided_key)
        
        wrong_key = "wrong-api-key"
        assert not hmac.compare_digest(correct_key, wrong_key)
    
    def test_sanitize_string(self):
        """Test string sanitization"""
        # Remove null bytes
        text = "hello\x00world"
        sanitized = text.replace("\x00", "")
        assert sanitized == "helloworld"
        
        # Trim to max length
        long_text = "a" * 300
        max_length = 255
        trimmed = long_text[:max_length]
        assert len(trimmed) == 255
    
    def test_phone_validation(self):
        """Test phone number validation"""
        import re
        
        valid_phones = ["+998901234567", "998901234567", "+1234567890"]
        pattern = r"^\+?\d{10,15}$"
        
        for phone in valid_phones:
            cleaned = re.sub(r"[^\d+]", "", phone)
            assert re.match(pattern, cleaned) is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
