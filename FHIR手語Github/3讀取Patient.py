import requests

FHIR_BASE = "https://hapi.fhir.org/baseR4"
patient_id = "131994547"

response = requests.get(
    f"{FHIR_BASE}/Patient/{patient_id}",
    headers={"Accept": "application/fhir+json"}
)

print(response.status_code)
print(response.text)