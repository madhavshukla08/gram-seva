"""
notifications.py — SMS / WhatsApp / Voice call via Twilio.
All functions fail soft: they return (ok: bool, message: str) instead of
raising, so a missing Twilio config never crashes the Streamlit app.
"""

import os
from twilio.rest import Client as TwilioClient


def _client():
    sid = os.environ.get("TWILIO_ACCOUNT_SID")
    token = os.environ.get("TWILIO_AUTH_TOKEN")
    if not (sid and token):
        return None
    return TwilioClient(sid, token)


def send_sms(to_phone, body):
    tw = _client()
    sms_from = os.environ.get("TWILIO_SMS_FROM")
    if not tw:
        return False, "Twilio credentials सेट नहीं हैं।"
    if not sms_from:
        return False, "TWILIO_SMS_FROM सेट नहीं है।"
    if not to_phone:
        return False, "फ़ोन नंबर नहीं दिया गया।"
    try:
        tw.messages.create(body=body, from_=sms_from, to=to_phone)
        return True, "SMS भेज दिया गया।"
    except Exception as e:
        return False, f"SMS त्रुटि: {e}"


def send_whatsapp(to_phone, body):
    tw = _client()
    wa_from = os.environ.get("TWILIO_WHATSAPP_FROM")
    if not tw:
        return False, "Twilio credentials सेट नहीं हैं।"
    if not wa_from:
        return False, "TWILIO_WHATSAPP_FROM सेट नहीं है।"
    if not to_phone:
        return False, "फ़ोन नंबर नहीं दिया गया।"
    try:
        tw.messages.create(body=body, from_=f"whatsapp:{wa_from}", to=f"whatsapp:{to_phone}")
        return True, "WhatsApp मैसेज भेज दिया गया।"
    except Exception as e:
        return False, f"WhatsApp त्रुटि: {e}"


def make_voice_call(to_phone, spoken_text):
    """Places a call that reads `spoken_text` aloud using Twilio's <Say> TwiML."""
    tw = _client()
    voice_from = os.environ.get("TWILIO_VOICE_FROM") or os.environ.get("TWILIO_SMS_FROM")
    if not tw:
        return False, "Twilio credentials सेट नहीं हैं।"
    if not voice_from:
        return False, "TWILIO_VOICE_FROM / TWILIO_SMS_FROM सेट नहीं है।"
    if not to_phone:
        return False, "फ़ोन नंबर नहीं दिया गया।"
    twiml = f'<Response><Say language="hi-IN">{spoken_text}</Say></Response>'
    try:
        tw.calls.create(twiml=twiml, from_=voice_from, to=to_phone)
        return True, "वॉयस कॉल भेजी जा रही है।"
    except Exception as e:
        return False, f"कॉल त्रुटि: {e}"


def notify_admin_new_complaint(admin_phone, complaint, use_sms, use_whatsapp):
    body = (
        f"🆕 नई शिकायत {complaint['id']}\n"
        f"गाँव: {complaint['village']}\n"
        f"श्रेणी: {complaint['category']} | प्राथमिकता: {complaint['urgency']}\n"
        f"विवरण: {(complaint['original_text'] or '')[:120]}"
    )
    results = []
    if use_sms:
        results.append(send_sms(admin_phone, body))
    if use_whatsapp:
        results.append(send_whatsapp(admin_phone, body))
    return results


def notify_citizen_status_update(citizen_phone, complaint):
    body = (
        f"📋 शिकायत अपडेट — {complaint['id']}\n"
        f"स्थिति: {complaint['status']}\n"
        f"{('टिप्पणी: ' + complaint['resolution_notes']) if complaint.get('resolution_notes') else ''}"
    )
    return send_sms(citizen_phone, body)
