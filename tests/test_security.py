from app.core.security import hash_password, verify_password


def test_hash_password_and_verify_password_accepts_correct_password():
    hashed = hash_password("StrongPass123!")

    assert hashed != "StrongPass123!"
    assert hashed.startswith("$argon2")
    assert verify_password("StrongPass123!", hashed) is True


def test_verify_password_rejects_incorrect_password():
    hashed = hash_password("StrongPass123!")

    assert verify_password("WrongPass123!", hashed) is False
