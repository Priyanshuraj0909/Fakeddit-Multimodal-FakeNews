"""Calibration and selective classification, independent of the final test set."""
import numpy as np
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss


def reliability(labels, probabilities, usable=None):
    labels, probabilities = np.asarray(labels), np.asarray(probabilities, dtype=float)
    if probabilities.shape != labels.shape or not np.isfinite(probabilities).all() or ((probabilities < 0) | (probabilities > 1)).any():
        raise ValueError('Expected aligned, finite binary probabilities')
    if not len(labels) or not np.isin(labels, [0, 1]).all():
        raise ValueError('Expected nonempty binary labels')
    usable = np.ones(len(labels), dtype=bool) if usable is None else np.asarray(usable, dtype=bool)
    if usable.shape != labels.shape:
        raise ValueError('Usability mask does not align with labels')
    bins, ece = [], 0.0
    for index in range(10):
        mask = (probabilities >= index / 10) & (probabilities < (index + 1) / 10 if index < 9 else probabilities <= 1)
        if mask.any():
            observed, predicted = float(labels[mask].mean()), float(probabilities[mask].mean())
            ece += mask.mean() * abs(observed-predicted)
            bins.append({'lower': index/10, 'upper': (index+1)/10, 'count': int(mask.sum()), 'mean_score': predicted, 'fraction_real': observed})
    selective = []
    for threshold in (0.5, 0.6, 0.65, 0.7, 0.8, 0.9, 0.95):
        accepted = usable & (np.maximum(probabilities, 1-probabilities) >= threshold)
        selective.append({'threshold': threshold, 'accepted': int(accepted.sum()), 'coverage': float(accepted.mean()),
                          'accuracy': float(accuracy_score(labels[accepted], probabilities[accepted] >= .5)) if accepted.any() else None})
    return {'brier_score': float(brier_score_loss(labels, probabilities)), 'log_loss': float(log_loss(labels, probabilities, labels=[0, 1])),
            'ece_10_equal_width_bins': float(ece), 'reliability_bins': bins, 'selective_classification': selective,
            'usable': int(usable.sum()), 'rows': len(labels)}
