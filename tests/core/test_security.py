from app.core.security import (
    constant_time_equals,
    generate_secret,
    hash_password,
    sha256_hex,
    verify_password,
)


def test_hash_password_and_verify_password_accepts_correct_password():
    hashed = hash_password("StrongPass123!")

    assert hashed != "StrongPass123!"
    assert hashed.startswith("$argon2")
    assert verify_password("StrongPass123!", hashed) is True


def test_verify_password_rejects_incorrect_password():
    hashed = hash_password("StrongPass123!")

    assert verify_password("WrongPass123!", hashed) is False


def test_constant_time_equals_compares_strings():
    assert constant_time_equals("same-token", "same-token")
    assert not constant_time_equals("same-token", "other-token")


def test_sha256_hex_hashes_payload():
    assert sha256_hex("payload") == (
        "239f59ed55e737c77147cf55ad0c1b030b6d7ee748a7426952f9b852d5a935e5"
    )


def test_generate_secret_returns_sufficient_length():
    assert len(generate_secret()) >= 32
