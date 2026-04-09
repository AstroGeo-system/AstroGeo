# 06_train_rf.py
# AstroGeo — Train Random Forest on India NDVI training data
# Run AFTER 05c_download_and_merge.py produces the combined CSV

import os
import json
import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import shap
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import (
    classification_report, confusion_matrix,
    ConfusionMatrixDisplay
)

TRAINING_CSV = '../data/ndvi_training_india_combined.csv'
MODEL_FILE   = '../models/geospatial_rf_model.pkl'
SHAP_CSV     = '../outputs/shap_mean_abs_values.csv'
RESULTS_FILE = '../models/rf_training_results.json'

FEATURE_COLS = [
    'ndvi_2018', 'ndvi_2019', 'ndvi_2020',
    'ndvi_2022', 'ndvi_2024',
    'delta_total', 'delta_recent',
]
LABEL_COL = 'change_class'

FEATURE_DISPLAY = [
    'NDVI 2018', 'NDVI 2019', 'NDVI 2020',
    'NDVI 2022', 'NDVI 2024',
    'Delta total\n(2018→2024)', 'Delta recent\n(2022→2024)',
]

CLASS_NAMES = [
    'Stable vegetation',
    'Vegetation loss',
    'Urban growth',
    'Stable other',
]
CLASS_LABELS = {0: 'Stable vegetation', 1: 'Vegetation loss',
                2: 'Urban growth', 3: 'Stable other'}


# ── Load data ────────────────────────────────────────────────
print('Loading training data...')
df = pd.read_csv(TRAINING_CSV)
print(f'  Rows: {len(df):,}')
print(f'  Class distribution:\n{df[LABEL_COL].value_counts().sort_index()}')

X = df[FEATURE_COLS].values
y = df[LABEL_COL].astype(int).values
present_labels = sorted(pd.unique(y).tolist())
present_class_names = [CLASS_LABELS[l] for l in present_labels]

# Train/test split — stratified to maintain class balance
X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.2,
    random_state=42,
    stratify=y,
)
print(f'\nTrain: {len(X_train):,} rows')
print(f'Test:  {len(X_test):,} rows')


# ── Train model ──────────────────────────────────────────────
print('\nTraining RandomForestClassifier...')
model = RandomForestClassifier(
    n_estimators=200,
    max_depth=10,
    min_samples_leaf=5,
    class_weight='balanced',   # handles class imbalance
    random_state=42,
    n_jobs=-1,                 # use all CPU cores
)
model.fit(X_train, y_train)
print('Training complete.')


# ── Evaluate ─────────────────────────────────────────────────
y_pred = model.predict(X_test)
report = classification_report(
    y_test, y_pred,
    labels=present_labels,
    target_names=present_class_names,
    output_dict=True,
)

print('\nClassification Report:')
print(classification_report(
    y_test, y_pred,
    labels=present_labels,
    target_names=present_class_names
))

# Cross-validation on full dataset
cv_scores = cross_val_score(model, X, y, cv=5, scoring='accuracy', n_jobs=-1)
print(f'5-fold CV accuracy: {cv_scores.mean():.3f} ± {cv_scores.std():.3f}')

overall_accuracy = report['accuracy']
print(f'Test accuracy: {overall_accuracy:.3f}')

# Warn if below target
if overall_accuracy < 0.82:
    print('⚠️  Accuracy below 0.82 target.')
    print('   Consider: more samples, relaxing cloud threshold, or')
    print('   adjusting class reclassification rules.')


# ── Save model ───────────────────────────────────────────────
joblib.dump(model, MODEL_FILE)
print(f'\nModel saved: {MODEL_FILE}')


# ── Plot 1: Confusion matrix ─────────────────────────────────
fig, ax = plt.subplots(figsize=(8, 6))
cm = confusion_matrix(y_test, y_pred)
disp = ConfusionMatrixDisplay(cm, display_labels=present_class_names)
disp.plot(ax=ax, colorbar=True, cmap='Blues')
ax.set_title('Confusion Matrix — India NDVI Random Forest', pad=14)
plt.tight_layout()
plt.savefig('../outputs/confusion_matrix.png', dpi=150, bbox_inches='tight')
print('Saved: confusion_matrix.png')
plt.close()


# ── SHAP analysis ────────────────────────────────────────────
print('\nRunning SHAP analysis (TreeExplainer)...')
# Use a representative sample — 800 rows is enough for stable SHAP values
sample_idx  = np.random.RandomState(42).choice(len(X_train), 800, replace=False)
X_sample    = X_train[sample_idx]

explainer   = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X_sample)
# Normalize SHAP outputs across versions into per-class matrices.
if isinstance(shap_values, list):
    # Older SHAP: list of arrays, each (n_samples, n_features)
    shap_values_by_class = shap_values
elif isinstance(shap_values, np.ndarray) and shap_values.ndim == 3:
    if shap_values.shape[2] == len(present_class_names):
        # Newer SHAP multiclass: (n_samples, n_features, n_classes)
        shap_values_by_class = [shap_values[:, :, c] for c in range(shap_values.shape[2])]
    elif shap_values.shape[0] == len(present_class_names):
        # Alternate multiclass layout: (n_classes, n_samples, n_features)
        shap_values_by_class = [shap_values[c, :, :] for c in range(shap_values.shape[0])]
    else:
        raise ValueError(f'Unexpected SHAP multiclass shape: {shap_values.shape}')
elif isinstance(shap_values, np.ndarray) and shap_values.ndim == 2:
    # Binary/single-output fallback.
    shap_values_by_class = [shap_values]
else:
    raise ValueError(f'Unsupported SHAP output type/shape: {type(shap_values)}')

# Mean absolute SHAP per feature per class
mean_abs_shap = np.array([np.abs(arr).mean(axis=0) for arr in shap_values_by_class])

# Save SHAP values as CSV for Streamlit and PostgreSQL
shap_df = pd.DataFrame(
    mean_abs_shap,
    index=present_class_names,
    columns=FEATURE_DISPLAY
)
shap_df.to_csv(SHAP_CSV)
print(f'\nSHAP values saved: {SHAP_CSV}')
print(shap_df.round(4))


# ── Plot 2: SHAP heatmap ─────────────────────────────────────
fig, ax = plt.subplots(figsize=(11, 5))
im = ax.imshow(mean_abs_shap, cmap='YlOrRd', aspect='auto')

ax.set_xticks(range(len(FEATURE_DISPLAY)))
ax.set_xticklabels(FEATURE_DISPLAY, fontsize=10, rotation=15, ha='right')
ax.set_yticks(range(len(present_class_names)))
ax.set_yticklabels(present_class_names, fontsize=11)

# Annotate cells with values
max_val = mean_abs_shap.max()
for i in range(len(present_class_names)):
    for j in range(len(FEATURE_DISPLAY)):
        val        = mean_abs_shap[i, j]
        text_color = 'white' if val > max_val * 0.6 else 'black'
        ax.text(j, i, f'{val:.3f}',
                ha='center', va='center',
                fontsize=9, color=text_color, fontweight='bold')

plt.colorbar(im, ax=ax, label='Mean |SHAP value|')
ax.set_title('SHAP Feature Importance by Class — India NDVI Model',
             fontsize=13, pad=14)
plt.tight_layout()
plt.savefig('../outputs/shap_heatmap.png', dpi=150, bbox_inches='tight')
print('Saved: shap_heatmap.png')
plt.close()


# ── Plot 3: Overall feature importance bar chart ─────────────
overall_importance = mean_abs_shap.mean(axis=0)
sorted_idx         = np.argsort(overall_importance)

fig, ax = plt.subplots(figsize=(9, 5))
colors  = ['#d73027' if 'Delta' in FEATURE_DISPLAY[i] else '#4575b4'
           for i in sorted_idx]
bars = ax.barh(
    [FEATURE_DISPLAY[i] for i in sorted_idx],
    overall_importance[sorted_idx],
    color=colors,
    height=0.6,
)

# Value labels on bars
for bar, val in zip(bars, overall_importance[sorted_idx]):
    ax.text(bar.get_width() + 0.0005,
            bar.get_y() + bar.get_height() / 2,
            f'{val:.4f}', va='center', fontsize=9)

ax.set_xlabel('Mean |SHAP value| (average across all classes)', fontsize=11)
ax.set_title('Overall Feature Importance — SHAP Summary', fontsize=12)

# Legend
from matplotlib.patches import Patch
legend_elements = [
    Patch(facecolor='#d73027', label='Change metric (delta)'),
    Patch(facecolor='#4575b4', label='Annual NDVI'),
]
ax.legend(handles=legend_elements, loc='lower right', fontsize=9)
plt.tight_layout()
plt.savefig('../outputs/shap_feature_importance_bar.png', dpi=150, bbox_inches='tight')
print('Saved: shap_feature_importance_bar.png')
plt.close()


# ── Plot 4: Per-class SHAP summary bars (version-safe) ───────
rows = int(np.ceil(len(present_class_names) / 2))
fig, axes = plt.subplots(rows, 2, figsize=(14, max(6, rows * 4.5)))
axes = np.array(axes).flatten()

for c, (ax, class_name) in enumerate(zip(axes, present_class_names)):
    vals = mean_abs_shap[c]
    order = np.argsort(vals)
    ax.barh(
        [FEATURE_DISPLAY[i] for i in order],
        vals[order],
        color="#7b68ee",
        height=0.6,
    )
    ax.set_title(f'Class {c}: {class_name}', fontsize=11)
    ax.set_xlabel('Mean |SHAP value|', fontsize=9)
    ax.tick_params(axis='y', labelsize=8)

for ax in axes[len(present_class_names):]:
    ax.axis('off')

plt.suptitle('Per-Class SHAP Feature Importance', fontsize=13, y=1.01)
plt.tight_layout()
plt.savefig('../outputs/shap_beeswarm_all_classes.png', dpi=150, bbox_inches='tight')
print('Saved: shap_beeswarm_all_classes.png')
plt.close()


# ── Save results summary ─────────────────────────────────────
results = {
    'model_file':        MODEL_FILE,
    'training_rows':     len(X_train),
    'test_rows':         len(X_test),
    'test_accuracy':     round(overall_accuracy, 4),
    'cv_accuracy_mean':  round(float(cv_scores.mean()), 4),
    'cv_accuracy_std':   round(float(cv_scores.std()), 4),
    'per_class_metrics': {
        cls: {
            'precision': round(report[cls]['precision'], 4),
            'recall':    round(report[cls]['recall'], 4),
            'f1_score':  round(report[cls]['f1-score'], 4),
        }
        for cls in present_class_names
    },
    'top_feature_overall': FEATURE_DISPLAY[int(np.argmax(overall_importance))],
    'shap_top_per_class': {
        present_class_names[c]: FEATURE_DISPLAY[int(np.argmax(mean_abs_shap[c]))]
        for c in range(len(present_class_names))
    },
    'trained_at': pd.Timestamp.utcnow().isoformat(),
}

with open(RESULTS_FILE, 'w') as f:
    json.dump(results, f, indent=2)

print(f'\nResults saved: {RESULTS_FILE}')
print('\n' + '=' * 55)
print('STEP 6 COMPLETE')
print('=' * 55)
print(f'Model:         {MODEL_FILE}')
print(f'Accuracy:      {overall_accuracy:.1%}')
print(f'CV Accuracy:   {cv_scores.mean():.1%} ± {cv_scores.std():.1%}')
print(f'Top feature:   {results["top_feature_overall"]}')
print(f'\nOutputs:')
print(f'  {MODEL_FILE}')
print(f'  {SHAP_CSV}')
print(f'  confusion_matrix.png')
print(f'  shap_heatmap.png')
print(f'  shap_feature_importance_bar.png')
print(f'  shap_beeswarm_all_classes.png')
print(f'\nNext: python 07_store_results.py')
