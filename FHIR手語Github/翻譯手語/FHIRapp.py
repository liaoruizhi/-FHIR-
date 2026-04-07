from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from datetime import datetime
import joblib
import numpy as np
import statistics
import os
import json

app = Flask(__name__)
CORS(app)  # ⭐ 加入 CORS 支援

MODEL_PATH = "svm_model.pkl"
BUFFER_SIZE = 30
THRESHOLD = 0.6

model = joblib.load(MODEL_PATH)

# ===== 特徵提取 =====
def extract_features(sequence):
    try:
        accel_x = [s["accel"]["x 軸加速度"] for s in sequence]
        accel_y = [s["accel"]["y 軸加速度"] for s in sequence]
        accel_z = [s["accel"]["z 軸加速度"] for s in sequence]
        gyr_a   = [s["gyro"]["繞 Z 軸 alpha"] for s in sequence]
        gyr_b   = [s["gyro"]["繞 X 軸 beta"] for s in sequence]
        gyr_g   = [s["gyro"]["繞 Y 軸 gamma"] for s in sequence]
        ori_a   = [s["orientation"]["α 方向角 (Z軸偏航 yaw)"] for s in sequence]
        ori_b   = [s["orientation"]["β 俯仰角 (X軸 pitch)"] for s in sequence]
        ori_g   = [s["orientation"]["γ 翻滾角 (Y軸 roll)"] for s in sequence]

        feats = []
        for arr in (accel_x, accel_y, accel_z,
                    gyr_a, gyr_b, gyr_g,
                    ori_a, ori_b, ori_g):
            feats.append(round(statistics.mean(arr), 4))
            feats.append(round(statistics.stdev(arr), 4))
        return feats
    except Exception as e:
        print("Feature extraction error:", e)
        return []

# ===== 建立 FHIR JSON =====
def build_fhir(features, prediction):
    names = [
        "X軸加速度平均值","X軸加速度標準差",
        "Y軸加速度平均值","Y軸加速度標準差",
        "Z軸加速度平均值","Z軸加速度標準差",
        "X軸角速度平均值","X軸角速度標準差",
        "Y軸角速度平均值","Y軸角速度標準差",
        "Z軸角速度平均值","Z軸角速度標準差",
        "X軸方向角平均值","X軸方向角標準差",
        "Y軸方向角平均值","Y軸方向角標準差",
        "Z軸方向角平均值","Z軸方向角標準差"
    ]

    units = [
        "m/s^2","m/s^2","m/s^2","m/s^2","m/s^2","m/s^2",
        "deg/s","deg/s","deg/s","deg/s","deg/s","deg/s",
        "degree","degree","degree","degree","degree","degree"
    ]

    components = []
    for i in range(len(names)):
        components.append({
            "code": {"text": names[i]},
            "valueQuantity": {
                "value": features[i],
                "unit": units[i]
            }
        })

    components.append({
        "code": {"text": "手語辨識結果"},
        "valueString": prediction
    })

    return {
        "resourceType": "Observation",
        "id": f"sign-obs-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "status": "final",
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "activity",
                "display": "活動"
            }]
        }],
        "code": {"text": "手語辨識"},
        "subject": {"reference": "Patient/patient-001", "display": "使用者"},
        "effectiveDateTime": datetime.now().isoformat(),
        "component": components
    }

# ===== Routes =====
@app.route("/")
def index():
    return render_template("predict.html")

@app.route("/test", methods=["GET"])
def test():
    return "Flask OK!"

@app.route("/predict-sequence", methods=["POST"])
def predict_sequence():
    try:
        payload = request.get_json(force=True)
        sequence = payload.get("sequence", [])

        if len(sequence) != BUFFER_SIZE:
            return jsonify({"status": "error", "message": "資料不足"}), 400

        features = extract_features(sequence)
        if not features:
            return jsonify({"status":"error","message":"特徵提取失敗"}), 500

        # 預測
        probas = model.predict_proba([features])[0]
        idx = np.argmax(probas)
        confidence = probas[idx]
        label = model.classes_[idx]

        if confidence < THRESHOLD:
            label = "信心不足"

        # 建立 FHIR JSON
        fhir_json = build_fhir(features, label)

        # ===== 新增：累積存檔到本地 FHIRjson.json =====
        file_path = "FHIRjson.json"
        all_data = []

        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    all_data = json.load(f)
            except json.JSONDecodeError:
                all_data = []

        all_data.append(fhir_json)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        # ===== 存檔結束 =====

        return jsonify({
            "status": "ok",
            "prediction": label,
            "confidence": round(confidence,4),
            "fhir": fhir_json
        })

    except Exception as e:
        print("Error in /predict-sequence:", e)
        return jsonify({"status": "error", "message": str(e)}), 500

# ===== Main =====
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)