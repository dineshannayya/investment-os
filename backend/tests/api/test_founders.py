"""
Tests for Founder API.
"""

from __future__ import annotations

from uuid import uuid4

from starlette import status


class TestFounderAPI:
    """Test Founder API."""

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    def test_create_founder(
        self,
        client,
        startup_factory,
    ) -> None:
        startup = startup_factory()

        payload = {
            "startup_id": str(startup.id),
            "full_name": "John Doe",
            "designation": "CEO",
            "email": "john@example.com",
            "linkedin_url": "https://linkedin.com/in/johndoe",
        }

        response = client.post(
            "/api/v1/founders",
            json=payload,
        )

        assert response.status_code == status.HTTP_201_CREATED

        body = response.json()

        assert body["full_name"] == payload["full_name"]
        assert body["designation"] == payload["designation"]
        assert body["email"] == payload["email"]
        assert body["linkedin_url"] == payload["linkedin_url"]
        assert body["startup_id"] == str(startup.id)
        assert "id" in body

    def test_create_duplicate_email(
        self,
        client,
        startup_factory,
        founder_factory,
    ) -> None:
        startup = startup_factory()

        founder_factory(
            startup=startup,
            email="john@example.com",
        )

        payload = {
            "startup_id": str(startup.id),
            "full_name": "John Doe",
            "designation": "CEO",
            "email": "john@example.com",
            "linkedin_url": None,
        }

        response = client.post(
            "/api/v1/founders",
            json=payload,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_unknown_startup(
        self,
        client,
    ) -> None:
        payload = {
            "startup_id": str(uuid4()),
            "full_name": "John Doe",
            "designation": "CEO",
            "email": "john@example.com",
            "linkedin_url": None,
        }

        response = client.post(
            "/api/v1/founders",
            json=payload,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_founder_invalid_payload(
        self,
        client,
    ) -> None:
        response = client.post(
            "/api/v1/founders",
            json={},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def test_list_founders(
        self,
        client,
        founder_factory,
    ) -> None:
        founder_factory()
        founder_factory()

        response = client.get("/api/v1/founders")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 2

    def test_get_founder(
        self,
        client,
        founder_factory,
    ) -> None:
        founder = founder_factory()

        response = client.get(
            f"/api/v1/founders/{founder.id}"
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["id"] == str(founder.id)

    def test_get_unknown_founder(
        self,
        client,
    ) -> None:
        response = client.get(
            f"/api/v1/founders/{uuid4()}"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def test_update_founder(
        self,
        client,
        founder_factory,
    ) -> None:
        founder = founder_factory()

        response = client.patch(
            f"/api/v1/founders/{founder.id}",
            json={
                "designation": "CTO",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["designation"] == "CTO"

    def test_update_duplicate_email(
        self,
        client,
        founder_factory,
    ) -> None:
        founder1 = founder_factory(
            email="one@example.com",
        )

        founder2 = founder_factory(
            email="two@example.com",
        )

        response = client.patch(
            f"/api/v1/founders/{founder2.id}",
            json={
                "email": founder1.email,
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_update_unknown_founder(
        self,
        client,
    ) -> None:
        response = client.patch(
            f"/api/v1/founders/{uuid4()}",
            json={
                "designation": "CEO",
            },
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def test_delete_founder(
        self,
        client,
        founder_factory,
    ) -> None:
        founder = founder_factory()

        response = client.delete(
            f"/api/v1/founders/{founder.id}"
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        response = client.get(
            f"/api/v1/founders/{founder.id}"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_unknown_founder(
        self,
        client,
    ) -> None:
        response = client.delete(
            f"/api/v1/founders/{uuid4()}"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
