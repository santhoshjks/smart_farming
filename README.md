# Smart Farming AI Web App

A modern, premium web application for smart farming, featuring Crop Recommendation, Fertilizer Advice, and Plant Disease Detection.

## Features
- **Crop Recommendation**: Suggests the best crop based on soil N, P, K values and weather conditions.
- **Fertilizer Recommendation**: Advises on the best fertilizer to use.
- **Disease Detection**: Identifies plant diseases from leaf images.

## Setup Instructions

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the Application**
   ```bash
   python app.py
   ```

3. **Open in Browser**
   Go to `http://127.0.0.1:5000`

## Note on Machine Learning Models
Currently, the application uses **mock logic** and heuristics for demonstration purposes. This is because training real machine learning models requires large datasets (GBs in size) which were not provided.

### To use real models:
1. Train your DecisionTree/RandomForest models using Pandas and Scikit-Learn.
2. Save them using `pickle`.
3. Load them in `app.py` at the top:
   ```python
   import pickle
   crop_model = pickle.load(open('models/crop_recommendation.pkl', 'rb'))
   ```
4. Replace the logic in `predict_crop_logic` with:
   ```python
   return crop_model.predict([[N, P, K, temp, humidity, ph, rainfall]])[0]
   ```
