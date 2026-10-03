import pytest
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.models import Aluno  # noqa: F401 — necessário para criar tabela


def pytest_collection_modifyitems(items):
    marker_order = {"unit": 0, "integration": 1, "e2e": 2}

    def sort_key(item):
        for marker, position in marker_order.items():
            if item.get_closest_marker(marker):
                return (position, str(item.fspath), item.name)
        return (len(marker_order), str(item.fspath), item.name)

    items.sort(key=sort_key)


@pytest.fixture(scope="function")
def db_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # ✅ CRIA AS TABELAS ANTES DE CADA TESTE
    Base.metadata.create_all(bind=engine)
    yield engine
    # ✅ LIMPA DEPOIS (opcional)
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(db_engine):
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


@pytest.fixture(scope="function")
def client(db_engine):
    from fastapi.testclient import TestClient

    from app.main import app

    Session = sessionmaker(bind=db_engine)

    def override_get_db():
        session = Session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
