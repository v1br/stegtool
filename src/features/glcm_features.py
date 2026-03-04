import numpy as np
from skimage.feature import graycomatrix, graycoprops


def extract_glcm_features(image):

    img = np.clip(image,0,255).astype("uint8")

    glcm = graycomatrix(
        img,
        distances=[1],
        angles=[0,0.785,1.57,2.356],
        levels=256,
        symmetric=True,
        normed=True
    )

    return [
        graycoprops(glcm,'contrast')[0].mean(),
        graycoprops(glcm,'correlation')[0].mean(),
        graycoprops(glcm,'energy')[0].mean(),
        graycoprops(glcm,'homogeneity')[0].mean()
    ]