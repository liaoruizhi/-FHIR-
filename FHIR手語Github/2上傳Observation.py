import requests
from datetime import datetime

FHIR_BASE = "https://hapi.fhir.org/baseR4"
patient_id = "131994547"

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

headers = {
    "Content-Type": "application/fhir+json",
    "Accept": "application/fhir+json"
}

response = requests.post(
    f"{FHIR_BASE}/Observation",
    headers=headers,
    json=observation_data
)

print(response.status_code)
print(response.text)