from pathlib import Path

from instant_transmission.ui import assets


def test_brand_assets_resolve_to_user_files():
    bg = assets.background_path()
    logo = assets.logo_path()
    icon = assets.icon_path()
    assert bg is not None and bg.name == "Shunkan_ido_bg.jpg"
    assert logo is not None and logo.name == "shunkan_ido_logo.png"
    assert icon is not None and icon.name == "shunkan_ido_icon.png"
    assert bg.is_file() and logo.is_file() and icon.is_file()


def test_assets_dir_points_at_repo_assets():
    assert assets.assets_dir().name == "assets"
    assert (assets.assets_dir() / "Shunkan_ido_bg.jpg").is_file()
