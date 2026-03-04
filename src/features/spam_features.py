import numpy as np


def calculate_transition_matrix(diff_array, axis, T=3):

    size = 2*T + 1

    if axis == 1:
        first = diff_array[:, :-1].flatten()
        second = diff_array[:, 1:].flatten()
    else:
        first = diff_array[:-1, :].flatten()
        second = diff_array[1:, :].flatten()

    indices = (first + T)*size + (second + T)

    counts = np.bincount(indices.astype(int), minlength=size**2)

    return counts / (counts.sum() + 1e-9)


def extract_spam_features(image, T=3):

    img = image.astype(float)

    res_h = np.clip(img[:,1:] - img[:,:-1], -T, T)
    res_v = np.clip(img[1:,:] - img[:-1,:], -T, T)
    res_d1 = np.clip(img[1:,1:] - img[:-1,:-1], -T, T)
    res_d2 = np.clip(img[1:,:-1] - img[:-1,1:], -T, T)

    return np.concatenate([
        calculate_transition_matrix(res_h,1,T),
        calculate_transition_matrix(res_v,0,T),
        calculate_transition_matrix(res_d1,1,T),
        calculate_transition_matrix(res_d2,1,T)
    ])