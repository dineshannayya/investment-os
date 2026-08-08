import pytest

from app.models import Role

import uuid

@pytest.fixture
def role_factory(db_session):
    def _create(**kwargs):
        suffix = uuid.uuid4().hex[:8]
        role = Role(
            name=kwargs.pop("name", f"reviewer_{suffix}"),
            display_name=kwargs.pop(
                "display_name",
                f"Reviewer {suffix}",
            ),
            description=kwargs.pop("description", "Role description"),
            is_system=kwargs.pop("is_system", False),
            **kwargs,
        )
        db_session.add(role)
        db_session.flush()
        return role

    return _create


@pytest.fixture
def role(role_factory):
    return role_factory()
