import base64
import re
from bs4 import BeautifulSoup
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

# Load Gmail API credentials
creds = Credentials.from_authorized_user_file(
    "token.json", ["https://www.googleapis.com/auth/gmail.readonly"]
)
service = build('gmail', 'v1', credentials=creds)

def extract_body(payload):
    if 'parts' in payload:
        for part in payload['parts']:
            result = extract_body(part)
            if result:
                return result
    if payload.get("mimeType") in ["text/plain", "text/html"]:
        data = payload["body"].get("data")
        if data:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
    return None

def clean_body(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    text = soup.get_text("\n", strip=True)

    # Remove disclaimers and signatures
    text = re.split(r"This email message and any documents attached", text, flags=re.IGNORECASE)[0]

    # Remove signature patterns
    signature_patterns = [
        r"^thanks\b",
        r"^regards\b",
        r"^\w+\s+\w+$",   # names
        r"\bdeveloper\b",
        r"@[\w\.-]+",     # email addresses
        r"www\.",         # websites
    ]

    lines = []
    for line in text.split("\n"):
        if any(re.search(pattern, line.strip(), re.IGNORECASE) for pattern in signature_patterns):
            continue  # Skip signature lines
        if line.strip():
            lines.append(line.strip())

    return "\n".join(lines)

def get_latest_emails(n=5):
    results = service.users().messages().list(userId='me', maxResults=n).execute()
    messages = results.get('messages', [])

    for msg in messages:
        msg_data = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
        headers = msg_data['payload']['headers']

        sender_email = None
        for h in headers:
            if h['name'].lower() == 'from':
                match = re.search(r'<(.+?)>', h['value'])
                sender_email = match.group(1) if match else h['value']
                break

        decoded_body = extract_body(msg_data['payload'])
        if decoded_body:
            cleaned_body = clean_body(decoded_body)
            print(f"{sender_email}\n{cleaned_body}\n{'-'*40}")

# Run
get_latest_emails(5)
