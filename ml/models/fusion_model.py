"""Validated image-first concatenation shared by training and inference."""
import numpy as np


def fuse_features(image, text):
    arrays = [np.asarray(image), np.asarray(text)]
    if any(a.ndim != 2 or a.shape[1] == 0 or not np.issubdtype(a.dtype, np.number)
           or np.iscomplexobj(a) or not np.isfinite(a).all() for a in arrays):
        raise ValueError("Expected finite two-dimensional modality features")
    if arrays[0].shape[0] != arrays[1].shape[0]:
        raise ValueError("Modalities must have the same number of samples")
    return np.concatenate(arrays, axis=1)
