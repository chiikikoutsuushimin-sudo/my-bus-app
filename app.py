import streamlit as st
import datetime
import base64
import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from streamlit_calendar import calendar
from google.oauth2.service_account import Credentials
import gspread

# --- 背景に動画を設定する関数 ---
def set_bg_video(video_file):
    with open(video_file, "rb") as f:
        video_bytes = f.read()
    b64_video = base64.b64encode(video_bytes).decode()
    
    video_html = f'''
    <style>
    header {{ visibility: hidden !important; opacity: 0 !important; pointer-events: none !important; }}
    footer {{ visibility: hidden !important; opacity: 0 !important; pointer-events: none !important; }}
    div[data-testid="stDecoration"] {{ display: none !important; }}
    div[data-testid="stStatusWidget"] {{ display: none !important; }}
    div[data-testid="stToolbar"] {{ display: none !important; }}
    [class*="viewerBadge"] {{ display: none !important; }}
    [class*="MainMenu"] {{ display: none !important; }}
    .stApp {{ background: transparent; }}
    #bg-video {{
        position: fixed; right: 0; bottom: 0; min-width: 100%; min-height: 100%;
        top: 50%; left: 50%; transform: translate(-50%, -50%); z-index: -1; object-fit: cover;
    }}
    .main .block-container {{
        background-color: rgba(0, 0, 0, 0.3) !important; padding: 2.5rem; border-radius: 15px;
        border: 1px solid rgba(255, 255, 255, 0.15) !important; box-shadow: 0 4px 30px rgba(0, 0, 0, 0.3);
    }}
    *, .stApp, .stMarkdown, .stSubheader, .stTitle, input, select, textarea, button, 
    div[data-testid="stExpander"] *, .fc *, div[role="listbox"] *, .stAlert * {{
        color: #ffffff !important;
        text-shadow: 1px 1px 0px #000000, -1px -1px 0px #000000, 1px -1px 0px #000000, -1px 1px 0px #000000,
                    0px 1px 0px #000000, 0px -1px 0px #000000, 1px 0px 0px #000000, -1px 0px 0px #000000 !important;
    }}
    input, select, textarea, button, div[data-testid="stExpander"], .fc, .fc-theme-standard td, .fc-theme-standard th {{
        background-color: rgba(0, 0, 0, 0.25) !important; border: 1px solid rgba(255, 255, 255, 0.3) !important;
    }}
    input:focus, select:focus, textarea:focus {{ border: 1px solid #ffffff !important; outline: none !important; }}
    button:hover {{ background-color: rgba(255, 255, 255, 0.1) !important; }}
    div[data-baseweb="popover"], div[role="listbox"], ul[role="listbox"] {{ background-color: rgba(15, 15, 15, 0.95) !important; }}
    </style>
    <video autoplay loop muted playsinline id="bg-video">
        <source src="data:video/mp4;base64,{b64_video}" type="video/mp4">
    </video>
    '''
    st.markdown(video_html, unsafe_allow_html=True)

try:
    set_bg_video("background.mp4")
except FileNotFoundError:
    st.warning("⚠️ 背景動画ファイル（background.mp4）が見つかりません。")

# --- 予約データ読み込み ---
def load_bookings_from_sheets():
    try:
        creds_dict = json.loads(st.secrets["gcp_json"])
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        sheet = client.open("施設予約データ").sheet1
        records = sheet.get_all_records()
        bookings = []
        for r in records:
            if not r["利用日"]: continue
            d_parts = list(map(int, str(r["利用日"]).split("-")))
            b_date = datetime.date(d_parts[0], d_parts[1], d_parts[2])
            st_parts = list(map(int, str(r["開始時間"]).split(":")))
            et_parts = list(map(int, str(r["終了時間"]).split(":")))
            bookings.append({
                "room": r["部屋名"], "date": b_date, "start_time": datetime.time(st_parts[0], st_parts[1]),
                "end_time": datetime.time(et_parts[0], et_parts[1])
            })
        return bookings
    except: return []

# --- ページ遷移用 ---
def change_page(page_name): st.session_state.page = page_name

if "page" not in st.session_state: st.session_state.page = "input_datetime"
if "bookings" not in st.session_state: st.session_state.bookings = load_bookings_from_sheets()

st.title("庄原市交通交流施設オンライン予約")

# ==========================================
# ページ振り分け
# ==========================================
if st.session_state.page == "input_datetime":
    # (省略：入力画面のロジックはそのまま維持)
    st.button("📅 全体の予約状況を別画面で確認する", use_container_width=True, on_click=change_page, args=("view_calendar",))
    # ... (以下の入力処理は以前のコードと同様) ...

elif st.session_state.page == "view_calendar":
    st.subheader("🗓️ 全体の予約状況")
    if st.button("⬅️ 戻る", use_container_width=True, on_click=change_page, args=("input_datetime",)): st.rerun()
    
    tab1, tab2 = st.tabs(["地域交流室１", "地域交流室２"])
    
    # 共通カレンダー設定
    cal_options = {"locale": "ja", "headerToolbar": {"left": "prev,next today", "center": "title", "right": "dayGridMonth"}}
    
    with tab1:
        events1 = [{"title": "🔴 予約済" if any(b['room'] == "地域交流室１（会議室）" and b['date'].strftime('%Y-%m-%d') == d.strftime('%Y-%m-%d') for b in st.session_state.bookings) else "🟢 空き", "start": d.strftime('%Y-%m-%d'), "allDay": True} for d in [datetime.date.today() + datetime.timedelta(days=i) for i in range(30)]]
        calendar(events=events1, options=cal_options, key="C_ROOM_1")
        
    with tab2:
        events2 = [{"title": "🔴 予約済" if any(b['room'] == "地域交流室２（多目的スペース）" and b['date'].strftime('%Y-%m-%d') == d.strftime('%Y-%m-%d') for b in st.session_state.bookings) else "🟢 空き", "start": d.strftime('%Y-%m-%d'), "allDay": True} for d in [datetime.date.today() + datetime.timedelta(days=i) for i in range(30)]]
        calendar(events=events2, options=cal_options, key="C_ROOM_2")

# (以降のinput_personal_infoやcompletedはそのまま維持)