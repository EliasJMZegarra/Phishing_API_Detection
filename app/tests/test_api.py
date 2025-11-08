from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_healthcheck():
    """Verifica que el endpoint /healthcheck funcione correctamente"""
    response = client.get("/healthcheck")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data and data["status"] == "ok"


def test_predict_safe_email():
    """Prueba un correo legítimo"""
    data = {"text": "Dear Mr. Suana, your booking for flight XY123 is confirmed."}
    response = client.post("/predict", json=data)
    assert response.status_code == 200
    json_data = response.json()
    assert "predicted_label" in json_data
    assert "confidence" in json_data
    assert json_data["predicted_label"] in ["Safe Email", "Phishing Email"]

def test_predict_phishing_email():
    """Prueba un correo de phishing"""
    data = {"text": "Your account has been suspended. Verify immediately: http://fakebank.com"}
    response = client.post("/predict", json=data)
    assert response.status_code == 200
    json_data = response.json()
    assert "predicted_label" in json_data
    assert "confidence" in json_data
    assert json_data["predicted_label"] in ["Safe Email", "Phishing Email"]

def test_empty_text():
    """Prueba cuando el texto está vacío"""
    data = {"text": ""}
    response = client.post("/predict", json=data)
    assert response.status_code == 200  # o 400 si decides manejarlo como error
    data = response.json()
    assert "error" in data
    assert "vacío" in data["error"]

def test_predict_phishing_advanced():
    """Prueba un correo de phishing más complejo (enlace + urgencia)"""
    data = {
        "text": (
            "Subject: Urgent - Verify your account\n"
            "From: support@bank-example.com\n\n"
            "Dear customer,\n"
            "We detected suspicious login attempts. Verify immediately at: "
            "https://bank-example.verify-now.com/login?user=123\n"
            "Failure to do so will result in suspension."
        )
    }
    response = client.post("/predict", json=data)
    assert response.status_code == 200
    json_data = response.json()
    assert "predicted_label" in json_data
    assert "confidence" in json_data
    assert json_data["predicted_label"] in ["Safe Email", "Phishing Email"]
