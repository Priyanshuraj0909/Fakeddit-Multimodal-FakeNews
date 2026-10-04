"""Independent split evaluation metrics."""
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score

def evaluate(frame, predicted):
    labels = frame["2_way_label"]
    return {"accuracy": accuracy_score(labels, predicted),
            "macro_f1": f1_score(labels, predicted, average="macro", zero_division=0),
            "classification_report": classification_report(labels, predicted, labels=[0, 1], output_dict=True, zero_division=0),
            "confusion_matrix": confusion_matrix(labels, predicted, labels=[0, 1]).tolist()}
