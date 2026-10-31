"""Optional experiment tracking; never upload raw data or full checkpoints automatically."""
import os


def track_run(name, metrics, parameters, reports=()):
    uri = os.environ.get('FAKEDDIT_MLFLOW_URI', '').strip()
    if not uri:
        return
    import mlflow
    mlflow.set_tracking_uri(uri)
    mlflow.set_experiment('fakeddit')
    with mlflow.start_run(run_name=name):
        mlflow.log_params(parameters)
        def log_values(values, prefix=''):
            for key, value in values.items():
                key = prefix + str(key)
                if isinstance(value, dict):
                    log_values(value, key + '/')
                elif isinstance(value, (int, float)) and not isinstance(value, bool):
                    mlflow.log_metric(key, value)
        log_values(metrics)
        for report in reports:
            mlflow.log_artifact(str(report), artifact_path='evaluation')
