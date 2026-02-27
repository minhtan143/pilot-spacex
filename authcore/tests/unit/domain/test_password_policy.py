"""Unit tests for PasswordPolicy domain service."""

from authcore.domain.services.password_policy import PasswordPolicy, PasswordPolicyResult


class TestPasswordPolicy:
    def setup_method(self) -> None:
        self.policy = PasswordPolicy()

    # --- valid ---

    def test_valid_password_passes(self) -> None:
        result = self.policy.validate("Secure1!")
        assert result.is_valid is True
        assert result.failures == ()

    def test_valid_long_password_passes(self) -> None:
        result = self.policy.validate("A" + "a" * 60 + "1")
        assert result.is_valid is True
        assert result.failures == ()

    # --- too short ---

    def test_too_short_fails(self) -> None:
        result = self.policy.validate("Ab1")
        assert result.is_valid is False
        assert any("at least 8" in f for f in result.failures)

    def test_exactly_min_length_passes(self) -> None:
        result = self.policy.validate("Abcdef1!")
        assert result.is_valid is True

    # --- too long ---

    def test_too_long_fails(self) -> None:
        long_pw = "A1" + "a" * 127  # 129 chars
        result = self.policy.validate(long_pw)
        assert result.is_valid is False
        assert any("at most 128" in f for f in result.failures)

    def test_exactly_max_length_passes(self) -> None:
        pw = "A1" + "a" * 126  # 128 chars
        result = self.policy.validate(pw)
        assert result.is_valid is True

    # --- missing uppercase ---

    def test_missing_uppercase_fails(self) -> None:
        result = self.policy.validate("alllower1")
        assert result.is_valid is False
        assert any("uppercase" in f for f in result.failures)

    # --- missing digit ---

    def test_missing_digit_fails(self) -> None:
        result = self.policy.validate("NoDigitHere!")
        assert result.is_valid is False
        assert any("digit" in f for f in result.failures)

    # --- multiple failures ---

    def test_multiple_failures_reported_together(self) -> None:
        # Short + no uppercase + no digit
        result = self.policy.validate("abc")
        assert result.is_valid is False
        assert len(result.failures) >= 3

    def test_empty_string_reports_all_applicable_failures(self) -> None:
        result = self.policy.validate("")
        assert result.is_valid is False
        # At minimum: too short, no uppercase, no digit
        assert len(result.failures) >= 3

    # --- return type ---

    def test_returns_password_policy_result(self) -> None:
        result = self.policy.validate("Secure1!")
        assert isinstance(result, PasswordPolicyResult)

    def test_failures_is_tuple(self) -> None:
        result = self.policy.validate("weak")
        assert isinstance(result.failures, tuple)
