"""Optional coarse background/noise maps; proposal geometry stays on native pixels."""

import cv2
import numpy as np

from .candidates import CandidateImage, enhance_compact, robust_sigma


def enhance_with_coarse_maps(image, *, denoise_sigma, background_sigma, noise_sigma,
                             quantization, background_step):
    """Use area-downsampled Gaussian maps, linearly sampled back to native size.

    Step 1 calls the unchanged T03 preprocessing exactly. Steps 2/4 approximate
    broad background and local noise maps only. The mild denoise, threshold mask,
    components and centroids always use the original image grid. Small images
    use at least one coarse sample per dimension; border handling is reflective.
    Map approximation can change proposals, so it requires measured validation.
    """
    if background_step == 1:
        return enhance_compact(image, denoise_sigma=denoise_sigma,
                               background_sigma=background_sigma, noise_sigma=noise_sigma,
                               quantization=quantization)
    height, width = image.shape
    size = (max(1, (width + background_step - 1) // background_step),
            max(1, (height + background_step - 1) // background_step))

    def broad_map(values, sigma):
        coarse = cv2.resize(values, size, interpolation=cv2.INTER_AREA)
        coarse = cv2.GaussianBlur(coarse, (0, 0), sigma / background_step,
                                  borderType=cv2.BORDER_REFLECT_101)
        return cv2.resize(coarse, (width, height), interpolation=cv2.INTER_LINEAR)

    smooth = cv2.GaussianBlur(image, (0, 0), denoise_sigma, borderType=cv2.BORDER_REFLECT_101)
    response = smooth - broad_map(image, background_sigma)
    response -= np.median(response)
    sigma = robust_sigma(response, quantization * 0.5)
    clipped = np.clip(response, -3 * sigma, 3 * sigma)
    variance = broad_map(clipped * clipped, noise_sigma)
    noise = np.maximum(np.sqrt(np.maximum(variance, 0)), sigma * 0.5)
    return CandidateImage(response, noise, sigma)
