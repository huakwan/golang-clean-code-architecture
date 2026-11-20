from __future__ import annotations

from functools import lru_cache

from src.config.crud_models import get_crud_model_registry, list_registered_models
from src.config.env_config import AppConfig, get_config
from src.infrastructure.database.mongodb.connector import MongoDBConnector
from src.interfaces.repositories.crud.factory import build_crud_repository
from src.interfaces.repositories.mongodb.activity_logger import MongoActivityLogger
from src.interfaces.repositories.postgres.user_repository import PostgresUserRepository
from src.shared.authentication.jwt_authentication import JWTAuthenticator
from src.usecases.crud.crud_usecase import CrudUsecase
from src.usecases.user.user_usecase import UserUsecase


class AppContainer:
    """Composition root wiring infrastructure repositories into application use cases."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.jwt_auth = JWTAuthenticator(
            secret_key=config.secret_key,
            app_name=config.name,
            access_expires=config.jwt_access_expires,
            refresh_expires=config.jwt_refresh_expires,
        )
        self.user_repo = PostgresUserRepository()
        self.activity_logger = MongoActivityLogger(
            collection_provider=MongoDBConnector.get_collection,
        )
        self.user_usecase = UserUsecase(
            user_repo=self.user_repo,
            jwt_auth=self.jwt_auth,
            activity_logger=self.activity_logger,
        )
        self.crud_usecase = CrudUsecase(
            repo_factory=lambda slug: build_crud_repository(
                slug,
                registry=get_crud_model_registry(),
                mongo_collection_provider=MongoDBConnector.get_collection,
            ),
            model_lister=list_registered_models,
        )


@lru_cache(maxsize=1)
def get_container() -> AppContainer:
    return AppContainer(get_config())


def reset_container() -> None:
    get_container.cache_clear()
