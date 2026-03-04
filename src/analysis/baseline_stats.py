class FeatureBaseline:

    def __init__(self):

        self.mean = {
            "entropy": 0.93,
            "glcm_contrast": 1.65,
            "glcm_correlation": 0.94
        }

        self.std = {
            "entropy": 0.05,
            "glcm_contrast": 0.18,
            "glcm_correlation": 0.02
        }

    def z_score(self, value, feature):

        mean = self.mean[feature]
        std = self.std[feature]

        return (value - mean)/std