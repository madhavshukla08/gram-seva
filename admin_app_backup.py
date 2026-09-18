import streamlit as st
import os
from datetime import datetime

import database as db
import auth
import notifications as notify
import plotly.express as px

st.set_page_config(
    page_title="ग्राम सेवा — Admin Portal",
    layout="wide",
    page_icon="🔐"
)

db.init_db()
auth.seed_default_admin()

st.session_state.setdefault("user", None)

STATUS_BADGE_CLASS = {
    "Submitted": "badge-Submitted",
    "In Progress": "badge-InProgress",
    "Resolved": "badge-Resolved",
    "Closed": "badge-Closed",
}

URGENCY_ICON = {
    "High": "🔴",
    "Medium": "🟡",
    "Low": "🟢",
}

st.markdown("""
<style>

/* =========================================================
   GRAM SEVA ADMIN PORTAL — PREMIUM GOVERNMENT STYLE UI
   ========================================================= */

.stApp {
    background:
        radial-gradient(circle at 15% 10%, rgba(255,153,51,0.12), transparent 28%),
        radial-gradient(circle at 85% 10%, rgba(19,136,8,0.12), transparent 28%),
        linear-gradient(135deg, #f7f9fc 0%, #eef2f7 100%);
}

/* Top government bar */
.gov-topbar {
    background: linear-gradient(90deg, #123b18, #0b5d25, #123b18);
    color: white;
    padding: 9px 18px;
    font-size: 0.82rem;
    font-weight: 600;
    border-radius: 12px 12px 0 0;
    display: flex;
    justify-content: space-between;
    flex-wrap: wrap;
    box-shadow: 0 5px 18px rgba(0,0,0,0.12);
}

/* Tricolor line */
.tricolor-strip {
    height: 5px;
    background: linear-gradient(
        90deg,
        #FF9933 33%,
        #ffffff 33%,
        #ffffff 66%,
        #138808 66%
    );
    border-radius: 5px;
    margin: 10px 0 20px 0;
}

/* Hero area */
.admin-hero {
    background:
        linear-gradient(
            135deg,
            rgba(255,255,255,0.96),
            rgba(245,248,252,0.94)
        );
    border: 1px solid rgba(0,0,0,0.07);
    border-radius: 24px;
    padding: 22px 25px 26px 25px;
    margin-bottom: 22px;
    box-shadow:
        0 12px 35px rgba(20,40,60,0.10),
        inset 0 1px 0 rgba(255,255,255,0.9);
    position: relative;
    overflow: hidden;
}

.admin-hero::before {
    content: "";
    position: absolute;
    left: 0;
    top: 0;
    width: 100%;
    height: 5px;
    background: linear-gradient(
        90deg,
        #FF9933 0%,
        #FF9933 33%,
        #ffffff 33%,
        #ffffff 66%,
        #138808 66%,
        #138808 100%
    );
}

.admin-photo-card {
    background: rgba(255,255,255,0.82);
    border-radius: 18px;
    padding: 12px;
    text-align: center;
    border: 1px solid rgba(0,0,0,0.08);
    box-shadow: 0 8px 22px rgba(0,0,0,0.10);
}

.admin-photo-card img {
    width: 100%;
    max-width: 145px;
    height: 145px;
    object-fit: cover;
    border-radius: 16px;
    border: 3px solid white;
    box-shadow: 0 5px 15px rgba(0,0,0,0.16);
}

.admin-photo-label {
    margin-top: 8px;
    font-size: 0.78rem;
    font-weight: 700;
    color: #3d4650;
}

/* Main portal branding */
.admin-brand {
    text-align: center;
    padding: 8px 10px;
}

.admin-brand .small-title {
    font-size: 0.82rem;
    letter-spacing: 3px;
    font-weight: 700;
    color: #68727d;
    text-transform: uppercase;
}

.admin-brand .main-title {
    font-size: clamp(2rem, 5vw, 3.4rem);
    line-height: 1.05;
    font-weight: 900;
    letter-spacing: -1px;
    margin: 7px 0;
    background: linear-gradient(90deg, #0b3d0b, #1b6d32, #0b3d0b);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.admin-brand .portal-title {
    font-size: clamp(1rem, 2.5vw, 1.35rem);
    font-weight: 800;
    letter-spacing: 4px;
    color: #263238;
}

.admin-brand .description {
    color: #6b747d;
    margin-top: 8px;
    font-size: 0.88rem;
}

/* Login heading */
.login-heading {
    text-align: center;
    margin: 18px 0 10px 0;
}

.login-heading .secure {
    font-size: clamp(1.8rem, 4vw, 2.7rem);
    font-weight: 900;
    letter-spacing: 2px;
    color: #17212b;
}

.login-heading .subtitle {
    color: #68727d;
    font-size: 0.9rem;
    margin-top: 3px;
}


/* =========================================================
   PROFESSIONAL WELCOME PROFILE
   ========================================================= */

.welcome-profile {
    background: linear-gradient(
        135deg,
        rgba(255,255,255,0.98),
        rgba(244,248,246,0.96)
    );
    border: 1px solid rgba(27,109,50,0.16);
    border-left: 5px solid #1b6d32;
    border-radius: 18px;
    padding: 18px 22px;
    margin: 8px 0 22px 0;
    box-shadow:
        0 8px 24px rgba(20,40,60,0.08),
        inset 0 1px 0 rgba(255,255,255,0.9);
}

.welcome-profile-content {
    width: 100%;
}

.welcome-label {
    font-size: 0.72rem;
    font-weight: 800;
    letter-spacing: 2px;
    color: #6b747d;
    margin-bottom: 4px;
}

.welcome-name {
    font-size: clamp(1.55rem, 3vw, 2.15rem);
    font-weight: 900;
    color: #17351e;
    line-height: 1.2;
    margin-bottom: 10px;
}

.welcome-meta {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    align-items: center;
}

.profile-role,
.profile-email {
    display: inline-flex;
    align-items: center;
    padding: 7px 12px;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 700;
}

.profile-role {
    background: rgba(27,109,50,0.10);
    color: #175b2b;
    border: 1px solid rgba(27,109,50,0.15);
}

.profile-email {
    background: rgba(0,0,0,0.035);
    color: #4e5963;
    border: 1px solid rgba(0,0,0,0.07);
    word-break: break-all;
}

@media (max-width: 700px) {
    .welcome-profile {
        padding: 15px 16px;
    }

    .welcome-meta {
        flex-direction: column;
        align-items: flex-start;
    }

    .profile-email {
        max-width: 100%;
    }
}

/* Login form styling */
div[data-testid="stTextInput"] input {
    border-radius: 12px !important;
    border: 1px solid #d5dce3 !important;
    padding: 12px 14px !important;
    background: rgba(255,255,255,0.96) !important;
}

div[data-testid="stTextInput"] input:focus {
    border-color: #1b6d32 !important;
    box-shadow: 0 0 0 2px rgba(27,109,50,0.12) !important;
}

div[data-testid="stButton"] button {
    border-radius: 12px !important;
    font-weight: 750 !important;
    min-height: 44px !important;
    transition: all 0.2s ease !important;
}

div[data-testid="stButton"] button:hover {
    transform: translateY(-1px);
    box-shadow: 0 7px 18px rgba(0,0,0,0.12);
}

/* Existing complaint cards */
.grv-card {
    background:#fff;
    border-radius:14px;
    padding:1rem 1.2rem;
    margin-bottom:0.8rem;
    box-shadow:0 1px 4px rgba(0,0,0,0.08);
    border-left:6px solid #ccc;
}

.grv-high { border-left-color:#e63946; }
.grv-medium { border-left-color:#f4a300; }
.grv-low { border-left-color:#2a9d8f; }

.badge {
    display:inline-block;
    padding:2px 10px;
    border-radius:999px;
    font-size:0.72rem;
    font-weight:600;
    color:white;
}

.badge-Submitted { background:#6c757d; }
.badge-InProgress { background:#f4a300; }
.badge-Resolved { background:#2a9d8f; }
.badge-Closed { background:#343a40; }

.complaint-id {
    font-family:monospace;
    background:#eef0f2;
    padding:2px 8px;
    border-radius:6px;
    font-weight:700;
}

/* =========================================================
   MOBILE HEADER — RESPONSIVE
   ========================================================= */
@media (max-width: 700px) {

    .admin-hero {
        padding: 12px 10px 16px 10px;
        border-radius: 16px;
        margin: 0 4px 12px 4px;
    }

    /* Header columns become compact */
    .admin-hero [data-testid="column"] {
        padding: 2px 4px !important;
    }

    .admin-photo-card {
        margin: 0 auto;
        text-align: center;
    }

    .admin-photo-card img {
        max-width: 78px !important;
        height: 78px !important;
        object-fit: cover;
        border-radius: 12px;
    }

    .admin-photo-label {
        font-size: 10px !important;
        line-height: 1.25 !important;
        margin-top: 4px !important;
    }

    .admin-brand {
        text-align: center;
        padding: 4px 2px !important;
    }

    .admin-brand .small-title {
        font-size: 8px !important;
        letter-spacing: 1px !important;
        line-height: 1.2 !important;
    }

    .admin-brand .main-title {
        font-size: 28px !important;
        line-height: 1.1 !important;
        margin: 3px 0 !important;
    }

    .admin-brand .portal-title {
        font-size: 10px !important;
        letter-spacing: 1px !important;
        line-height: 1.3 !important;
    }

    .admin-brand .description {
        font-size: 9px !important;
        line-height: 1.35 !important;
        margin-top: 4px !important;
    }
}

/* Very small phones */
@media (max-width: 420px) {

    .admin-hero {
        padding: 9px 6px 12px 6px;
        border-radius: 14px;
    }

    .admin-photo-card img {
        max-width: 62px !important;
        height: 62px !important;
        border-radius: 10px;
    }

    .admin-photo-label {
        font-size: 8px !important;
    }

    .admin-brand .small-title {
        font-size: 7px !important;
        letter-spacing: 0.7px !important;
    }

    .admin-brand .main-title {
        font-size: 23px !important;
    }

    .admin-brand .portal-title {
        font-size: 8px !important;
        letter-spacing: 0.7px !important;
    }

    .admin-brand .description {
        font-size: 8px !important;
    }
}


/* =========================================================
   PROFESSIONAL DASHBOARD OVERVIEW
   ========================================================= */

.dashboard-overview {
    background: linear-gradient(135deg, #ffffff, #f5f8fb);
    border: 1px solid rgba(0,0,0,0.07);
    border-radius: 20px;
    padding: 20px 22px;
    margin: 18px 0 18px 0;
    box-shadow: 0 8px 25px rgba(20,40,60,0.08);
}

.dashboard-title {
    font-size: 1.55rem;
    font-weight: 850;
    color: #17351d;
    margin-bottom: 3px;
}

.dashboard-subtitle {
    color: #6b747d;
    font-size: 0.86rem;
    margin-bottom: 16px;
}

.kpi-grid {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 12px;
}

.kpi-card {
    background: rgba(255,255,255,0.95);
    border: 1px solid #e1e7ec;
    border-radius: 15px;
    padding: 15px;
    min-height: 90px;
}

.kpi-label {
    font-size: 0.76rem;
    color: #68727d;
    font-weight: 700;
}

.kpi-value {
    font-size: 1.65rem;
    font-weight: 900;
    color: #17212b;
    margin-top: 5px;
}

/* =========================================================
   MOBILE KPI CARDS
   ========================================================= */

@media (max-width: 900px) {
    .dashboard-overview {
        padding: 16px 14px;
        border-radius: 16px;
    }

    .kpi-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 10px;
    }

    .kpi-card {
        min-height: 82px;
        padding: 12px;
        border-radius: 13px;
    }

    .kpi-label {
        font-size: 0.68rem;
    }

    .kpi-value {
        font-size: 1.45rem;
    }

    .kpi-note {
        font-size: 0.65rem;
    }
}

@media (max-width: 520px) {
    .dashboard-overview {
        padding: 13px 10px;
        margin: 12px 0;
        border-radius: 14px;
    }

    .dashboard-title {
        font-size: 1.25rem;
    }

    .dashboard-subtitle {
        font-size: 0.72rem;
        margin-bottom: 11px;
    }

    .kpi-grid {
        grid-template-columns: 1fr;
        gap: 8px;
    }

    .kpi-card {
        min-height: 68px;
        padding: 10px 12px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }

    .kpi-label {
        font-size: 0.68rem;
    }

    .kpi-value {
        font-size: 1.35rem;
        margin-top: 2px;
    }

    .kpi-note {
        font-size: 0.62rem;
    }
}

.kpi-note {
    font-size: 0.7rem;
    color: #7b858e;
    margin-top: 2px;
}

@media (max-width: 900px) {
    .kpi-grid {
        grid-template-columns: repeat(2, 1fr);
    }
}

@media (max-width: 500px) {
    .kpi-grid {
        grid-template-columns: 1fr;
    }
}

</style>
""", unsafe_allow_html=True)

# ============================================================
# GOVERNMENT HEADER
# ============================================================

st.markdown("""
<div class="gov-topbar">
    <span>🇮🇳 भारत सरकार | Government of India</span>
    <span>राजस्थान सरकार | Government of Rajasthan</span>
</div>
<div class="tricolor-strip"></div>
""", unsafe_allow_html=True)

# ============================================================
# PM / CM + PORTAL BRANDING
# ============================================================

pm_photo = "assets/pm_photo.jpg"
cm_photo = "assets/cm_photo.jpg"

h1, h2, h3 = st.columns([1.15, 3.7, 1.15])

with h1:
    if os.path.exists(pm_photo):
        st.markdown('<div class="admin-photo-card">', unsafe_allow_html=True)
        st.image(pm_photo, use_container_width=True)
        st.markdown(
            '<div class="admin-photo-label">माननीय प्रधानमंत्री<br>भारत सरकार</div>',
            unsafe_allow_html=True
        )
        st.markdown('</div>', unsafe_allow_html=True)

with h2:
    st.markdown("""
    <div class="admin-brand">
        <div class="small-title">RURAL GRIEVANCE MANAGEMENT</div>
        <div class="main-title">ग्राम सेवा</div>
        <div class="portal-title">ADMIN / OFFICER PORTAL</div>
        <div class="description">
            सुरक्षित प्रशासनिक एवं शिकायत प्रबंधन प्रणाली
        </div>
    </div>
    """, unsafe_allow_html=True)

with h3:
    if os.path.exists(cm_photo):
        st.markdown('<div class="admin-photo-card">', unsafe_allow_html=True)
        st.image(cm_photo, use_container_width=True)
        st.markdown(
            '<div class="admin-photo-label">माननीय मुख्यमंत्री<br>राजस्थान</div>',
            unsafe_allow_html=True
        )
        st.markdown('</div>', unsafe_allow_html=True)

# ============================================================
# MAIN LOGIN TITLE
# ============================================================

st.markdown("""
<div class="login-heading">
    <div class="secure">🔐 SECURE LOGIN</div>
    <div class="subtitle">Authorized Admin / Officer access only</div>
</div>
""", unsafe_allow_html=True)


# ============================================================
# ADMIN / OFFICER AUTHENTICATION
# ============================================================

if not st.session_state.user:
    st.header("🔐 Admin / Officer Login")
    st.caption("डिफ़ॉल्ट admin: username `admin`, password `admin123` — पहली बार लॉगिन के बाद बदलें।")
    u = st.text_input("Username", key="login_username")
    p = st.text_input("Password", type="password", key="login_password")

    col_login, col_forgot = st.columns(2)

    with col_login:
        login_clicked = st.button("Login", type="primary")

    with col_forgot:
        forgot_clicked = st.button("🔑 Forgot Password?")

    if login_clicked:
        user = auth.authenticate(u, p)

        if user:
            st.session_state.user = user
            st.rerun()

        else:
            # Check whether this username is temporarily locked
            login_username = (u or "").strip()

            if login_username:
                try:
                    failed_attempts, locked_until = auth._get_login_security(
                        login_username
                    )

                    if locked_until:
                        lock_time = datetime.fromisoformat(locked_until)
                        remaining = lock_time - datetime.now()

                        if remaining.total_seconds() > 0:
                            total_seconds = int(
                                remaining.total_seconds()
                            )

                            minutes, seconds = divmod(
                                total_seconds,
                                60
                            )

                            st.error(
                                "🔒 Account temporarily locked"
                            )

                            st.warning(
                                f"⏱️ Unlocks in **{minutes:02d}:{seconds:02d}**"
                            )

                            st.caption(
                                "बहुत अधिक गलत login attempts के कारण "
                                "account temporarily locked है।"
                            )

                        else:
                            st.error(
                                "गलत username या password।"
                            )

                    elif failed_attempts > 0:
                        remaining_attempts = max(
                            auth.MAX_LOGIN_ATTEMPTS - failed_attempts,
                            0
                        )

                        st.error(
                            "❌ गलत username या password।"
                        )

                        st.caption(
                            f"⚠️ {remaining_attempts} login attempts बाकी हैं।"
                        )

                    else:
                        st.error(
                            "गलत username या password।"
                        )

                except Exception:
                    # Never expose internal security errors to the user
                    st.error(
                        "गलत username या password।"
                    )
            else:
                st.error(
                    "Username और password डालें।"
                )

    if forgot_clicked:
        st.session_state.show_forgot_password = True

    if st.session_state.get("show_forgot_password", False):
        st.divider()
        st.subheader("🔑 Forgot Password")

        identifier = st.text_input(
            "Username या Registered Email",
            key="forgot_identifier"
        )

        if st.button("📩 Send OTP", key="send_reset_otp"):
            if not identifier.strip():
                st.warning("Username या email डालें।")
            else:
                try:
                    ok, message = auth.request_password_reset(identifier)

                    if ok:
                        st.session_state.reset_otp_sent = True
                        st.success(message)
                    else:
                        st.error(message)

                except Exception as e:
                    st.error(f"OTP भेजने में समस्या: {e}")

        if st.session_state.get("reset_otp_sent", False):
            otp = st.text_input(
                "🔢 6-Digit OTP",
                max_chars=6,
                key="reset_otp"
            )

            new_password = st.text_input(
                "🔐 New Password",
                type="password",
                key="reset_new_password"
            )

            confirm_password = st.text_input(
                "🔐 Confirm New Password",
                type="password",
                key="reset_confirm_password"
            )

            if st.button("✅ Reset Password", key="reset_password"):
                if new_password != confirm_password:
                    st.error("दोनों passwords समान होने चाहिए।")
                elif len(new_password) < 8:
                    st.error("Password कम से कम 8 characters का होना चाहिए।")
                else:
                    ok, message = auth.reset_password(
                        st.session_state.get("forgot_identifier", ""),
                        otp,
                        new_password
                    )

                    if ok:
                        st.success(message)
                        st.session_state.show_forgot_password = False
                        st.session_state.reset_otp_sent = False
                        st.info("अब नए password से Login करें।")
                    else:
                        st.error(message)
else:
    user = st.session_state.user

    # Get latest user data from database
    current_user = auth.get_user(user["username"])

    # Safely read registered email from sqlite3.Row
    registered_email = ""
    if current_user and "email" in current_user.keys():
        registered_email = current_user["email"] or ""

    # Get display name from registered email
    welcome_name = user["username"]

    if registered_email and "@" in registered_email:
        email_local = registered_email.split("@", 1)[0].lower()

        import re

        name_candidates = re.findall(r"[a-zA-Z]{3,}", email_local)

        ignored_words = {
            "poornima",
            "edu",
            "gmail",
            "admin",
            "officer",
            "tech",
            "btech",
            "aids",
            "student"
        }

        valid_names = [
            word for word in name_candidates
            if word.lower() not in ignored_words
        ]

        if valid_names:
            welcome_name = max(valid_names, key=len).capitalize()

    # Professional Welcome Profile
    topc1, topc2 = st.columns([5, 1])

    with topc1:
        welcome_html = f"""
        <div class="welcome-profile">
            <div class="welcome-profile-content">
                <div class="welcome-label">
                    WELCOME BACK
                </div>

                <div class="welcome-name">
                    👋 {welcome_name}
                </div>

                <div class="welcome-meta">
                    <span class="profile-role">
                        🛡️ {user["role"].capitalize()}
                    </span>

                    <span class="profile-email">
                        📧 {registered_email if registered_email else "Email not registered"}
                    </span>
                </div>
            </div>
        </div>
        """

        st.html(welcome_html)

    with topc2:
        if st.button("Logout"):
            st.session_state.user = None
            st.rerun()

    # =========================
    # ADMIN EMAIL SETTINGS
    # =========================
    if user["role"] == "admin":
        with st.expander("⚙️ Admin Email Settings"):
            current_user = auth.get_user(user["username"])
            current_email = (
                current_user["email"]
                if current_user and current_user["email"]
                else ""
            )

            st.caption("Forgot Password OTP इसी registered email पर भेजा जाएगा।")

            new_email = st.text_input(
                "📧 Registered Email",
                value=current_email,
                key="admin_email_setting"
            )

            if st.button("💾 Save Email", key="save_admin_email"):
                new_email = new_email.strip()

                try:
                    auth.set_email(user["username"], new_email)
                    st.success("✅ Admin email successfully updated.")
                except ValueError as e:
                    st.error(str(e))
                except Exception as e:
                    st.error(f"Email save करने में समस्या: {e}")


    # =========================================================
    # PROFESSIONAL DASHBOARD OVERVIEW
    # =========================================================

    dashboard_all = db.get_all_complaints()

    dashboard_total = len(dashboard_all)

    dashboard_pending = sum(
        1 for item in dashboard_all
        if item["status"] not in ("Resolved", "Closed")
    )

    dashboard_resolved = sum(
        1 for item in dashboard_all
        if item["status"] in ("Resolved", "Closed")
    )

    dashboard_sla = db.get_sla_counts()
    dashboard_escalations = db.get_escalation_counts()

    dashboard_breached = dashboard_sla.get("Breached", 0)
    dashboard_escalated = sum(
        dashboard_escalations.get(level, 0)
        for level in (1, 2, 3)
    )

    st.html(f"""
    <div class="dashboard-overview">
        <div class="dashboard-title">
            📊 Dashboard Overview
        </div>

        <div class="dashboard-subtitle">
            शिकायतों, SLA और escalation की वर्तमान स्थिति
        </div>

        <div class="kpi-grid">

            <div class="kpi-card">
                <div class="kpi-label">📋 TOTAL COMPLAINTS</div>
                <div class="kpi-value">{dashboard_total}</div>
                <div class="kpi-note">कुल शिकायतें</div>
            </div>

            <div class="kpi-card">
                <div class="kpi-label">🟡 PENDING</div>
                <div class="kpi-value">{dashboard_pending}</div>
                <div class="kpi-note">अभी कार्रवाई बाकी</div>
            </div>

            <div class="kpi-card">
                <div class="kpi-label">🔴 SLA BREACHED</div>
                <div class="kpi-value">{dashboard_breached}</div>
                <div class="kpi-note">SLA समय सीमा पार</div>
            </div>

            <div class="kpi-card">
                <div class="kpi-label">🚨 ESCALATED</div>
                <div class="kpi-value">{dashboard_escalated}</div>
                <div class="kpi-note">Escalated complaints</div>
            </div>

            <div class="kpi-card">
                <div class="kpi-label">🟢 RESOLVED</div>
                <div class="kpi-value">{dashboard_resolved}</div>
                <div class="kpi-note">Resolved / Closed</div>
            </div>

        </div>
    </div>
    """)

    tab_list, tab_analytics = st.tabs(["📋 शिकायतें", "📊 Analytics"])

    with tab_list:
        all_complaints = db.get_all_complaints()
        villages = ["सभी"] + sorted(set(c["village"] for c in all_complaints)) if all_complaints else ["सभी"]

        f1, f2, f3 = st.columns(3)
        status_f = f1.selectbox("स्थिति", ["सभी"] + db.STATUS_FLOW)
        village_f = f2.selectbox("गाँव", villages)
        urgency_f = f3.selectbox("प्राथमिकता", ["सभी", "High", "Medium", "Low"])

        complaints = db.get_all_complaints(status_f, village_f, urgency_f)

        # =================================================
        # PHASE 1 — SLA Dashboard Metrics
        # =================================================
        sla_counts = db.get_sla_counts()

        pending_count = sum(
            1 for c in all_complaints
            if c["status"] not in ("Resolved", "Closed")
        )

        escalation_counts = db.get_escalation_counts()

        m1, m2, m3, m4, m5 = st.columns(5)

        m1.metric(
            "🔴 SLA Breached",
            sla_counts.get("Breached", 0)
        )

        m2.metric(
            "🟠 Due Soon",
            sla_counts.get("Due Soon", 0)
        )

        m3.metric(
            "🚨 Escalated",
            sum(
                escalation_counts.get(level, 0)
                for level in (1, 2, 3)
            )
        )

        m4.metric(
            "🟡 Pending",
            pending_count
        )

        m5.metric(
            "🟢 Resolved",
            sum(
                1 for c in all_complaints
                if c["status"] in ("Resolved", "Closed")
            )
        )

        # =================================================
        # PHASE 1 — Escalation Level Breakdown
        # =================================================
        e1, e2, e3 = st.columns(3)

        e1.metric(
            "🚨 Level 1",
            escalation_counts.get(1, 0)
        )

        e2.metric(
            "🔥 Level 2",
            escalation_counts.get(2, 0)
        )

        e3.metric(
            "🛑 Level 3",
            escalation_counts.get(3, 0)
        )

        st.divider()

        for c in complaints:
            urg_class = {"High": "grv-high", "Medium": "grv-medium", "Low": "grv-low"}.get(c["urgency"], "")
            badge = STATUS_BADGE_CLASS.get(c["status"], "badge-Submitted")

            try:
                escalation_level = int(c.get("escalation_level") or 0)
            except (TypeError, ValueError):
                escalation_level = 0

            escalation_display = {
                0: "⚪ Level 0 — Normal",
                1: "🚨 Level 1 — Escalated",
                2: "🔥 Level 2 — High Escalation",
                3: "🛑 Level 3 — Critical Escalation",
            }.get(
                min(max(escalation_level, 0), 3),
                "⚪ Level 0 — Normal"
            )

            st.markdown(f"""
            <div class="grv-card {urg_class}">
                <span class="complaint-id">{c['id']}</span> &nbsp;
                <b>{c['village']}</b> · {c['category']} · {URGENCY_ICON.get(c['urgency'],'')} {c['urgency']}
                &nbsp; <span class="badge {badge}">{c['status']}</span>
                <br>
                <small>{c['created_at']}</small>
                &nbsp; · &nbsp; <b>{escalation_display}</b>
            </div>
            """, unsafe_allow_html=True)

            with st.expander("विवरण / Update status"):
                st.write(f"**मूल शिकायत:** {c['original_text']}")
                st.write(f"**सारांश:** {c['summary']}")

                # =================================================
                # PHASE 1 — Department + Priority + Officer + SLA
                # =================================================
                d1, d2, d3, d4 = st.columns(4)

                with d1:
                    st.metric(
                        "🏢 विभाग",
                        c.get("department") or "General"
                    )

                with d2:
                    priority = c.get("priority") or c.get("urgency") or "Medium"
                    priority_icon = {
                        "High": "🔴",
                        "Medium": "🟠",
                        "Low": "🟢"
                    }.get(priority, "⚪")

                    st.metric(
                        "🎯 Priority",
                        f"{priority_icon} {priority}"
                    )

                with d3:
                    assigned_officer = (
                        c.get("assigned_officer")
                        or c.get("assigned_to")
                    )

                    st.metric(
                        "👤 Assigned Officer",
                        assigned_officer or "Not Assigned"
                    )

                with d4:
                    sla_hours = c.get("sla_hours")
                    st.metric(
                        "⏱️ SLA",
                        f"{sla_hours} घंटे" if sla_hours else "N/A"
                    )

                if c.get("sla_deadline"):
                    st.info(
                        f"📅 **SLA Deadline:** {c['sla_deadline']}"
                    )

                    # =================================================
                    # PHASE 1 — Live SLA Status
                    # =================================================
                    try:
                        sla_state = db.get_sla_state(c)

                        sla_display = {
                            "On Track": "🟢 On Track",
                            "Due Soon": "🟠 Due Soon",
                            "Breached": "🔴 Breached",
                            "Completed": "✅ Completed",
                            "No SLA": "⚪ No SLA",
                            "Invalid SLA": "⚠️ Invalid SLA",
                        }.get(
                            sla_state,
                            f"⚪ {sla_state}"
                        )

                        st.markdown(
                            f"**SLA Status:** {sla_display}"
                        )

                    except Exception as e:
                        st.warning(
                            f"SLA status load नहीं हो सका: {e}"
                        )

                if c["latitude"] and c["longitude"]:
                    st.map({
                        "lat": [c["latitude"]],
                        "lon": [c["longitude"]]
                    })

                if c["photo_path"] and os.path.exists(c["photo_path"]):
                    st.image(c["photo_path"], width=250)

                if c["video_path"] and os.path.exists(c["video_path"]):
                    st.video(c["video_path"])

                # =================================================
                # PHASE 1 — Complaint Timeline
                # =================================================
                st.markdown("### 🕒 Complaint Timeline")

                try:
                    timeline = db.get_complaint_updates(c["id"])

                    if timeline:
                        for event in timeline:
                            action = event.get("action") or "Update"
                            remarks = event.get("remarks") or ""
                            updated_by = event.get("updated_by") or "system"
                            event_time = event.get("created_at") or ""

                            st.markdown(
                                f"""
                                **🔹 {action}**  
                                `{event_time}` · 👤 {updated_by}  
                                {remarks}
                                """
                            )
                    else:
                        st.caption("अभी कोई timeline update नहीं है।")

                except Exception as e:
                    st.warning(f"Timeline load नहीं हो सकी: {e}")

                st.divider()

                # =================================================
                # PHASE 1 — OFFICER UPDATE
                # =================================================
                new_status = st.selectbox(
                    "स्थिति बदलें",
                    db.STATUS_FLOW,
                    index=db.STATUS_FLOW.index(c["status"]),
                    key=f"status_{c['id']}"
                )

                priority = st.selectbox(
                    "🎯 Priority",
                    ["High", "Medium", "Low"],
                    index=["High", "Medium", "Low"].index(
                        c.get("priority") or c.get("urgency") or "Medium"
                    ),
                    key=f"priority_{c['id']}"
                )

                assigned_officer = st.text_input(
                    "👤 Assigned Officer",
                    value=c.get("assigned_officer")
                    or c.get("assigned_to")
                    or user["username"],
                    key=f"officer_{c['id']}"
                )

                notes = st.text_area(
                    "टिप्पणी (Citizen को भेजी जाएगी)",
                    value=c.get("resolution_notes") or "",
                    key=f"notes_{c['id']}"
                )

                resolution_remarks = st.text_area(
                    "📝 Resolution Remarks",
                    value=c.get("resolution_remarks") or "",
                    key=f"resolution_remarks_{c['id']}"
                )

                resolution_photo = st.file_uploader(
                    "📸 Resolution Evidence Photo",
                    type=["jpg", "jpeg", "png"],
                    key=f"resolution_photo_{c['id']}"
                )

                escalation_level = st.selectbox(
                    "🚨 Escalation Level",
                    [0, 1, 2, 3],
                    index=min(
                        max(int(c.get("escalation_level") or 0), 0),
                        3
                    ),
                    format_func=lambda x: (
                        "Level 0 — Normal"
                        if x == 0 else
                        f"Level {x} — Escalated"
                    ),
                    key=f"escalation_{c['id']}"
                )

                if st.button(
                    "💾 अपडेट करें व Citizen को Notify करें",
                    key=f"upd_{c['id']}"
                ):
                    saved_photo = c.get("resolution_photo")

                    if resolution_photo:
                        os.makedirs("uploads", exist_ok=True)

                        photo_name = (
                            f"resolution_{c['id']}_"
                            f"{resolution_photo.name}"
                        )

                        photo_path = os.path.join(
                            "uploads",
                            photo_name
                        )

                        with open(photo_path, "wb") as f:
                            f.write(resolution_photo.getbuffer())

                        saved_photo = photo_path

                    db.update_status(
                        c["id"],
                        new_status,
                        notes=notes,
                        assigned_officer=assigned_officer,
                        resolution_remarks=resolution_remarks or None,
                        resolution_photo=saved_photo,
                        escalation_level=escalation_level
                    )

                    with db.get_conn() as conn:
                        conn.execute(
                            """
                            UPDATE complaints
                            SET priority = ?,
                                updated_at = ?
                            WHERE id = ?
                            """,
                            (
                                priority,
                                datetime.now().isoformat(
                                    timespec="seconds"
                                ),
                                c["id"],
                            )
                        )

                    updated = db.get_complaint(c["id"])

                    ok, msg = notify.notify_citizen_status_update(
                        c["citizen_phone"],
                        updated
                    )

                    st.success("स्थिति और Phase 1 जानकारी अपडेट हो गई।")
                    st.info(msg)
                    st.rerun()

    with tab_analytics:
        # =========================================================
        # PROFESSIONAL ANALYTICS DASHBOARD
        # =========================================================

        data = db.get_analytics()

        categories = data.get("by_category", [])
        urgencies = data.get("by_urgency", [])
        statuses = data.get("by_status", [])
        villages = data.get("by_village", [])
        daily = data.get("daily", [])

        if not categories:
            st.info("अभी विश्लेषण के लिए पर्याप्त डेटा नहीं है।")
        else:
            # -----------------------------------------------------
            # Analytics summary
            # -----------------------------------------------------

            analytics_total = sum(
                int(item.get("n", 0) or 0)
                for item in categories
            )

            analytics_high = next(
                (
                    int(item.get("n", 0) or 0)
                    for item in urgencies
                    if item.get("urgency") == "High"
                ),
                0
            )

            analytics_medium = next(
                (
                    int(item.get("n", 0) or 0)
                    for item in urgencies
                    if item.get("urgency") == "Medium"
                ),
                0
            )

            analytics_low = next(
                (
                    int(item.get("n", 0) or 0)
                    for item in urgencies
                    if item.get("urgency") == "Low"
                ),
                0
            )

            analytics_resolved = sum(
                int(item.get("n", 0) or 0)
                for item in statuses
                if item.get("status") in ("Resolved", "Closed")
            )

            analytics_pending = max(
                analytics_total - analytics_resolved,
                0
            )

            st.markdown(
                """
                <div class="analytics-header">
                    <div class="analytics-title">
                        📊 Analytics & Performance
                    </div>
                    <div class="analytics-subtitle">
                        शिकायतों, प्राथमिकता और स्थिति का विस्तृत विश्लेषण
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            # -----------------------------------------------------
            # KPI cards
            # -----------------------------------------------------

            k1, k2, k3, k4, k5 = st.columns(5)

            k1.metric(
                "📋 Total",
                analytics_total
            )

            k2.metric(
                "🟡 Pending",
                analytics_pending
            )

            k3.metric(
                "🔴 High Priority",
                analytics_high
            )

            k4.metric(
                "🟠 Medium Priority",
                analytics_medium
            )

            k5.metric(
                "🟢 Resolved",
                analytics_resolved
            )

            st.divider()

            # -----------------------------------------------------
            # Category + Priority
            # -----------------------------------------------------

            a1, a2 = st.columns(2)

            with a1:
                st.markdown("### 📂 शिकायतें — श्रेणी अनुसार")

                category_chart = px.pie(
                    categories,
                    names="category",
                    values="n",
                    hole=0.45
                )

                category_chart.update_layout(
                    margin=dict(t=30, b=20, l=20, r=20),
                    legend_title_text="श्रेणी",
                    showlegend=True
                )

                st.plotly_chart(
                    category_chart,
                    use_container_width=True
                )

            with a2:
                st.markdown("### 🎯 प्राथमिकता — Priority")

                priority_chart = px.bar(
                    urgencies,
                    x="urgency",
                    y="n",
                    text="n"
                )

                priority_chart.update_layout(
                    xaxis_title="प्राथमिकता",
                    yaxis_title="शिकायतों की संख्या",
                    margin=dict(t=30, b=40, l=40, r=20),
                    showlegend=False
                )

                priority_chart.update_traces(
                    textposition="outside"
                )

                st.plotly_chart(
                    priority_chart,
                    use_container_width=True
                )

            # -----------------------------------------------------
            # Status + Village
            # -----------------------------------------------------

            a3, a4 = st.columns(2)

            with a3:
                st.markdown("### 📋 शिकायतों की स्थिति")

                status_chart = px.bar(
                    statuses,
                    x="status",
                    y="n",
                    text="n"
                )

                status_chart.update_layout(
                    xaxis_title="स्थिति",
                    yaxis_title="शिकायतों की संख्या",
                    margin=dict(t=30, b=40, l=40, r=20),
                    showlegend=False
                )

                status_chart.update_traces(
                    textposition="outside"
                )

                st.plotly_chart(
                    status_chart,
                    use_container_width=True
                )

            with a4:
                st.markdown("### 🏘️ शीर्ष 10 गाँव")

                village_chart = px.bar(
                    villages,
                    x="n",
                    y="village",
                    orientation="h",
                    text="n"
                )

                village_chart.update_layout(
                    xaxis_title="शिकायतों की संख्या",
                    yaxis_title="गाँव",
                    margin=dict(t=30, b=40, l=80, r=30),
                    showlegend=False
                )

                village_chart.update_traces(
                    textposition="outside"
                )

                st.plotly_chart(
                    village_chart,
                    use_container_width=True
                )

            # -----------------------------------------------------
            # Daily complaint trend
            # -----------------------------------------------------

            if daily:
                st.markdown("### 📈 दैनिक शिकायत ट्रेंड")

                trend_chart = px.line(
                    daily,
                    x="day",
                    y="n",
                    markers=True
                )

                trend_chart.update_layout(
                    xaxis_title="दिन",
                    yaxis_title="शिकायतों की संख्या",
                    margin=dict(t=30, b=40, l=40, r=20),
                    showlegend=False
                )

                st.plotly_chart(
                    trend_chart,
                    use_container_width=True
                )

            # -----------------------------------------------------
            # Priority summary
            # -----------------------------------------------------

            st.markdown("### 🎯 Priority Summary")

            p1, p2, p3 = st.columns(3)

            p1.metric(
                "🔴 High",
                analytics_high
            )

            p2.metric(
                "🟠 Medium",
                analytics_medium
            )

            p3.metric(
                "🟢 Low",
                analytics_low
            )

