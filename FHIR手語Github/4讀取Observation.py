import requests

FHIR_BASE = "https://hapi.fhir.org/baseR4"
observation_id = "131998379"

response = requests.get(
    f"{FHIR_BASE}/Observation/{observation_id}",
    headers={"Accept": "application/fhir+json"}
)

print(response.status_code)
print(response.text)