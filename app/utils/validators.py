




def is_valid_password(password: str) -> bool:
    MIN_LENGTH = 8
    checks = (
        len(password) >= MIN_LENGTH,
        any(c.isdigit() for c in password),
        any(c.isupper() for c in password),
        any(c.islower() for c in password),
        any(not c.isalnum() for c in password),
    )
    return all(checks)


