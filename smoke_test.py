import time
import requests

BASE_URL = "https://remote-runtime-environment.onrender.com"

payload = {
    "problem_id": 1,
    "language": "python",
    "source_code": "import sys\ndef main():\n    lines = sys.stdin.read().split()\n    if not lines: return\n    print(int(lines[0]) + int(lines[1]))\nif __name__ == '__main__': main()\n"
}

def run():
    print("🚀 Submitting code to live Render backend...")
    res = requests.post(f"{BASE_URL}/submissions/", json=payload, timeout=10)
    sub_id = res.json().get("id") or res.json().get("submission_id")
    print(f"✅ Submission ID: {sub_id}\n⏳ Polling Redis queue for verdict...")
    
    for attempt in range(1, 15):
        data = requests.get(f"{BASE_URL}/submissions/{sub_id}", timeout=5).json()
        verdict = data.get("verdict", "PENDING")
        status = data.get("status", "QUEUED")
        print(f"   [{attempt}/15] Status: {status} | Verdict: {verdict}")
        if status in ["COMPLETED", "SUCCESS", "FAILED"] or verdict not in ["PENDING", "QUEUED", "RUNNING"]:
            print(f"\n🎉 FINAL RESULT: {verdict}")
            return
        time.sleep(2)

if __name__ == "__main__":
    run()
