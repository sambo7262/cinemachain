"""Tests for StaticFiles mount at /static/ (Phase 4.2)."""
import pytest


def test_static_posters_directory_served(client):
    """StaticFiles mount at /static/ returns 200 for a valid .jpg path (once a poster exists).

    This test is a smoke test for the mount itself — skipped until Plan 02 adds the mount.
    Once the mount exists, GET /static/posters/any_file.jpg should return 404 (not found)
    rather than a routing 404 from FastAPI, proving the static mount is active.
    """
    try:
        from fastapi.staticfiles import StaticFiles
        import os
        # If the /static mount exists, /static/posters/0.jpg returns 404 (file not found)
        # vs a 404 with detail "Not Found" from the FastAPI router (which means mount is absent)
        r = client.get("/static/posters/0.jpg")
        # Either 200 (file exists) or 404 from StaticFiles (file missing) is acceptable.
        # A 404 with FastAPI JSON {"detail": "Not Found"} means mount is absent — fail.
        if r.status_code == 404:
            content_type = r.headers.get("content-type", "")
            assert "application/json" not in content_type, (
                "Got FastAPI JSON 404 — /static/ mount is not registered in main.py"
            )
    except ImportError:
        pytest.skip("fastapi.staticfiles not available")
