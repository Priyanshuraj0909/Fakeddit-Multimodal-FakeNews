"""CPU XGBoost classifier configuration; validation controls early stopping."""
def build_classifier(estimators=2000):
    from xgboost import XGBClassifier
    return XGBClassifier(tree_method="hist", device="cpu", n_estimators=estimators,
                         max_depth=6, learning_rate=0.03, early_stopping_rounds=50,
                         random_state=42, eval_metric="logloss")
