# backend/responsible_ai/04c_debug_shap.py
import joblib, os
import pandas as pd
import numpy as np
import shap

MODEL_DIR = 'data/models/launch'
ensemble = joblib.load(os.path.join(MODEL_DIR, 'launch_model.pkl'))
scaler = joblib.load(os.path.join(MODEL_DIR, 'launch_scaler.pkl'))

# Create a dummy row with 17 features
X_dummy = np.zeros((10, 17))
rf = ensemble.named_estimators_['rf']

print(f"RF features: {rf.n_features_in_}")
print(f"X_dummy shape: {X_dummy.shape}")

explainer = shap.KernelExplainer(rf.predict_proba, shap.sample(X_dummy, 5))
sv = explainer.shap_values(X_dummy)

if isinstance(sv, list):
    print(f"SHAP list length: {len(sv)}")
    print(f"SHAP[0] shape: {sv[0].shape}")
else:
    print(f"SHAP shape: {sv.shape}")
