import numpy as np
from skimage.transform import resize

from src.features.spam_features import extract_spam_features
from src.features.glcm_features import extract_glcm_features
from src.features.entropy_features import extract_lsb_entropy


def preprocess(image, size=512):

    if image.ndim == 3:
        image = (
            0.299*image[:,:,0] +
            0.587*image[:,:,1] +
            0.114*image[:,:,2]
        )

    if image.shape[0] != size:
        image = resize(image, (size,size), preserve_range=True)

    return image


def extract_feature_breakdown(image):

    img = preprocess(image)

    spam = extract_spam_features(img)
    glcm = extract_glcm_features(img)
    entropy = extract_lsb_entropy(img)

    features = np.concatenate([spam, glcm, [entropy]])

    return {
        "features": features,
        "spam": spam,
        "glcm": glcm,
        "entropy": entropy
    }