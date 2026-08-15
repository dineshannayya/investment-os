"""
Tests for Startup API endpoints.
"""

from __future__ import annotations

from uuid import uuid4

from app.core.config import API_PREFIX
from app.models.enums import StartupStage, StartupStatus

STARTUPS_URL = f"{API_PREFIX}/startups"


class TestStartupAPI:
    """Tests for Startup API."""

    # -------------------------------------------------------------------------
    # POST /startups
    # -------------------------------------------------------------------------

    def test_create_startup(
        self,
        client,
    ) -> None:
        """Create a startup."""

        response = client.post(
            STARTUPS_URL,
            json={
                "name": "Investment OS",
                "legal_name": "Investment OS Pvt Ltd",
                "description": "AI investment platform",
                "sector": "AI",
                "industry": "Software",
                "stage": StartupStage.MVP.value,
                "status": StartupStatus.ACTIVE.value,
            },
        )

        assert response.status_code == 201

        data = response.json()

        assert data["name"] == "Investment OS"
        assert data["sector"] == "AI"
        assert "id" in data

    # -------------------------------------------------------------------------
    # GET /startups
    # -------------------------------------------------------------------------

    def test_list_startups(
        self,
        client,
        startup_factory,
    ) -> None:
        """List startups."""

        startup_factory(name="Alpha")
        startup_factory(name="Beta")

        response = client.get(STARTUPS_URL)

        assert response.status_code == 200

        data = response.json()

        assert len(data) >= 2

    # -------------------------------------------------------------------------
    # GET /startups/{id}
    # -------------------------------------------------------------------------

    def test_get_startup(
        self,
        client,
        startup_factory,
    ) -> None:
        """Retrieve a startup."""

        startup = startup_factory()

        response = client.get(
            f"{STARTUPS_URL}/{startup.id}"
        )

        assert response.status_code == 200

        assert response.json()["id"] == str(startup.id)

    def test_get_startup_not_found(
        self,
        client,
    ) -> None:
        """Unknown startup returns 404."""

        response = client.get(
            f"{STARTUPS_URL}/{uuid4()}"
        )

        assert response.status_code == 404

    # -------------------------------------------------------------------------
    # PATCH /startups/{id}
    # -------------------------------------------------------------------------

    def test_update_startup(
        self,
        client,
        startup_factory,
    ) -> None:
        """Update startup."""

        startup = startup_factory()

        response = client.patch(
            f"{STARTUPS_URL}/{startup.id}",
            json={
                "description": "Updated description",
            },
        )

        assert response.status_code == 200

        assert (
            response.json()["description"]
            == "Updated description"
        )

    # -------------------------------------------------------------------------
    # DELETE /startups/{id}
    # -------------------------------------------------------------------------

    def test_delete_startup(
        self,
        client,
        startup_factory,
    ) -> None:
        """Delete startup."""

        startup = startup_factory()

        response = client.delete(
            f"{STARTUPS_URL}/{startup.id}"
        )

        assert response.status_code == 204

        response = client.get(
            f"{STARTUPS_URL}/{startup.id}"
        )

        assert response.status_code == 404

    # Validation failure
    def test_create_startup_invalid_payload(
        self,
        client,
    ):
        response = client.post(
            STARTUPS_URL,
            json={},
        )
    
        assert response.status_code == 422
    
    # Duplicate startup
    def test_create_duplicate_startup(
        self,
        client,
        startup_factory,
    ):
        startup_factory(name="Duplicate")
    
        response = client.post(
            STARTUPS_URL,
            json={
                "name": "Duplicate",
                "stage": StartupStage.MVP.value,
                "status": StartupStatus.ACTIVE.value,
            },
        )
    
        assert response.status_code in (400, 409)
    
    # Delete unknown startup
    def test_delete_unknown_startup(
        self,
        client,
    ):
        response = client.delete(
            f"{STARTUPS_URL}/{uuid4()}"
        )
    
        assert response.status_code == 404
