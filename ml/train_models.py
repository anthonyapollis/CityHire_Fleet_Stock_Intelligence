"""
CityHire Fleet & Stock Intelligence - local ML layer.

Runs on local scikit-learn (no Databricks/Azure ML) - the Azure trial for this
account ends 2026-07-19, so cloud infra was deliberately skipped for this build.

Three models, each targeting a genuine, non-trivial signal already present in
the synthetic dataset (not a randomly-labelled target dressed up as "ML"):

1. Utilisation forecaster (regression)   - seasonal + category/depot pattern
2. Workshop % / in-service trajectory     - the 12-month improvement trend,
   (regression)                            used to predict when the 15% target
                                            is actually crossed
3. Capex overspend classifier             - which category-months are likely
   (classification)                        to exceed budget, from category +
                                            month features
4. Day-rate pricing model (regression)    - day_rate_gbp from capex + category,
                                            a pricing-consistency check
"""
import json
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score, roc_auc_score, accuracy_score, f1_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
ML = ROOT / "ml"
(ML / "models").mkdir(parents=True, exist_ok=True)
(ML / "reports").mkdir(parents=True, exist_ok=True)

results = {}

# =============================================================================
# MODEL 1 + 2: Daily stock stats - utilisation % and workshop % forecasting
# =============================================================================
daily = pd.read_csv(RAW / "daily_stock_stats.csv", parse_dates=["date"])
daily["day_of_year"] = daily["date"].dt.dayofyear
daily["month"] = daily["date"].dt.month
daily["days_since_start"] = (daily["date"] - daily["date"].min()).dt.days

split_date = daily["date"].quantile(0.85)
train = daily[daily["date"] <= split_date]
test = daily[daily["date"] > split_date]

cat_features = ["category", "depot"]
num_features = ["days_since_start", "month", "day_of_year"]

def build_pipeline(model):
    pre = ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore"), cat_features),
    ], remainder="passthrough")
    return Pipeline([("pre", pre), ("model", model)])

for target, name in [("utilisation_pct", "utilisation_forecast"), ("workshop_pct", "workshop_forecast")]:
    Xtr, ytr = train[cat_features + num_features], train[target]
    Xte, yte = test[cat_features + num_features], test[target]
    pipe = build_pipeline(GradientBoostingRegressor(n_estimators=200, max_depth=3, learning_rate=0.08, random_state=42))
    pipe.fit(Xtr, ytr)
    pred = pipe.predict(Xte)
    r2 = r2_score(yte, pred)
    mae = mean_absolute_error(yte, pred)
    joblib.dump(pipe, ML / "models" / f"{name}.joblib")
    results[name] = {"target": target, "r2": round(r2, 4), "mae": round(mae, 3),
                      "train_rows": len(Xtr), "test_rows": len(Xte),
                      "split_date": str(split_date.date())}
    print(f"{name}: R2={r2:.4f}  MAE={mae:.3f} pts  (n_train={len(Xtr)}, n_test={len(Xte)})")

# When does workshop % actually cross the 15% target, per the model's fitted trend?
future_dates = pd.date_range(daily["date"].min(), daily["date"].min() + pd.Timedelta(days=500), freq="D")
fc_frame = pd.DataFrame({
    "category": "Plant", "depot": "London North",
    "days_since_start": (future_dates - daily["date"].min()).days,
    "month": future_dates.month, "day_of_year": future_dates.dayofyear,
})
workshop_model = joblib.load(ML / "models" / "workshop_forecast.joblib")
fc_frame["pred_workshop_pct"] = workshop_model.predict(fc_frame[cat_features + num_features])
crossing = fc_frame[fc_frame["pred_workshop_pct"] <= 15].sort_values("days_since_start")
crossing_date = None
if len(crossing):
    crossing_date = (daily["date"].min() + pd.Timedelta(days=int(crossing.iloc[0]["days_since_start"]))).date()
results["workshop_forecast"]["predicted_15pct_crossing_date"] = str(crossing_date) if crossing_date else None
print(f"Workshop % model predicts crossing 15% target around: {crossing_date}")

# =============================================================================
# MODEL 3: Capex overspend classifier (category-month level)
# =============================================================================
capex = pd.read_csv(RAW / "capex_monthly.csv", parse_dates=["month"])
capex["month_num"] = capex["month"].dt.month
capex["over_budget"] = capex["over_budget"].astype(str).str.lower().eq("true").astype(int)

from sklearn.linear_model import LogisticRegression

# category identity is the real driver (3 categories were seeded with a
# structurally higher overspend probability) - month has no designed signal,
# so it's dropped rather than left in to add noise a small sample can overfit to
Xc = capex[["category"]]
yc = capex["over_budget"]
Xc_tr, Xc_te, yc_tr, yc_te = train_test_split(Xc, yc, test_size=0.25, random_state=42, stratify=yc)

pre = ColumnTransformer([("cat", OneHotEncoder(handle_unknown="ignore"), ["category"])], remainder="passthrough")
clf_pipe = Pipeline([("pre", pre), ("model", LogisticRegression(max_iter=1000, class_weight="balanced"))])
clf_pipe.fit(Xc_tr, yc_tr)
proba = clf_pipe.predict_proba(Xc_te)[:, 1]
pred = (proba >= 0.5).astype(int)
auc = roc_auc_score(yc_te, proba) if len(set(yc_te)) > 1 else float("nan")
acc = accuracy_score(yc_te, pred)
f1 = f1_score(yc_te, pred, zero_division=0)
joblib.dump(clf_pipe, ML / "models" / "capex_overspend_classifier.joblib")
results["capex_overspend_classifier"] = {
    "auc": round(auc, 4) if auc == auc else None, "accuracy": round(acc, 4), "f1": round(f1, 4),
    "train_rows": len(Xc_tr), "test_rows": len(Xc_te),
    "positive_rate_test": round(float(yc_te.mean()), 4),
}
print(f"capex_overspend_classifier: AUC={auc:.4f}  Acc={acc:.4f}  F1={f1:.4f}")

# Coefficients for the classifier (which categories drive overspend risk)
cat_names = list(clf_pipe.named_steps["pre"].named_transformers_["cat"].get_feature_names_out(["category"]))
coefs = clf_pipe.named_steps["model"].coef_[0]
feat_imp = sorted(zip(cat_names, coefs), key=lambda x: -x[1])[:8]
results["capex_overspend_classifier"]["top_risk_categories"] = [{"feature": f, "log_odds_coef": round(float(i), 4)} for f, i in feat_imp]

# =============================================================================
# MODEL 4: Day-rate pricing model (regression) - capex/category -> day rate
# =============================================================================
sm = pd.read_csv(RAW / "stock_master.csv")
Xp = sm[["category", "capex_gbp", "age_years"]]
yp = sm["day_rate_gbp"]
Xp_tr, Xp_te, yp_tr, yp_te = train_test_split(Xp, yp, test_size=0.2, random_state=42)
pre_p = ColumnTransformer([("cat", OneHotEncoder(handle_unknown="ignore"), ["category"])], remainder="passthrough")
price_pipe = Pipeline([("pre", pre_p), ("model", RandomForestRegressor(n_estimators=300, max_depth=8, random_state=42))])
price_pipe.fit(Xp_tr, yp_tr)
p_pred = price_pipe.predict(Xp_te)
p_r2 = r2_score(yp_te, p_pred)
p_mae = mean_absolute_error(yp_te, p_pred)
joblib.dump(price_pipe, ML / "models" / "day_rate_pricing_model.joblib")
results["day_rate_pricing_model"] = {"r2": round(p_r2, 4), "mae_gbp": round(p_mae, 2),
                                       "train_rows": len(Xp_tr), "test_rows": len(Xp_te)}
print(f"day_rate_pricing_model: R2={p_r2:.4f}  MAE=£{p_mae:.2f}")

# Flag under-priced assets (actual day rate well below model's expected rate) -
# JD bullet: "proactive recommendation for the purchase of stock" / pricing gaps
sm["predicted_day_rate"] = price_pipe.predict(sm[["category", "capex_gbp", "age_years"]])
sm["price_gap_pct"] = (sm["predicted_day_rate"] - sm["day_rate_gbp"]) / sm["predicted_day_rate"] * 100
underpriced = sm.sort_values("price_gap_pct", ascending=False).head(20)[
    ["stock_code", "category", "product_name", "depot", "day_rate_gbp", "predicted_day_rate", "price_gap_pct"]
]
underpriced.to_csv(ML / "reports" / "underpriced_assets.csv", index=False)
print(f"Flagged {len(underpriced)} under-priced assets -> ml/reports/underpriced_assets.csv")

# =============================================================================
# Save summary
# =============================================================================
(ML / "reports" / "model_results.json").write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
print("\nSaved model_results.json")
for k, v in results.items():
    print(k, "->", v)
