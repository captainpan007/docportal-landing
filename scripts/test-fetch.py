import requests, re, time

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}

url = 'https://proadvisor.intuit.com/app/accountant/search?searchId=pooja-r-loomba-cpa'
resp = requests.get(url, headers=headers, timeout=15)
print(f"Status: {resp.status_code}")
print(f"Content length: {len(resp.text)}")
print(f"First 500 chars: {resp.text[:500]}")

emails = re.findall(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', resp.text)
print(f"Emails found: {emails}")
