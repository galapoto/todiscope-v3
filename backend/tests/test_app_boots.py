from backend.app.main import create_app


def test_app_boots() -> None:
    app = create_app()
    assert app is not None

