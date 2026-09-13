# ग्राम सेवा — Rural Grievance Portal (v2)

## नया क्या है (What's new)
| Feature | Status |
|---|---|
| Voice complaint → Hindi transcription | ✅ (Whisper) |
| AI category + urgency + summary | ✅ (GPT-4o-mini) |
| Village-wise complaints | ✅ filter in dashboard |
| Admin dashboard | ✅ |
| Analytics / charts | ✅ Plotly: category, urgency, village, status, daily trend |
| Mobile-friendly UI | ✅ responsive CSS |
| Twilio SMS / WhatsApp / **Voice call** | ✅ `notifications.py` |
| Login + admin/officer roles | ✅ `auth.py`, seeded admin/admin123 |
| Real database | ✅ SQLite (`gram_seva.db`), replaces session_state |
| Complaint location / GPS | ✅ `streamlit-geolocation` (falls back to manual lat/lon) |
| Complaint ID + tracking | ✅ `GRV-XXXXXX`, public tracking page |
| Photo/video evidence | ✅ saved to `uploads/` |
| Resolution workflow | ✅ Submitted → In Progress → Resolved → Closed |
| Citizen status notification | ✅ SMS sent on every status change |

## Setup

```bash
pip install -r requirements.txt
```

### Environment variables
```bash
export OPENAI_API_KEY="sk-..."
export TWILIO_ACCOUNT_SID="AC..."
export TWILIO_AUTH_TOKEN="..."
export TWILIO_SMS_FROM="+1XXXXXXXXXX"
export TWILIO_WHATSAPP_FROM="+14155238886"   # Twilio WhatsApp sandbox or approved number
export TWILIO_VOICE_FROM="+1XXXXXXXXXX"      # optional, falls back to TWILIO_SMS_FROM
```

### Run
```bash
streamlit run app.py
```

### First login
- Username: `admin`
- Password: `admin123`
- **Change this immediately** — add a proper "change password" flow or create new users via `auth.create_user()` before putting this anywhere near real citizens' data.

## Folder structure
```
gram_seva_v2/
├── app.py              # main Streamlit app (3 pages: submit, track, admin)
├── database.py          # SQLite layer
├── auth.py               # login/roles
├── notifications.py     # Twilio SMS/WhatsApp/voice
├── requirements.txt
├── assets/              # pm_photo.jpg, cm_photo.jpg, emblems
├── uploads/              # citizen photo/video evidence (auto-created)
└── gram_seva.db          # SQLite database (auto-created on first run)
```

## Known limitations / before real production use
- Password hashing is salted SHA-256, not bcrypt/argon2 — fine for a demo, not for a real government deployment.
- No rate limiting, CSRF protection, or HTTPS enforcement — put this behind a proper reverse proxy and auth layer before going live.
- `streamlit-geolocation` needs the citizen's browser to grant location permission; it will silently do nothing if denied — the manual lat/lon fields are the fallback.
- SQLite is fine for a pilot; move to Postgres before scaling to many concurrent panchayats.
- Voice calls use Twilio's built-in Hindi text-to-speech (`<Say language="hi-IN">`), which is understandable but robotic — for a real citizen-facing deployment, consider a pre-recorded human voice message instead.
