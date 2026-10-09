from pathlib import Path

from streamlit.testing.v1 import AppTest

from services import version


def test_release_exposes_semantic_version_and_normalized_build_identity():
    assert getattr(version, "APP_VERSION", None) == "0.1.0"
    assert version.BUILD_SHA
    assert len(version.BUILD_SHA) <= 12


def test_footer_displays_release_version_and_build_sha():
    app = AppTest.from_file(Path(__file__).parents[1] / "app.py").run()

    assert not app.exception
    assert any(
        "v0.1.0" in item.value and version.BUILD_SHA in item.value
        for item in app.caption
    )
