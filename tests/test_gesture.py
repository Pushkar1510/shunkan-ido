from types import SimpleNamespace
from instant_transmission.gesture import is_instant_transmission


def _lm(x: float, y: float, z: float = 0.0):
    return SimpleNamespace(x=x, y=y, z=z)


def _hand(
    wrist=(0.5, 0.55),
    index_pip=(0.48, 0.40),
    index_tip=(0.50, 0.26),
    middle_pip=(0.52, 0.40),
    middle_tip=(0.52, 0.26),
    ring_pip=(0.54, 0.42),
    ring_tip=(0.54, 0.48),
    pinky_pip=(0.56, 0.43),
    pinky_tip=(0.56, 0.49),
):
    # MediaPipe hand indices used by implementation must match these slots.
    pts = [None] * 21
    pts[0] = _lm(*wrist)
    pts[6] = _lm(*index_pip)
    pts[8] = _lm(*index_tip)
    pts[10] = _lm(*middle_pip)
    pts[12] = _lm(*middle_tip)
    pts[14] = _lm(*ring_pip)
    pts[16] = _lm(*ring_tip)
    pts[18] = _lm(*pinky_pip)
    pts[20] = _lm(*pinky_tip)
    # Fill unused with wrist so attribute access is safe if probed
    for i, p in enumerate(pts):
        if p is None:
            pts[i] = _lm(*wrist)
    return pts


def _face_forehead():
    # Implementation should treat landmark 10 (MediaPipe Face Mesh) as forehead approx
    pts = [_lm(0.5, 0.5) for _ in range(468)]
    pts[10] = _lm(0.5, 0.25)
    return pts


_SIZES = ((1280, 720), (640, 360), (3840, 2160))


def test_valid_instant_transmission_pose():
    hand = _hand()
    face = _face_forehead()
    for image_size in _SIZES:
        assert is_instant_transmission(hand, face, image_size) is True


def test_rejects_when_fingers_far_from_forehead():
    hand = _hand(index_tip=(0.2, 0.8), middle_tip=(0.22, 0.8))
    face = _face_forehead()
    for image_size in _SIZES:
        assert is_instant_transmission(hand, face, image_size) is False


def test_rejects_open_palm():
    hand = _hand(
        ring_pip=(0.54, 0.40),
        ring_tip=(0.54, 0.26),
        pinky_pip=(0.56, 0.41),
        pinky_tip=(0.56, 0.27),
    )
    face = _face_forehead()
    for image_size in _SIZES:
        assert is_instant_transmission(hand, face, image_size) is False


def test_model_download_timeout_raises_runtime_error(monkeypatch, tmp_path):
    import instant_transmission.gesture as gesture

    class _Hung:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, _size):
            raise TimeoutError("timed out")

    def boom(url, timeout=0):
        return _Hung()

    monkeypatch.setattr(gesture.urllib.request, "urlopen", boom)
    monkeypatch.setattr(gesture, "_MODEL_DIR", tmp_path)
    try:
        gesture._cached_model("https://example.invalid/hand.task", "hand_landmarker.task")
    except RuntimeError as exc:
        assert "timed out" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")
    assert list(tmp_path.iterdir()) == []


def test_model_download_cancelled_by_stop_callback(monkeypatch, tmp_path):
    import instant_transmission.gesture as gesture

    class _Stream:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, _size):
            return b"x" * 1024

    def fake_urlopen(url, timeout=0):
        return _Stream()

    stopped = {"n": 0}

    def should_stop():
        stopped["n"] += 1
        return stopped["n"] >= 2

    monkeypatch.setattr(gesture.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(gesture, "_MODEL_DIR", tmp_path)
    try:
        gesture._cached_model(
            "https://example.invalid/hand.task",
            "hand_landmarker.task",
            should_stop=should_stop,
        )
    except RuntimeError as exc:
        assert str(exc) == "download cancelled"
    else:
        raise AssertionError("expected RuntimeError")
    assert list(tmp_path.iterdir()) == []


def test_cached_model_skips_download(monkeypatch, tmp_path):
    import instant_transmission.gesture as gesture

    dest = tmp_path / "hand_landmarker.task"
    dest.write_bytes(b"ok")

    def boom(url, timeout=0):
        raise AssertionError("should not download")

    monkeypatch.setattr(gesture.urllib.request, "urlopen", boom)
    monkeypatch.setattr(gesture, "_MODEL_DIR", tmp_path)
    assert gesture._cached_model("https://example.invalid/hand.task", "hand_landmarker.task") == dest
