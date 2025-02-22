import pandas as pd
import pickle
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

df = pd.read_csv("C:/Users/vinodini.saravanan/Downloads/Diabetes project/Diabetes project-20250216T085626Z-001/Diabetes project/diabetes.csv")

X = df.drop("Outcome", axis=1)
y = df["Outcome"]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

model = RandomForestClassifier(n_estimators=100)
model.fit(X_train, y_train)

with open("diabetes_model.pkl", "wb") as f:
    pickle.dump(model, f)

print("✅ Model trained and saved as diabetes_model.pkl")