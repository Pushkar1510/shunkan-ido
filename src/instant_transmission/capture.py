from __future__ import annotations

import cv2
import numpy as np

# A single missed grab is common while a camera warms up. Raise only after
# several failures in one read so a transient miss does not kill the loop.
_MAX_READ_ATTEMPTS = 5


class CameraCapture:
    def __init__(self, camera: int, width: int, height: int, fps: int) -> None:
        self._camera = camera
        self._cap = cv2.VideoCapture(camera)
        if not self._cap.isOpened():
            self._cap.release()
            raise RuntimeError(f"Could not open camera {camera}")
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self._cap.set(cv2.CAP_PROP_FPS, fps)

    def read(self) -> np.ndarray:
        for _ in range(_MAX_READ_ATTEMPTS):
            if not self._cap.isOpened():
                break
            ok, frame = self._cap.read()
            if ok and frame is not None and frame.size > 0:
                return frame
        raise RuntimeError(f"Camera {self._camera} grab failed repeatedly")

    def close(self) -> None:
        self._cap.release()
