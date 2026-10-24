from valhalla.schemas import Texture


def test_texture_validation() -> None:
    url = "http://localhost/textures/abc123"
    texture = Texture.model_validate({"meta": {}, "url": url})
    assert texture.url == url
