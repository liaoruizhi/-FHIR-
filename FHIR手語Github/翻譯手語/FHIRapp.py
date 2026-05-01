from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from datetime import datetime
import joblib
import numpy as np
import statistics
import os
import json
import requests
import re

app = Flask(__name__)
CORS(app)

MODEL_PATH = "svm_model.pkl"
BUFFER_SIZE = 30
THRESHOLD = 0.6

FHIR_BASE = "https://hapi.fhir.org/baseR4"
FHIR_HEADERS = {
    "Content-Type": "application/fhir+json",
    "Accept": "application/fhir+json"
}

PATIENT_INFO = {
    "family": "Liao",
    "given": "Ruizhi",
    "gender": "male",
    "birthDate": "2008-01-01"
}

PATIENT_ID_FILE = "patient_id.txt"
FHIR_LOCAL_FILE = "FHIRjson.json"

model = joblib.load(MODEL_PATH)


# ===== Patient 建立 / 取得 =====
def get_saved_patient_id():
    if os.path.exists(PATIENT_ID_FILE):
        with open(PATIENT_ID_FILE, "r", encoding="utf-8") as f:
            patient_id = f.read().strip()
            if patient_id:
                return patient_id
    return None


def save_patient_id(patient_id):
    with open(PATIENT_ID_FILE, "w", encoding="utf-8") as f:
        f.write(str(patient_id))


def create_or_get_patient():
    saved_id = get_saved_patient_id()
    if saved_id:
        return saved_id

    patient_data = {
        "resourceType": "Patient",
        "name": [
            {
                "family": PATIENT_INFO["family"],
                "given": [PATIENT_INFO["given"]]
            }
        ],
        "gender": PATIENT_INFO["gender"],
        "birthDate": PATIENT_INFO["birthDate"]
    }

    response = requests.post(
        f"{FHIR_BASE}/Patient",
        headers=FHIR_HEADERS,
        json=patient_data,
        timeout=20
    )

    print("建立 Patient 狀態碼:", response.status_code)
    print(response.text)

    if response.status_code in [200, 201]:
        patient_id = response.json().get("id")
        save_patient_id(patient_id)
        return patient_id

    if response.status_code == 412:
        match = re.search(r"Patient/(\d+)", response.text)
        if match:
            patient_id = match.group(1)
            save_patient_id(patient_id)
            return patient_id

    raise Exception(f"建立 Patient 失敗: {response.status_code} {response.text}")


# ===== 特徵提取 =====
def extract_features(sequence):
    try:
        accel_x = [s["accel"]["x 軸加速度"] for s in sequence]
        accel_y = [s["accel"]["y 軸加速度"] for s in sequence]
        accel_z = [s["accel"]["z 軸加速度"] for s in sequence]

        gyr_a = [s["gyro"]["繞 Z 軸 alpha"] for s in sequence]
        gyr_b = [s["gyro"]["繞 X 軸 beta"] for s in sequence]
        gyr_g = [s["gyro"]["繞 Y 軸 gamma"] for s in sequence]

        ori_a = [s["orientation"]["α 方向角 (Z軸偏航 yaw)"] for s in sequence]
        ori_b = [s["orientation"]["β 俯仰角 (X軸 pitch)"] for s in sequence]
        ori_g = [s["orientation"]["γ 翻滾角 (Y軸 roll)"] for s in sequence]

        feature_names = [
            "X軸加速度平均值", "X軸加速度標準差",
            "Y軸加速度平均值", "Y軸加速度標準差",
            "Z軸加速度平均值", "Z軸加速度標準差",
            "Z軸角速度平均值", "Z軸角速度標準差",
            "X軸角速度平均值", "X軸角速度標準差",
            "Y軸角速度平均值", "Y軸角速度標準差",
            "Z軸方向角平均值", "Z軸方向角標準差",
            "X軸方向角平均值", "X軸方向角標準差",
            "Y軸方向角平均值", "Y軸方向角標準差"
        ]

        feature_units = [
            "m/s^2", "m/s^2",
            "m/s^2", "m/s^2",
            "m/s^2", "m/s^2",
            "deg/s", "deg/s",
            "deg/s", "deg/s",
            "deg/s", "deg/s",
            "degree", "degree",
            "degree", "degree",
            "degree", "degree"
        ]

        raw_arrays = [accel_x, accel_y, accel_z, gyr_a, gyr_b, gyr_g, ori_a, ori_b, ori_g]

        features = []
        feature_map = []

        idx = 0
        for arr in raw_arrays:
            mean_val = round(statistics.mean(arr), 4)
            std_val = round(statistics.stdev(arr), 4)

            features.append(mean_val)
            features.append(std_val)

            feature_map.append({
                "name": feature_names[idx],
                "value": mean_val,
                "unit": feature_units[idx]
            })
            feature_map.append({
                "name": feature_names[idx + 1],
                "value": std_val,
                "unit": feature_units[idx + 1]
            })

            idx += 2

        return features, feature_map

    except Exception as e:
        print("Feature extraction error:", e)
        return [], []


# ===== 建立 FHIR Observation JSON =====
def build_fhir_observation(feature_map, prediction, confidence, patient_id, timestamp):
    components = []

    for item in feature_map:
        components.append({
            "code": {"text": item["name"]},
            "valueQuantity": {
                "value": item["value"],
                "unit": item["unit"]
            }
        })

    components.append({
        "code": {"text": "手語辨識信心值"},
        "valueQuantity": {
            "value": round(float(confidence), 4),
            "unit": "score"
        }
    })

    return {
        "resourceType": "Observation",
        "status": "final",
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "activity",
                "display": "Activity"
            }]
        }],
        "code": {"text": "手語辨識"},
        "subject": {
            "reference": f"Patient/{patient_id}",
            "display": "使用者"
        },
        "effectiveDateTime": timestamp,
        "valueString": str(prediction),
        "component": components
    }


# ===== 上傳 Observation 到 HAPI FHIR =====
def upload_observation_to_hapi(observation_json):
    response = requests.post(
        f"{FHIR_BASE}/Observation",
        headers=FHIR_HEADERS,
        json=observation_json,
        timeout=20
    )

    print("上傳 Observation 狀態碼:", response.status_code)
    print(response.text)

    if response.status_code not in [200, 201]:
        raise Exception(f"Observation 上傳失敗: {response.status_code} {response.text}")

    return response.json()


# ===== 讀取 Observation =====
def read_observation(observation_id):
    response = requests.get(
        f"{FHIR_BASE}/Observation/{observation_id}",
        headers={"Accept": "application/fhir+json"},
        timeout=20
    )

    print("讀取 Observation 狀態碼:", response.status_code)
    print(response.text)

    if response.status_code != 200:
        raise Exception(f"Observation 讀取失敗: {response.status_code} {response.text}")

    return response.json()


# ===== 本地存檔 =====
def save_fhir_to_local(fhir_json):
    all_data = []

    if os.path.exists(FHIR_LOCAL_FILE):
        try:
            with open(FHIR_LOCAL_FILE, "r", encoding="utf-8") as f:
                all_data = json.load(f)
        except json.JSONDecodeError:
            all_data = []

    all_data.append(fhir_json)

    with open(FHIR_LOCAL_FILE, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)


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
        timestamp = datetime.now().isoformat()

        if len(sequence) != BUFFER_SIZE:
            return jsonify({
                "status": "error",
                "message": f"資料不足，需 {BUFFER_SIZE} 筆",
                "timestamp": timestamp
            }), 400

        features, feature_map = extract_features(sequence)
        if not features:
            return jsonify({
                "status": "error",
                "message": "特徵提取失敗",
                "timestamp": timestamp
            }), 500

        probas = model.predict_proba([features])[0]
        idx = np.argmax(probas)
        confidence = float(probas[idx])
        label = str(model.classes_[idx])

        if confidence < THRESHOLD:
            return jsonify({
                "status": "uncertain",
                "prediction": "信心不足",
                "confidence": round(confidence, 4),
                "timestamp": timestamp
            })

        patient_id = create_or_get_patient()

        fhir_json = build_fhir_observation(
            feature_map=feature_map,
            prediction=label,
            confidence=confidence,
            patient_id=patient_id,
            timestamp=timestamp
        )

        upload_result = upload_observation_to_hapi(fhir_json)
        observation_id = upload_result.get("id")

        read_result = read_observation(observation_id)

        local_record = {
            "timestamp": timestamp,
            "patient_id": patient_id,
            "prediction": label,
            "confidence": round(confidence, 4),
            "fhir_upload_result": upload_result,
            "fhir_read_result": read_result
        }
        save_fhir_to_local(local_record)

        return jsonify({
            "status": "ok",
            "prediction": label,
            "confidence": round(confidence, 4),
            "timestamp": timestamp,
            "patient_id": patient_id,
            "observation_id": observation_id,
            "fhir": fhir_json,
            "fhir_upload_success": True
        })

    except Exception as e:
        print("Error in /predict-sequence:", e)
        return jsonify({
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)