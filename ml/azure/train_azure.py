"""
Training script that RUNS ON AZURE ML (submitted as a command job).
Retrains the day-rate pricing model (the highest-value model locally: R^2 0.93)
using Azure ML's native run tracking (mlflow autolog), so metrics show up in
the Azure ML Studio run history as proof of a real cloud training run.
"""
import argparse
import mlflow
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

parser = argparse.ArgumentParser()
parser.add_argument("--data", type=str, required=True)
args = parser.parse_args()

mlflow.sklearn.autolog()

sm = pd.read_csv(args.data)
X = sm[["category", "capex_gbp", "age_years"]]
y = sm["day_rate_gbp"]
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

pre = ColumnTransformer([("cat", OneHotEncoder(handle_unknown="ignore"), ["category"])], remainder="passthrough")
pipe = Pipeline([("pre", pre), ("model", RandomForestRegressor(n_estimators=300, max_depth=8, random_state=42))])

with mlflow.start_run():
    pipe.fit(X_train, y_train)
    pred = pipe.predict(X_test)
    r2 = r2_score(y_test, pred)
    mae = mean_absolute_error(y_test, pred)
    mlflow.log_metric("r2", r2)
    mlflow.log_metric("mae_gbp", mae)
    mlflow.log_param("n_train", len(X_train))
    mlflow.log_param("n_test", len(X_test))
    print(f"AZURE ML TRAINING RUN COMPLETE: R2={r2:.4f} MAE=£{mae:.2f}")
    print(f"train_rows={len(X_train)} test_rows={len(X_test)}")
