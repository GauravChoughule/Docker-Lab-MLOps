# Import necessary libraries
import os
import joblib
from sklearn.datasets import load_breast_cancer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

MODEL_DIR = "model"
MODEL_PATH = os.path.join(MODEL_DIR, "breast_cancer_model.pkl")

if __name__ == '__main__':
    # Load the Breast Cancer Wisconsin dataset (30 features, 2 classes: malignant / benign)
    data = load_breast_cancer()
    X, y = data.data, data.target
    print(f"Loaded {X.shape[0]} samples with {X.shape[1]} features")

    # Stratified split keeps the same malignant/benign ratio in train and test
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Pipeline: scale the features, then Logistic Regression
    model = Pipeline([
        ("scaler", StandardScaler()),
        ("classifier", LogisticRegression(max_iter=1000, random_state=42)),
    ])
    model.fit(X_train, y_train)

    # Evaluate on the test set
    preds = model.predict(X_test)
    print(f"Test accuracy: {accuracy_score(y_test, preds):.3f}")
    print(classification_report(y_test, preds, target_names=data.target_names))

    # Save the model
    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(model, MODEL_PATH)

    print(f"The model training was successful. Saved to {MODEL_PATH}")
