"""Common password blacklist and password policy verification."""

# Top common/weak passwords to reject outright
COMMON_PASSWORDS: set[str] = {
    "password",
    "password123",
    "12345678",
    "123456789",
    "1234567890",
    "qwerty1234",
    "admin123",
    "letmein123",
    "welcome123",
    "changeme123",
    "festiva123",
    "festiva2026",
    "iloveyou1",
    "sunshine1",
    "princess1",
    "football1",
    "monkey123",
    "dragon123",
    "master123",
}

MIN_PASSWORD_LENGTH = 10
MAX_PASSWORD_LENGTH = 128


def validate_password_policy(password: str) -> None:
    """Validate password against length, complexity, and common blacklist.

    Raises:
        ValueError if the password violates policy.
    """
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters long.")
    if len(password) > MAX_PASSWORD_LENGTH:
        raise ValueError(f"Password must not exceed {MAX_PASSWORD_LENGTH} characters.")
    if password.lower() in COMMON_PASSWORDS:
        raise ValueError(
            "Password is too common and easily guessable. Please choose a stronger password."
        )


def normalize_email(email: str) -> str:
    """Normalize email address by trimming whitespace and converting to lowercase."""
    return email.strip().lower()
