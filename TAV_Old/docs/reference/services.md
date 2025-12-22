# Services Reference

Backend services for email and messaging integrations. These services are used internally by communication nodes but can also be used directly.

---

## IMAP Service

Located at `backend/app/services/imap_service.py`.

Handles email reading from various providers with automatic IMAP configuration.

### Supported Providers

| Provider | IMAP Server | Port | Notes |
|----------|-------------|------|-------|
| `gmail` | imap.gmail.com | 993 | Requires App Password |
| `outlook` | outlook.office365.com | 993 | Works with @outlook.com, @hotmail.com |
| `yahoo` | imap.mail.yahoo.com | 993 | Requires App Password |
| `office365` | outlook.office365.com | 993 | For enterprise Office 365 |
| `custom` | (user-specified) | 993 | Custom IMAP server |

### Usage

```python
from app.services.imap_service import get_imap_service

imap = get_imap_service()

# Fetch emails
emails = await imap.fetch_emails(
    email_address="user@gmail.com",
    password="app-password",        # App-specific password!
    provider="gmail",
    folder_name="INBOX",
    only_unread=True,
    filter_sender="important@company.com",
    filter_subject="Invoice",
    max_emails=10,
    mark_as_read=False
)

# Each email contains:
for email in emails:
    print(email["subject"])
    print(email["sender"])
    print(email["content"])         # Plain text body
    print(email["html_content"])    # HTML body (if available)
    print(email["attachments"])     # List of attachment info
```

### Email Object Structure

```python
{
    "subject": "Invoice #123",
    "sender": "billing@company.com",
    "to": "user@gmail.com",
    "cc": "manager@company.com",
    "content": "Please find attached...",
    "html_content": "<html>...</html>",
    "received_date": "Mon, 1 Jan 2024 10:00:00 +0000",
    "message_id": "<unique-id@mail.gmail.com>",
    "attachments": [
        {
            "filename": "invoice.pdf",
            "content_type": "application/pdf",
            "size": 12345
        }
    ]
}
```

### Test Connection

```python
result = await imap.test_connection(
    email_address="user@gmail.com",
    password="app-password",
    provider="gmail"
)

if result["success"]:
    print("Connected successfully!")
    print(result["details"])  # Server info, folder access, email count
else:
    print(f"Failed: {result['error']}")
    print(f"Help: {result['help']}")
```

### Custom IMAP Server

```python
emails = await imap.fetch_emails(
    email_address="user@company.com",
    password="password",
    provider="custom",
    imap_server="mail.company.com",
    imap_port=993
)
```

---

## SMTP Service

Located at `backend/app/services/smtp_service.py`.

Handles email sending with multi-provider support.

### Supported Providers

| Provider | SMTP Server | Port | TLS | Notes |
|----------|-------------|------|-----|-------|
| `gmail` | smtp.gmail.com | 587 | Yes | Requires App Password |
| `outlook` | smtp-mail.outlook.com | 587 | Yes | @outlook.com, @hotmail.com |
| `yahoo` | smtp.mail.yahoo.com | 587 | Yes | Requires App Password |
| `office365` | smtp.office365.com | 587 | Yes | Enterprise Office 365 |
| `custom` | (user-specified) | 587 | Yes | Custom SMTP server |

### Usage

```python
from app.services.smtp_service import get_smtp_service

smtp = get_smtp_service()

result = await smtp.send_email(
    to_addresses=["recipient@example.com"],
    subject="Hello from TAV!",
    body="This is a plain text email.",
    from_address="sender@gmail.com",
    from_name="TAV Engine",
    provider="gmail",
    smtp_password="app-password",
    
    # Optional
    html_body="<h1>Hello!</h1><p>This is HTML.</p>",
    cc_addresses=["cc@example.com"],
    bcc_addresses=["bcc@example.com"],
    reply_to="reply@example.com",
    attachments=[
        {"filename": "report.pdf", "path": "/path/to/report.pdf"},
        {"filename": "data.csv", "content": b"col1,col2\nval1,val2"}
    ]
)

if result["success"]:
    print(f"Sent to {result['recipients']}")
else:
    print(f"Failed: {result['error']}")
```

### Attachment Formats

```python
# From file path
{"filename": "report.pdf", "path": "/path/to/file.pdf"}

# From bytes
{"filename": "data.csv", "content": b"raw,bytes,here"}

# With MIME type
{"filename": "image.png", "content": image_bytes, "mimetype": "image/png"}
```

### Custom SMTP Server

```python
result = await smtp.send_email(
    to_addresses=["user@example.com"],
    subject="Test",
    body="Test email",
    from_address="sender@company.com",
    provider="custom",
    smtp_server="mail.company.com",
    smtp_port=587,
    smtp_username="sender@company.com",
    smtp_password="password",
    use_tls=True
)
```

---

## Twilio Service

Located at `backend/app/services/twilio_service.py`.

Handles WhatsApp and SMS messaging via Twilio API.

### Prerequisites

```bash
pip install twilio
```

### WhatsApp Messaging

```python
from app.services.twilio_service import get_twilio_service

twilio = get_twilio_service()

# Custom message
result = await twilio.send_whatsapp(
    to="+1234567890",               # Recipient phone number
    from_number="+14155238886",     # Your Twilio WhatsApp number
    account_sid="AC...",            # Twilio Account SID
    auth_token="...",               # Twilio Auth Token
    body="Your order has shipped!",
    media_url=["https://example.com/image.jpg"]  # Optional media
)

# Approved template (ContentSID)
result = await twilio.send_whatsapp(
    to="+1234567890",
    from_number="+14155238886",
    account_sid="AC...",
    auth_token="...",
    content_sid="HXabcd1234...",    # Your approved template SID
    content_variables={"1": "John", "2": "Passport"}  # Template variables
)

if result["success"]:
    print(f"Sent! SID: {result['message_sid']}")
    print(f"Status: {result['status']}")  # "queued", "sent", "delivered"
else:
    print(f"Failed: {result['error']}")
    print(f"Error code: {result.get('error_code')}")
```

### SMS Messaging

```python
result = await twilio.send_sms(
    to="+1234567890",
    body="Your verification code is 123456",
    from_number="+15558675309",     # Your Twilio phone number
    account_sid="AC...",
    auth_token="...",
    media_url=["https://example.com/image.jpg"]  # Optional (MMS)
)
```

### Check Message Status

```python
status = await twilio.get_message_status(
    message_sid="SM...",
    account_sid="AC...",
    auth_token="..."
)

print(status["status"])  # "queued", "sending", "sent", "delivered", "failed"
print(status["error_message"])  # If failed
```

### Message Status Values

| Status | Description |
|--------|-------------|
| `queued` | Message is queued for sending |
| `sending` | Message is being sent |
| `sent` | Message sent to carrier |
| `delivered` | Message delivered to recipient |
| `failed` | Message failed to send |
| `undelivered` | Carrier couldn't deliver |

---

## Usage in Nodes

These services are used internally by communication nodes:

| Node | Service Used |
|------|--------------|
| `email_polling_trigger` | IMAPService |
| `email_composer` | SMTPService |
| `whatsapp_send` | TwilioService |
| `whatsapp_listener` | TwilioService (webhook) |

### Example: Email Composer Node

```python
class EmailComposerNode(BaseNode):
    async def process(self, inputs, config, context):
        smtp = get_smtp_service()
        
        result = await smtp.send_email(
            to_addresses=config["to"].split(","),
            subject=config["subject"],
            body=inputs.get("body", ""),
            from_address=config["from_address"],
            provider=config.get("provider", "gmail"),
            smtp_password=config["password"]
        )
        
        return {"success": result["success"], "details": result}
```

---

## App Passwords

Most email providers require **App Passwords** instead of regular passwords when using IMAP/SMTP:

### Gmail

1. Go to Google Account → Security → 2-Step Verification
2. Scroll to "App passwords"
3. Generate new app password for "Mail"
4. Use this password in TAV

### Outlook/Office 365

1. Go to Security settings
2. Enable two-factor authentication
3. Create app password under "Additional security options"

### Yahoo

1. Go to Account Security
2. Enable two-step verification
3. Generate app password

---

## Error Handling

### IMAP Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "Authentication failed" | Wrong password | Use App Password, not regular password |
| "Connection refused" | Server unreachable | Check server address and port |
| "Timeout" | Slow network | Increase timeout or check connection |

### SMTP Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "Authentication failed" | Wrong credentials | Verify username and password |
| "SMTP server required" | Missing server | Specify server for custom provider |
| "Connection refused" | Server unreachable | Check server and port |

### Twilio Errors

| Error Code | Cause | Solution |
|------------|-------|----------|
| 20003 | Authentication failed | Verify Account SID and Auth Token |
| 21608 | Unverified recipient | Add number to verified list (trial) |
| 21211 | Invalid phone number | Check phone number format (+E.164) |
| 63016 | WhatsApp not enabled | Enable WhatsApp in Twilio console |

---

## Related Documentation

- [Built-in Nodes](built-in-nodes.md) - Email and WhatsApp nodes
- [Credentials](credentials.md) - Storing service credentials securely
- [Capabilities](capabilities.md) - TriggerCapability for polling

