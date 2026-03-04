import numpy as np


def extract_lsb_entropy(image):

    lsb = (image.astype("uint8") % 2).flatten()

    p0 = np.mean(lsb==0)
    p1 = 1 - p0

    H = 0

    if p0>0:
        H -= p0*np.log2(p0)

    if p1>0:
        H -= p1*np.log2(p1)

    return H