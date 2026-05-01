import requests
from datetime import datetime
import re

FHIR_BASE = "https://hapi.fhir.org/baseR4"

HEADERS = {
    "Content-Type": "application/fhir+json",
    "Accept": "application/fhir+json"
}


def create_patient():
    patient_data = {
        "resourceType": "Patient",
        "name": [
            {
                "family": "Liao",
                "given": ["Ruizhi"]
            }
        ],
        "gender": "male",
        "birthDate": "2008-01-01"
    }

    response = requests.post(
        f"{FHIR_BASE}/Patient",
        headers=HEADERS,
        json=patient_data
    )

    print("\n========== 1. 建立 Patient ==========")
    print("狀態碼:", response.status_code)
    print(response.text)

    if response.status_code in [200, 201]:
        data = response.json()
        return data.get("id")

    if response.status_code == 412:
        text = response.text
        match = re.search(r"Patient/(\d+)", text)
        if match:
            existing_patient_id = match.group(1)
            print(f"\n偵測到重複 Patient，改用既有 Patient id: {existing_patient_id}")
            return existing_patient_id

    raise Exception("建立 Patient 失敗")


def create_observation(patient_id):
    observation_data = {
        "resourceType": "Observation",
        "status": "final",
        "code": {
            "text": "手語辨識"
        },
        "subject": {
            "reference": f"Patient/{patient_id}"
        },
        "effectiveDateTime": datetime.now().isoformat(),
        "valueString": "你好"
    }

    response = requests.post(
        f"{FHIR_BASE}/Observation",
        headers=HEADERS,
        json=observation_data
    )

    print("\n========== 2. 上傳 Observation ==========")
    print("狀態碼:", response.status_code)
    print(response.text)

    if response.status_code not in [200, 201]:
        raise Exception("上傳 Observation 失敗")

    data = response.json()
    return data.get("id")


def read_patient(patient_id):
    response = requests.get(
        f"{FHIR_BASE}/Patient/{patient_id}",
        headers={"Accept": "application/fhir+json"}
    )

    print("\n========== 3. 讀取 Patient ==========")
    print("狀態碼:", response.status_code)
    print(response.text)

    if response.status_code != 200:
        raise Exception("讀取 Patient 失敗")


def read_observation(observation_id):
    response = requests.get(
        f"{FHIR_BASE}/Observation/{observation_id}",
        headers={"Accept": "application/fhir+json"}
    )

    print("\n========== 4. 讀取 Observation ==========")
    print("狀態碼:", response.status_code)
    print(response.text)

    if response.status_code != 200:
        raise Exception("讀取 Observation 失敗")


def main():
    try:
        patient_id = create_patient()
        print("\n成功取得 Patient id:", patient_id)

        observation_id = create_observation(patient_id)
        print("\n成功取得 Observation id:", observation_id)

        read_patient(patient_id)
        read_observation(observation_id)

        print("\n========== 測試完成 ==========")
        print("FHIR 與 HAPI FHIR Server 的上傳與讀取流程全部成功")
        print("Patient id:", patient_id)
        print("Observation id:", observation_id)

    except Exception as e:
        print("\n========== 測試失敗 ==========")
        print("錯誤原因:", str(e))


if __name__ == "__main__":
    main()