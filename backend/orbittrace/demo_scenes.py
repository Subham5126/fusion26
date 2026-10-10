"""Small deterministic image-only demo scenes; no truth passed to inference."""
import numpy as np


def generate_demo_preset(preset: str) -> list[np.ndarray]:
    """Render five 640x480 frames with separated targets and bounded motion."""
    if preset not in ('1', '2', '3', '4'):
        raise ValueError('Unknown demo preset')
    yy, xx = np.mgrid[:480, :640]
    images = []
    for i in range(5):
        if preset == '1':
            centers = [(120 + 12*i, 150), (460 - 10*i, 330)]
        elif preset == '2':
            centers = [(120 + 10*i, 120 + 8*i), (440 - 8*i, 340 - 10*i)]
        elif preset == '3':
            centers = [(110 + 12*i, 130 + 3*i), (320 + 2*i, 320 - 10*i), (510 - 11*i, 140 + 7*i)]
        else:
            centers = [(120 + 10*i, 120 + i*i), (440 - 9*i, 330 - i*i), (310 + 2*i*i, 210 + 9*i)]
        image = np.full(xx.shape, 20.0)
        for x, y in centers:
            image += 100 * np.exp(-((xx-x)**2 + (yy-y)**2) / (2*1.8**2))
        images.append(np.rint(np.clip(image, 0, 255)).astype(np.uint8))
    return images
