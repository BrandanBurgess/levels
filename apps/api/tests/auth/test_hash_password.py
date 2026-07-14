from __future__ import annotations

import pytest
from argon2 import PasswordHasher

from levels_api.scripts import hash_password


def test_hash_password_prompts_without_echo_and_prints_only_hash(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    answers = iter(["correct horse battery staple", "correct horse battery staple"])
    monkeypatch.setattr(hash_password, "getpass", lambda _: next(answers))

    hash_password.main()

    output = capsys.readouterr().out.strip()
    assert output.startswith("$argon2id$")
    assert "correct horse" not in output
    assert PasswordHasher().verify(output, "correct horse battery staple")


def test_hash_password_rejects_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    answers = iter(["one secure password", "another secure password"])
    monkeypatch.setattr(hash_password, "getpass", lambda _: next(answers))

    with pytest.raises(SystemExit, match="Passwords do not match"):
        hash_password.main()
