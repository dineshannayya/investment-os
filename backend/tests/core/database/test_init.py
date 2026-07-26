"""
Tests for app.core.database package exports.
"""

import app.core.database as database


def test_package_exports_expected_objects() -> None:
    """
    Verify all public database objects are exported.
    """

    assert database.Base is not None

    assert database.engine is not None

    assert callable(database.create_db_engine)

    assert callable(database.create_session)

    assert callable(database.get_db)

    assert callable(database.is_database_alive)

def test_package_all_contains_expected_exports() -> None:
    """
    Verify __all__ exports remain stable.
    """

    expected = {
        "Base",
        "engine",
        "create_db_engine",
        "create_session",
        "get_db",
        "is_database_alive",
    }

    assert set(database.__all__) == expected


