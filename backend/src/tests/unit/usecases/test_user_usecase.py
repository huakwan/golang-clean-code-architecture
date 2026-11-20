from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.domain.entities.user import (
    UserEntity,
    UserLoginRequest,
    UserLogoutRequest,
    UserPermissionEntity,
    UserRefreshTokenRequest,
    UserRegisterRequest,
    UserTokenClaimsEntity,
    UserTokenEntity,
)
from src.domain.exceptions import AuthenticationError, ConflictError, NotFoundError, ValidationError
from src.domain.repositories.user_repository import StoredUserRecord
from src.shared.authentication.jwt_authentication import JWTAuthenticator, hash_token
from src.shared.authentication.password import hash_password
from src.usecases.user.user_usecase import UserUsecase


def _sample_user(user_id: int = 1) -> UserEntity:
    return UserEntity(
        id=user_id,
        email="jane@example.com",
        first_name="Jane",
        last_name="Doe",
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )


def _make_usecase(
    *,
    repo: MagicMock | None = None,
    logger: MagicMock | None = None,
) -> tuple[UserUsecase, MagicMock, JWTAuthenticator, MagicMock]:
    user_repo = repo or MagicMock()
    jwt_auth = JWTAuthenticator(
        secret_key="test-secret-key-at-least-32-bytes-long",
        app_name="PYTHON DJANGO CLEAN API",
        access_expires=3600,
        refresh_expires=86400,
    )
    activity_logger = logger or MagicMock()
    uc = UserUsecase(user_repo=user_repo, jwt_auth=jwt_auth, activity_logger=activity_logger)
    return uc, user_repo, jwt_auth, activity_logger


def test_register_user_creates_user_default_permission_and_logs_activity() -> None:
    uc, repo, _, logger = _make_usecase()
    repo.get_user_by_email.return_value = None
    repo.insert_user.return_value = _sample_user(10)

    user = uc.register_user(
        UserRegisterRequest("jane@example.com", "secret123", "Jane", "Doe"),
        ip_address="127.0.0.1",
    )

    assert user.id == 10
    repo.insert_user.assert_called_once()
    repo.insert_user_permission.assert_called_once_with(10, "user")
    logger.record.assert_called_once()
    assert logger.record.call_args.kwargs["action"] == "USER_REGISTER"
    assert logger.record.call_args.kwargs["status"] == "success"


def test_register_user_invalid_email_raises_validation_error() -> None:
    uc, repo, _, _ = _make_usecase()
    with pytest.raises(ValidationError, match="email pattern is invalid"):
        uc.register_user(UserRegisterRequest("bad-email", "secret123", "Jane", "Doe"))
    repo.insert_user.assert_not_called()


def test_register_user_duplicate_email_raises_conflict_error() -> None:
    uc, repo, _, _ = _make_usecase()
    repo.get_user_by_email.return_value = StoredUserRecord(_sample_user(), "hash")
    with pytest.raises(ConflictError, match="email already exists"):
        uc.register_user(UserRegisterRequest("jane@example.com", "secret123", "Jane", "Doe"))


def test_login_success_and_fail_safe_activity_logger() -> None:
    logger = MagicMock()
    logger.record.side_effect = RuntimeError("MongoDB down")
    uc, repo, jwt_auth, _ = _make_usecase(logger=logger)

    hashed = hash_password("secret123")
    repo.get_user_by_email.return_value = StoredUserRecord(_sample_user(1), hashed)
    repo.upsert_oauth.side_effect = lambda uid, acc, ref: UserTokenEntity(acc, ref)

    resp = uc.login(UserLoginRequest("jane@example.com", "secret123"), ip_address="127.0.0.1")

    assert resp.user.id == 1
    assert resp.token.access
    assert resp.token.refresh
    assert jwt_auth.parse_token(resp.token.access, expected_sub="access-token").claims.id == 1
    repo.upsert_oauth.assert_called_once_with(
        1,
        hash_token(resp.token.access),
        hash_token(resp.token.refresh),
    )
    logger.record.assert_called_once()


def test_login_wrong_password_logs_failed_attempt_and_raises() -> None:
    uc, repo, _, logger = _make_usecase()
    repo.get_user_by_email.return_value = StoredUserRecord(
        _sample_user(1), hash_password("correct-pass")
    )

    with pytest.raises(AuthenticationError, match="password is invalid"):
        uc.login(UserLoginRequest("jane@example.com", "wrong-pass"))

    logger.record.assert_called_once()
    assert logger.record.call_args.kwargs["action"] == "USER_LOGIN"
    assert logger.record.call_args.kwargs["status"] == "failed"


def test_refresh_token_rotates_access_and_preserves_refresh_exp() -> None:
    uc, repo, jwt_auth, logger = _make_usecase()
    user = _sample_user(3)
    initial_refresh = jwt_auth.create_refresh_token(UserTokenClaimsEntity(id=3))
    original_exp = jwt_auth.parse_token(initial_refresh, expected_sub="refresh-token").exp

    repo.find_one_oauth_by_user_id.return_value = UserTokenEntity(
        hash_token("old-acc"),
        hash_token(initial_refresh),
    )
    repo.get_user_by_user_id.return_value = user
    repo.upsert_oauth.side_effect = lambda uid, acc, ref: UserTokenEntity(acc, ref)

    resp = uc.refresh_token(UserRefreshTokenRequest(initial_refresh))
    assert resp.user.id == 3
    assert resp.token.refresh != initial_refresh
    parsed_refresh = jwt_auth.parse_token(resp.token.refresh, expected_sub="refresh-token")
    assert parsed_refresh.exp == original_exp
    repo.upsert_oauth.assert_called_once_with(
        3,
        hash_token(resp.token.access),
        hash_token(resp.token.refresh),
    )
    logger.record.assert_called_once()
    assert logger.record.call_args.kwargs["action"] == "USER_REFRESH_TOKEN"


def test_refresh_token_mismatch_raises_authentication_error() -> None:
    uc, repo, jwt_auth, _ = _make_usecase()

    refresh = jwt_auth.create_refresh_token(UserTokenClaimsEntity(id=3))
    repo.find_one_oauth_by_user_id.return_value = UserTokenEntity("acc", "different-refresh")

    with pytest.raises(AuthenticationError, match="user token not found"):
        uc.refresh_token(UserRefreshTokenRequest(refresh))


def test_logout_deletes_oauth_and_logs_activity() -> None:
    uc, repo, jwt_auth, logger = _make_usecase()

    refresh = jwt_auth.create_refresh_token(UserTokenClaimsEntity(id=5))
    repo.find_one_oauth_by_user_id.return_value = UserTokenEntity("acc", hash_token(refresh))

    uc.logout(UserLogoutRequest(refresh))
    repo.delete_oauth_by_user_id.assert_called_once_with(5)
    logger.record.assert_called_once()
    assert logger.record.call_args.kwargs["action"] == "USER_LOGOUT"


def test_authenticate_validates_jwt_and_db_session() -> None:
    uc, repo, jwt_auth, _ = _make_usecase()

    access = jwt_auth.create_access_token(UserTokenClaimsEntity(id=2))
    repo.find_oauth_by_user_id_and_access_token.return_value = UserTokenEntity(
        hash_token(access),
        "ref",
    )
    repo.get_user_by_user_id.return_value = _sample_user(2)
    repo.get_user_permission_by_user_id.return_value = UserPermissionEntity(1, 2, "user")

    user, perm = uc.authenticate(access)
    assert user.id == 2
    assert perm is not None and perm.permission == "user"
    repo.find_oauth_by_user_id_and_access_token.assert_called_once_with(2, hash_token(access))


def test_usecase_rejects_wrong_token_type_across_auth_endpoints() -> None:
    uc, repo, jwt_auth, _ = _make_usecase()
    claims = UserTokenClaimsEntity(id=7)
    access = jwt_auth.create_access_token(claims)
    refresh = jwt_auth.create_refresh_token(claims)

    with pytest.raises(AuthenticationError):
        uc.authenticate(refresh)

    with pytest.raises(AuthenticationError):
        uc.refresh_token(UserRefreshTokenRequest(access))

    with pytest.raises(AuthenticationError):
        uc.logout(UserLogoutRequest(access))

    repo.find_oauth_by_user_id_and_access_token.assert_not_called()
    repo.find_one_oauth_by_user_id.assert_not_called()


def test_get_user_profile_not_found_raises() -> None:
    uc, repo, _, _ = _make_usecase()
    repo.get_user_by_user_id.return_value = None
    with pytest.raises(NotFoundError, match="user not found"):
        uc.get_user_profile(999)


def test_register_and_login_normalize_email_case() -> None:
    uc, repo, _, _ = _make_usecase()
    repo.get_user_by_email.return_value = None
    repo.insert_user.return_value = _sample_user(11)

    uc.register_user(UserRegisterRequest("  Jane@Example.COM ", "secret123", "Jane", "Doe"))
    repo.get_user_by_email.assert_called_with("jane@example.com")
    assert repo.insert_user.call_args.kwargs["email"] == "jane@example.com"

    repo.get_user_by_email.reset_mock()
    repo.get_user_by_email.return_value = StoredUserRecord(
        _sample_user(11),
        hash_password("secret123"),
    )
    repo.upsert_oauth.side_effect = lambda uid, acc, ref: UserTokenEntity(acc, ref)

    uc.login(UserLoginRequest("  JANE@Example.COM ", "secret123"))
    repo.get_user_by_email.assert_called_once_with("jane@example.com")


def test_login_unknown_user_still_verifies_dummy_password_for_timing_safety(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.usecases.user import user_usecase

    uc, repo, _, logger = _make_usecase()
    repo.get_user_by_email.return_value = None

    calls: list[tuple[str, str | None]] = []

    def spy_verify(plain: str, hashed: str | None) -> bool:
        calls.append((plain, hashed))
        return False

    monkeypatch.setattr(user_usecase, "verify_password", spy_verify)

    with pytest.raises(AuthenticationError, match="password is invalid"):
        uc.login(UserLoginRequest("missing@example.com", "any-pass"))

    assert calls == [("any-pass", None)]
    logger.record.assert_called_once()
    assert logger.record.call_args.kwargs["status"] == "failed"


def test_register_user_rejects_whitespace_and_oversized_fields() -> None:
    uc, repo, _, _ = _make_usecase()

    with pytest.raises(ValidationError, match="first_name and last_name are required"):
        uc.register_user(UserRegisterRequest("jane@example.com", "secret123", "   ", "Doe"))

    with pytest.raises(ValidationError, match="first_name and last_name are required"):
        uc.register_user(UserRegisterRequest("jane@example.com", "secret123", "Jane", "   "))

    with pytest.raises(ValidationError):
        uc.register_user(UserRegisterRequest("jane@example.com", "secret123", "a" * 151, "Doe"))

    with pytest.raises(ValidationError):
        uc.register_user(UserRegisterRequest("jane@example.com", "secret123", "Jane", "b" * 151))

    long_email = f"{'a' * 64}@{'b' * 63}.{'c' * 63}.{'d' * 60}.com"
    assert len(long_email) > 255
    with pytest.raises(ValidationError):
        uc.register_user(UserRegisterRequest(long_email, "secret123", "Jane", "Doe"))

    repo.insert_user.assert_not_called()


def test_register_and_refresh_wrap_db_writes_in_atomic_without_locking_activity_log() -> None:
    from contextlib import contextmanager

    events: list[str] = []
    uc, repo, jwt_auth, logger = _make_usecase()

    @contextmanager
    def spy_atomic():
        events.append("enter_atomic")
        try:
            yield
        finally:
            events.append("exit_atomic")

    repo.atomic.side_effect = spy_atomic
    repo.get_user_by_email.return_value = None
    repo.insert_user.side_effect = lambda **kw: (events.append("insert_user"), _sample_user(12))[1]
    repo.insert_user_permission.side_effect = lambda uid, perm: (
        events.append("insert_permission"),
        UserPermissionEntity(1, uid, perm),
    )[1]
    logger.record.side_effect = lambda **kw: events.append("log_activity")

    uc.register_user(UserRegisterRequest("atomic@example.com", "secret123", "Atomic", "User"))
    assert events == [
        "enter_atomic",
        "insert_user",
        "insert_permission",
        "exit_atomic",
        "log_activity",
    ]

    events.clear()
    initial_refresh = jwt_auth.create_refresh_token(UserTokenClaimsEntity(id=12))
    repo.find_one_oauth_by_user_id.side_effect = lambda uid, **kw: (
        events.append(f"find_oauth:for_update={kw.get('for_update')}"),
        UserTokenEntity(hash_token("old"), hash_token(initial_refresh)),
    )[1]
    repo.get_user_by_user_id.side_effect = lambda uid: (
        events.append("get_user"),
        _sample_user(12),
    )[1]
    repo.upsert_oauth.side_effect = lambda uid, acc, ref: (
        events.append("upsert_oauth"),
        UserTokenEntity(acc, ref),
    )[1]

    uc.refresh_token(UserRefreshTokenRequest(initial_refresh))
    repo.find_one_oauth_by_user_id.assert_called_once_with(12, for_update=True)
    assert events == [
        "enter_atomic",
        "find_oauth:for_update=True",
        "get_user",
        "upsert_oauth",
        "exit_atomic",
        "log_activity",
    ]
