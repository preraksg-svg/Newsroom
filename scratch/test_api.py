
import requests

def test_api():
    try:
        r = requests.get("http://localhost:8000/api/news?status=Draft")
        print(f"Status Code: {r.status_code}")
        data = r.json()
        print(f"Success: {data.get('success')}")
        items = data.get('data', {}).get('items', [])
        print(f"Items found: {len(items)}")
        if items:
            print(f"First item title: {items[0]['fields'].get('title')}")
            print(f"First item status: {items[0]['fields'].get('status')}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_api()
