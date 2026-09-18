import streamlit as st
import re
from faster_whisper import WhisperModel
import os
import json
import io
from datetime import datetime

import database as db
import auth
import notifications as notify

try:
    from streamlit_geolocation import streamlit_geolocation
    HAS_GEO = True
except ImportError:
    HAS_GEO = False

import plotly.express as px

# ============================================================
# CONFIG (env vars) — see README.md
# ============================================================
whisper_model = WhisperModel("tiny", device="cpu", compute_type="int8")
db.init_db()
auth.seed_default_admin()

st.set_page_config(page_title="ग्राम सेवा पोर्टल", layout="wide", page_icon="🇮🇳")

ASSETS_DIR, UPLOADS_DIR = "assets", "uploads"
os.makedirs(UPLOADS_DIR, exist_ok=True)



def extract_basic_details(text):
    """Free local extraction of name, village and ward from Hindi/Roman-Hindi text."""
    import re

    result = {
        "name": "",
        "village": "",
        "ward": "",
    }

    # Hindi + Roman Hindi name patterns
    name_patterns = [
        r"(?:मेरा नाम|नाम है)\s*[:\-]?\s*([^\n,।]+?)(?=\s+(?:है|हूँ|गाँव|गांव|ग्राम|वार्ड)|[।,\n]|$)",
        r"(?:my name is|my name)\s*[:\-]?\s*([^\n,.]+?)(?=\s+(?:is|and|village|gau|gaon|ward|baud)|[.,\n]|$)",
        r"(?:we are nam|naam|name)\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)",
    ]

    for pattern in name_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result["name"] = match.group(1).strip()
            break

    # Hindi + Roman Hindi village patterns
    village_patterns = [
        r"(?:गाँव|गांव|ग्राम)\s*(?:का नाम)?\s*[:\-]?\s*([^\s,।]+)",
        r"(?:gau|gaon|gram|village)\s+(?:ka naam\s+)?([A-Za-z]+)",
    ]

    for pattern in village_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            village = match.group(1).strip()
            if village.lower() not in ["hai", "is", "ka", "ki", "ke"]:
                result["village"] = village
                break

    # Hindi + Roman Hindi ward patterns
    ward_patterns = [
        r"(?:वार्ड|वॉर्ड)\s*(?:नंबर|नं\.?|संख्या)?\s*[:\-]?\s*(\d+)",
        r"(?:ward|baud|board)\s*(?:number|no\.?|num)?\s*[:\-]?\s*(\d+)",
    ]

    for pattern in ward_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result["ward"] = match.group(1)
            break

    return result


def asset(name):
    p = os.path.join(ASSETS_DIR, name)
    return p if os.path.exists(p) else None


# ---------------------------------------------------------------
# Styling
# ---------------------------------------------------------------
st.markdown("""
<style>
.main { background-color: #f5f6f8; }
.block-container { padding-top: 1rem; max-width: 1200px; }
.gov-topbar { background:#0b3d0b; color:white; padding:6px 16px; font-size:0.78rem;
    border-radius:6px 6px 0 0; display:flex; justify-content:space-between; flex-wrap:wrap; }
.tricolor-strip { height:5px; background:linear-gradient(90deg,#FF9933 33%,white 33%,white 66%,#138808 66%);
    border-radius:3px; margin:0.8rem 0 1.2rem 0; }
.grv-card { background:#fff; border-radius:14px; padding:1rem 1.2rem; margin-bottom:0.8rem;
    box-shadow:0 1px 4px rgba(0,0,0,0.08); border-left:6px solid #ccc; }
.grv-high { border-left-color:#e63946; } .grv-medium { border-left-color:#f4a300; } .grv-low { border-left-color:#2a9d8f; }
.badge { display:inline-block; padding:2px 10px; border-radius:999px; font-size:0.72rem; font-weight:600; color:white; }
.badge-Submitted { background:#6c757d; } .badge-InProgress { background:#f4a300; }
.badge-Resolved { background:#2a9d8f; } .badge-Closed { background:#343a40; }
.complaint-id { font-family:monospace; background:#eef0f2; padding:2px 8px; border-radius:6px; font-weight:700; }
@media (max-width: 640px) { .block-container { padding-left:0.6rem; padding-right:0.6rem; } }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="gov-topbar">
    <span>🇮🇳 भारत सरकार | Government of India</span>
    <span>राजस्थान सरकार | Government of Rajasthan</span>
</div>
""", unsafe_allow_html=True)

hcol1, hcol2 = st.columns([1, 5])
with hcol1:
    img = asset("pm_photo.jpg")
    if img:
        st.image(img, width=70)
with hcol2:
    st.markdown("### 🎙️ ग्राम सेवा — Rural Grievance Portal")
    st.caption("राजस्थान सरकार की पहल | निःशुल्क, ग्रामीणों के लिए")

st.markdown('<div class="tricolor-strip"></div>', unsafe_allow_html=True)

# ---------------------------------------------------------------
# Session state
# ---------------------------------------------------------------
st.session_state.setdefault("user", None)
st.session_state.setdefault("admin_phone", "")
st.session_state.setdefault("notify_sms", True)
st.session_state.setdefault("notify_whatsapp", True)
st.session_state.setdefault("gps", {"lat": None, "lon": None})

STATUS_BADGE_CLASS = {"Submitted": "badge-Submitted", "In Progress": "badge-InProgress",
                       "Resolved": "badge-Resolved", "Closed": "badge-Closed"}
URGENCY_ICON = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}
CATEGORIES = ["Water Supply", "Electricity", "Roads & Infrastructure", "Sanitation", "Others"]

# ---------------------------------------------------------------
# Sidebar — navigation + admin login
# ---------------------------------------------------------------
with st.sidebar:
    st.header("मेनू")
    page = st.radio("नेविगेशन", ["📝 शिकायत दर्ज करें", "🔍 शिकायत ट्रैक करें"],
                     label_visibility="collapsed")

with st.sidebar:
    st.markdown("---")
    st.subheader("🤖 Gram Seva AI Assistant")

    # Photo / poster
    assistant_img = asset("pm_photo.jpg")
    if assistant_img:
        st.image(assistant_img, use_container_width=True)

    intro_text = (
        "नमस्ते! आपका स्वागत है ग्राम सेवा पोर्टल में। "
        "ग्राम सेवा एक ग्रामीण शिकायत प्रबंधन प्रोजेक्ट है, "
        "जिसे माधव शुक्ला द्वारा बनाया गया है। "
        "इसका उद्देश्य ग्रामीण क्षेत्रों की समस्याओं को दर्ज करने और "
        "उनकी स्थिति को ट्रैक करने में मदद करना है। "
        "जैसे पानी की समस्या, जल रिसाव, बिजली, सड़क, सफाई, "
        "नाली, नदी या अन्य स्थानीय समस्याएँ। "
        "आप अपनी शिकायत लिखकर या अपनी आवाज़ में दर्ज कर सकते हैं। "
        "शिकायत जमा करने के बाद आपको एक Complaint ID मिलेगी, "
        "जिससे आप अपनी शिकायत का status track कर सकते हैं।"
    )

    # Auto voice introduction
    import streamlit.components.v1 as components

    voice_html = f"""
    <div style="font-family:Arial,sans-serif;padding:8px;">
        <div style="
            background:#f1f5f9;
            border-radius:12px;
            padding:12px;
            font-size:14px;
            line-height:1.5;
        ">
            <b>🔊 परिचय</b><br>
            ग्राम सेवा पोर्टल में आपका स्वागत है।
        </div>

        <button id="speakBtn" style="
            margin-top:8px;
            border:0;
            border-radius:8px;
            padding:8px 12px;
            background:#166534;
            color:white;
            cursor:pointer;
        ">🔊 सुनें</button>
    </div>

    <script>
    const intro = {intro_text!r};

    function speakIntro() {{
        if (!("speechSynthesis" in window)) return;

        window.speechSynthesis.cancel();

        const speech = new SpeechSynthesisUtterance(intro);
        speech.lang = "hi-IN";
        speech.rate = 0.92;
        speech.pitch = 1.0;
        speech.volume = 1.0;

        window.speechSynthesis.speak(speech);
    }}

    document.getElementById("speakBtn").onclick = speakIntro;

    // Automatically start when the assistant panel loads.
    setTimeout(speakIntro, 700);
    </script>
    """

    components.html(voice_html, height=155, scrolling=False)

    st.caption("Portal के बारे में कोई भी सवाल पूछ सकते हैं।")

    if "ai_messages" not in st.session_state:
        st.session_state.ai_messages = []

    for msg in st.session_state.ai_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    ai_prompt = st.chat_input(
        "Portal के बारे में पूछें...",
        key="gram_seva_ai_input"
    )

    if ai_prompt:
        st.session_state.ai_messages.append({
            "role": "user",
            "content": ai_prompt
        })

        try:
            from openai import OpenAI

            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            response = client.responses.create(
                model="gpt-4o-mini",
                instructions="""
You are the Gram Seva Portal AI Assistant.

Explain the Gram Seva portal clearly and briefly.

The portal is a student-built project by B.Tech student Madhav Shukla.
It helps citizens understand and submit rural/local complaints such as:
water supply problems, water leakage, electricity problems, roads,
sanitation, drainage, river/local environmental problems and other
local civic issues.

Explain:
- how to submit a complaint
- voice complaint
- complaint ID and tracking
- village and ward information
- photo/video evidence
- GPS/location
- complaint status
- SLA and escalation
- citizen notifications
- admin/officer dashboard

Answer in Hindi, English or Hinglish according to the user's question.

Do not invent complaint data or status.
Do not claim that this is an official government website.
Do not provide fake government schemes, officials, phone numbers or policies.
If a question is unrelated to the portal, politely say that you can
help explain the Gram Seva portal and its features.
""",
                input=ai_prompt
            )

            answer = response.output_text

        except Exception as e:
            answer = f"AI Assistant अभी उपलब्ध नहीं है: {e}"

        st.session_state.ai_messages.append({
            "role": "assistant",
            "content": answer
        })

        st.rerun()

# =================================================================
# PAGE 1 — Submit complaint
# =================================================================
if page == "📝 शिकायत दर्ज करें":
    st.header("🔊 अपनी शिकायत दर्ज करें")

    c1, c2 = st.columns(2)
    with c1:
        village_name = st.text_input("गाँव का नाम", "चन्दनपुर")
        ward = st.text_input("वार्ड / मोहल्ला (वैकल्पिक)")
        citizen_phone = st.text_input("आपका फ़ोन नंबर (स्टेटस अपडेट के लिए)", placeholder="+91XXXXXXXXXX")
    with c2:
        st.write("📍 **स्थान (GPS)**")
        if HAS_GEO:
            loc = streamlit_geolocation()
            if loc and loc.get("latitude"):
                st.session_state.gps = {"lat": loc["latitude"], "lon": loc["longitude"]}
                st.success(f"स्थान मिला: {loc['latitude']:.5f}, {loc['longitude']:.5f}")
        else:
            lat = st.number_input("Latitude (वैकल्पिक)", format="%.6f", value=0.0)
            lon = st.number_input("Longitude (वैकल्पिक)", format="%.6f", value=0.0)
            if lat and lon:
                st.session_state.gps = {"lat": lat, "lon": lon}

    st.subheader("🎤 अपनी शिकायत बोलकर दर्ज करें")
    complaint_text = st.text_area("📝 या अपनी शिकायत यहाँ लिखें", placeholder="उदाहरण: हमारे गाँव में 3 दिन से पानी नहीं आ रहा है।")
    st.caption("नीचे रिकॉर्ड बटन दबाएँ और अपनी शिकायत अपने शब्दों में बोलें।")

    audio_file = st.audio_input("🎙️ अपनी शिकायत रिकॉर्ड करें")

    audio_bytes = None

    if audio_file is not None:
        audio_bytes = audio_file.getvalue()
        st.success("✅ आपकी आवाज़ रिकॉर्ड हो गई है।")
        st.audio(audio_file)
    photo_file = st.file_uploader("📸 फ़ोटो सबूत (वैकल्पिक)", type=["jpg", "jpeg", "png"])
    video_file = st.file_uploader("🎥 वीडियो सबूत (वैकल्पिक)", type=["mp4", "mov"])

    if st.button("📤 शिकायत दर्ज करें", type="primary") and (audio_bytes or complaint_text.strip()):
        with st.spinner("🤖 AI शिकायत को समझ रहा है..."):

            if audio_bytes:
                st.write("🔊 Audio bytes:", len(audio_bytes))

                with open("temp_audio.wav", "wb") as f:
                    f.write(audio_bytes)

                st.audio("temp_audio.wav", format="audio/wav")

                segments, info = whisper_model.transcribe(
                    "temp_audio.wav",
                    language="hi",
                    task="transcribe",
                    beam_size=5,
                    vad_filter=True
                )

                user_text = " ".join(
                    segment.text for segment in segments
                ).strip()
                st.success(f"🎤 **पहचाना गया टेक्स्ट:** {user_text}")
                st.write("🔎 Debug transcription:", repr(user_text))
            else:
                user_text = complaint_text.strip()
                st.success(f"📝 **आपकी शिकायत:** {user_text}")

            prompt = f"""
            आप ग्राम सेवा पोर्टल के AI Assistant हैं।
            ग्रामीण की शिकायत को ध्यान से समझें और उपलब्ध जानकारी को JSON में निकालें।

            शिकायत:
            "{user_text}"

            JSON में केवल ये 7 Keys दें:

            1. "name" — व्यक्ति का नाम। अगर नाम नहीं बताया गया हो तो "" दें।
            2. "village" — गाँव का नाम। अगर नहीं बताया गया हो तो "" दें।
            3. "ward" — वार्ड/मोहल्ला नंबर या नाम। अगर नहीं बताया गया हो तो "" दें।
            4. "category" — केवल इनमें से एक:
               "Water Supply", "Electricity", "Roads & Infrastructure", "Sanitation", "Others"
            5. "urgency" — केवल इनमें से एक:
               "High", "Medium", "Low"
            6. "summary_hindi" — शिकायत का छोटा और स्पष्ट हिंदी सारांश।
            7. "complaint" — शिकायत का पूरा साफ़ किया हुआ विवरण हिंदी में।

            महत्वपूर्ण:
            - जानकारी अनुमान से न बनाएं।
            - जो जानकारी शिकायत में नहीं है उसे "" रखें।
            - category और urgency हमेशा दिए गए विकल्पों में से चुनें।
            - केवल valid JSON दें, कोई अतिरिक्त text नहीं।
            """
            # 🆓 Free local Auto-Fill (no OpenAI API required)
            text_lower = user_text.lower()

            if any(x in text_lower for x in ["पानी", "जल", "नल", "water"]):
                category = "Water Supply"
            elif any(x in text_lower for x in ["बिजली", "लाइट", "करंट", "electricity"]):
                category = "Electricity"
            elif any(x in text_lower for x in ["सड़क", "रोड", "गड्ढा", "road"]):
                category = "Roads & Infrastructure"
            elif any(x in text_lower for x in ["कचरा", "नाली", "सफाई", "शौचालय", "sanitation"]):
                category = "Sanitation"
            else:
                category = "Others"

            if any(x in text_lower for x in ["तुरंत", "बहुत जरूरी", "आपात", "आपातकाल", "3 दिन", "4 दिन", "5 दिन"]):
                urgency = "High"
            elif any(x in text_lower for x in ["जल्दी", "जरूरी", "समस्या"]):
                urgency = "Medium"
            else:
                urgency = "Low"

            # 🎯 Free local extraction: Name + Village + Ward
            basic_details = extract_basic_details(user_text)

            ai = {
                "name": basic_details.get("name", ""),
                "village": basic_details.get("village", "") or village_name or "",
                "ward": basic_details.get("ward", "") or ward or "",
                "category": category,
                "urgency": urgency,
                "summary_hindi": user_text[:150],
                "complaint": user_text,
            }

            # 🤖 AI Auto-Fill Preview
            st.subheader("🤖 AI द्वारा समझी गई जानकारी")
            st.info("कृपया जानकारी जाँच लें। AI द्वारा निकाली गई जानकारी को submit करने से पहले verify करें।")

            ai_name = st.text_input(
                "👤 नाम",
                value=ai.get("name", ""),
                key="ai_name"
            )
            ai_village = st.text_input(
                "🏠 गाँव",
                value=ai.get("village", "") or village_name,
                key="ai_village"
            )
            ai_ward = st.text_input(
                "🔢 वार्ड / मोहल्ला",
                value=ai.get("ward", "") or ward,
                key="ai_ward"
            )
            ai_category = st.selectbox(
                "📂 शिकायत की श्रेणी",
                CATEGORIES,
                index=CATEGORIES.index(ai.get("category", "Others"))
                    if ai.get("category", "Others") in CATEGORIES else CATEGORIES.index("Others"),
                key="ai_category"
            )
            ai_urgency = st.selectbox(
                "🚨 प्राथमिकता",
                ["High", "Medium", "Low"],
                index=["High", "Medium", "Low"].index(ai.get("urgency", "Medium"))
                    if ai.get("urgency", "Medium") in ["High", "Medium", "Low"] else 1,
                key="ai_urgency"
            )
            ai_summary = st.text_input(
                "📝 हिंदी सारांश",
                value=ai.get("summary_hindi", ""),
                key="ai_summary"
            )
            ai_complaint = st.text_area(
                "📄 पूरी शिकायत",
                value=ai.get("complaint", "") or user_text,
                key="ai_complaint"
            )

            photo_path = None
            if photo_file:
                photo_path = os.path.join(UPLOADS_DIR, f"{datetime.now().timestamp()}_{photo_file.name}")
                with open(photo_path, "wb") as f:
                    f.write(photo_file.getbuffer())
            video_path = None
            if video_file:
                video_path = os.path.join(UPLOADS_DIR, f"{datetime.now().timestamp()}_{video_file.name}")
                with open(video_path, "wb") as f:
                    f.write(video_file.getbuffer())

            # Save the verified AI preview in session state.
            st.session_state["phase1_pending_complaint"] = {
                "citizen_name": ai_name,
                "village": ai_village,
                "ward": ai_ward,
                "category": ai_category,
                "urgency": ai_urgency,
                "summary": ai_summary,
                "original_text": ai_complaint,
                "citizen_phone": citizen_phone,
                "latitude": st.session_state.gps["lat"],
                "longitude": st.session_state.gps["lon"],
                "photo_path": photo_path,
                "video_path": video_path,
            }

            st.success("✅ जानकारी तैयार है। ऊपर की जानकारी जाँचकर नीचे से अंतिम रूप से शिकायत दर्ज करें।")

    # Final confirmation: database में complaint तभी बनेगी जब citizen confirm करे.
    pending = st.session_state.get("phase1_pending_complaint")

    if pending:
        st.divider()
        st.subheader("✅ अंतिम पुष्टि")
        st.info("ऊपर दी गई जानकारी सही होने पर नीचे का बटन दबाएँ।")

        if st.button("✅ जानकारी सही है — शिकायत दर्ज करें", type="primary"):
            with st.spinner("शिकायत दर्ज की जा रही है..."):
                cid = db.create_complaint(**pending)

                complaint = db.get_complaint(cid)
                notify.notify_admin_new_complaint(
                    st.session_state.admin_phone,
                    complaint,
                    st.session_state.notify_sms,
                    st.session_state.notify_whatsapp,
                )

                st.session_state["phase1_pending_complaint"] = None

            st.balloons()
            st.success(
                f"🎉 शिकायत दर्ज हो गई! आपकी **Complaint ID: {cid}** है — इसे सुरक्षित रखें।"
            )

# =================================================================
# PAGE 2 — Track complaint (public, by ID)
# =================================================================
elif page == "🔍 शिकायत ट्रैक करें":
    st.header("🔍 अपनी शिकायत ट्रैक करें")
    cid = st.text_input("Complaint ID डालें (जैसे GRV-A1B2C3)").strip().upper()
    if st.button("खोजें") and cid:
        c = db.get_complaint(cid)
        if not c:
            st.error("यह Complaint ID नहीं मिला। कृपया जांचें।")
        else:
            badge = STATUS_BADGE_CLASS.get(c["status"], "badge-Submitted")
            st.markdown(f"""
            <div class="grv-card">
                <span class="complaint-id">{c['id']}</span>
                &nbsp; <span class="badge {badge}">{c['status']}</span><br><br>
                <b>गाँव:</b> {c['village']} {('· वार्ड: ' + c['ward']) if c['ward'] else ''}<br>
                <b>श्रेणी:</b> {c['category']} &nbsp; <b>प्राथमिकता:</b> {URGENCY_ICON.get(c['urgency'],'')} {c['urgency']}<br>
                <b>सारांश:</b> {c['summary']}<br>
                <b>दर्ज किया गया:</b> {c['created_at']} &nbsp; <b>अंतिम अपडेट:</b> {c['updated_at']}<br>
                {'<b>अधिकारी टिप्पणी:</b> ' + c['resolution_notes'] if c['resolution_notes'] else ''}
            </div>
            """, unsafe_allow_html=True)
            if c["photo_path"] and os.path.exists(c["photo_path"]):
                st.image(c["photo_path"], caption="सबूत फ़ोटो", width=300)
            if c["video_path"] and os.path.exists(c["video_path"]):
                st.video(c["video_path"])

# =================================================================
# Admin / Officer Portal has been separated into admin_app.py

st.markdown("""
<footer style="text-align:center; color:#666; font-size:0.8rem; margin-top:2rem; padding:1rem;">
    © राजस्थान सरकार | Government of Rajasthan · डिजिटल ग्रामीण सेवा पहल<br>
    Developed &amp; Designed by Madhav Shukla
</footer>
""", unsafe_allow_html=True)
