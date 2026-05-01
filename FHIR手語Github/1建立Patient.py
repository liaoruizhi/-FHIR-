import requests

FHIR_BASE = "https://hapi.fhir.org/baseR4"

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

headers = {
    "Content-Type": "application/fhir+json",
    "Accept": "application/fhir+json"
}

response = requests.post(f"{FHIR_BASE}/Patient", headers=headers, json=patient_data)

print(response.status_code)
print(response.text)