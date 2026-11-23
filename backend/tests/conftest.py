"""
Configuração global da suíte de testes automatizados (Pytest) — JuriVision.
Garante isolamento completo do banco de dados de testes em um arquivo SQLite temporário
por sessão (`tmp_path_factory`), preservando intacto o banco local `jurivision_local.sqlite3`.
"""
import pytest
from sqlalchemy import create_engine

import app.core.database as db_mod
import app.main as main_mod
from app.core.database import Base, SessionLocal
from app.core.seed import seed_initial_data


@pytest.fixture(scope="session", autouse=True)
def isolated_test_database(tmp_path_factory: pytest.TempPathFactory):
    """
    Redireciona `engine` e `SessionLocal` para um SQLite temporário isolado durante
    toda a execução do pytest, evitando poluir `jurivision_local.sqlite3`.
    """
    db_dir = tmp_path_factory.mktemp("jurivision_test_db")
    db_file = db_dir / "test_jurivision.sqlite3"
    test_engine = create_engine(
        f"sqlite:///{db_file.as_posix()}",
        connect_args={"check_same_thread": False},
    )

    original_db_engine = db_mod.engine
    original_main_engine = main_mod.engine

    db_mod.engine = test_engine
    main_mod.engine = test_engine
    SessionLocal.configure(bind=test_engine)

    Base.metadata.create_all(bind=test_engine)
    with SessionLocal() as db:
        seed_initial_data(db)

    yield test_engine

    test_engine.dispose()
    db_mod.engine = original_db_engine
    main_mod.engine = original_main_engine
    SessionLocal.configure(bind=original_db_engine)
