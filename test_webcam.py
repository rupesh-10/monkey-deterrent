import requests
import json

def test_webcam():
    url = "http://127.0.0.1:5050/webcam"
    headers = {"Content-Type": "application/json"}
    data = {"action": "start"}
    
    print("Testing webcam start...")
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_webcam()
