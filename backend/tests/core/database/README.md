Coverage Summary


| File              | Coverage Strategy            |
| ----------------- | ---------------------------- |
| `engine.py`       | Factory creation + singleton |
| `session.py`      | Session lifecycle            |
| `dependencies.py` | Generator cleanup paths      |
| `health.py`       | Success, failure, cleanup    |
| `base.py`         | Declarative inheritance      |
| `__init__.py`     | Public API exports           |

| File                   | Tests |
| ---------------------- | ----: |
| `test_engine.py`       |     5 |
| `test_session.py`      |     6 |
| `test_dependencies.py` |     3 |
| `test_health.py`       |     3 |
| `test_base.py`         |     2 |
| `test_init.py`         |     2 |

Grand Total: 21 focused unit tests.

1. test_engine.py
Purpose: Verify engine creation.

| Test                                         | Purpose                    |
| -------------------------------------------- | -------------------------- |
| `test_create_db_engine_returns_engine`       | Factory works              |
| `test_create_db_engine_uses_custom_url`      | URL override               |
| `test_create_db_engine_returns_new_instance` | Factory creates new engine |
| `test_engine_singleton_exists`               | Singleton initialized      |
| `test_engine_has_required_components`        | Basic engine configuration |


Notes:
    Use create_db_engine("sqlite:///:memory:") to avoid PostgreSQL.
    Do not assert the exact pool class or internal SQLAlchemy attributes.

Expected coverage:
    create_db_engine()
    Module-level engine

Target: 100%

2. test_session.py
Purpose: Verify session creation lifecycle.

| Test                                          | Purpose                                           |
| --------------------------------------------- | ------------------------------------------------- |
| `test_create_session_returns_session`         | Session creation                                  |
| `test_create_session_returns_unique_sessions` | Independent sessions                              |
| `test_session_is_bound_to_engine`             | Correct engine binding                            |
| `test_session_configuration`                  | Session options (`autoflush`, `expire_on_commit`) |
| `test_session_close`                          | Cleanup path                                      |
| `test_session_close_is_idempotent`            | Safe repeated cleanup                             |


Notes:
Do not test transactions here.
Do not require actual tables.

Expected coverage:
_SessionFactory
create_session()

Target: 100%


3. test_dependencies.py
Purpose: Verify FastAPI dependency behavior.

| Test                                         | Verifies                 |
| -------------------------------------------- | ------------------------ |
| `test_get_db_yields_session`                 | Session creation & yield |
| `test_get_db_closes_session_after_iteration` | Normal generator cleanup |
| `test_get_db_closes_session_on_exception`    | Exception cleanup        |


Implementation approach:
Patch create_session() to return a MagicMock.
Advance the generator with next().
Finish it with close() or throw().
Verify close() is called exactly once.

Expected coverage:
get_db()
try/finally

Target: 100%

4. test_health.py
Purpose: Verify health check logic.

| Test                                                  | Verifies              |
| ----------------------------------------------------- | --------------------- |
| `test_database_alive_returns_true`                    | Healthy database path |
| `test_database_alive_returns_false_on_database_error` | Error handling        |
| `test_database_alive_executes_select_one_query`       | Correct SQL statement |


Implementation:
Patch create_session().
Mock execute().
Raise SQLAlchemyError for failure path.
Assert close() called in both cases.

Do not require a running database.

Expected coverage:
Success path
Exception path
finally

Target: 100%

5. test_base.py
Purpose: Verify package exports.

| Test                              | Purpose               |
| --------------------------------- | --------------------- |
| `test_base_is_declarative_base`   | Inheritance           |
| `test_models_share_base_metadata` | Metadata registration |

Suggested assertions:
Import:
Base
engine
create_db_engine
create_session
get_db
is_database_alive
Optionally verify:
assert "create_session" in database.__all__

This protects the package's public interface.

Expected coverage:
Entire __init__.py

Target: 100%

6. test_init.py

| Test                                         | Purpose        |
| -------------------------------------------- | -------------- |
| `test_package_exports_expected_objects`      | Public imports |
| `test_package_all_contains_expected_exports` | Stable API     |

