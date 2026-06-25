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
    /* 右上のForkボタンやメニュー、足元の文字、バッジ等を完全に非表示にする */
    header {{ visibility: hidden; }}
    footer {{ visibility: hidden; }}
    div[data-testid="stDecoration"] {{ display: none; }}
    div[data-testid="stStatusWidget"] {{ display: none; }}
    [class^="viewerBadge"] {{ display: none !important; }}
    
    /* 背景動画とコンテンツのデザイン調整（重複をカットしました） */
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


# --- Googleスプレッドシートから予約データを読み込む関数 ---
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
            start_time = datetime.time(st_parts[0], st_parts[1])
            
            et_parts = list(map(int, str(r["終了時間"]).split(":")))
            end_time = datetime.time(et_parts[0], et_parts[1])
            
            hours = et_parts[0] - st_parts[0]
            
            bookings.append({
                "room": r["部屋名"], "date": b_date, "start_time": start_time, "end_time": end_time,
                "fee": int(r["料金"]), "name": r["お名前"], "email": r["メールアドレス"],
                "address": r["ご住所"], "phone": str(r["電話番号"]), "purpose": r["使用目的"],
                "num_people": int(r["利用人数"]), "hours": hours
            })
        return bookings
    except Exception as e:
        st.error(f"⚠️ スプレッドシート同期エラー: {e}")
        return []


# --- Googleスプレッドシートに新しい予約を書き込む関数 ---
def add_booking_to_sheets(b):
    try:
        creds_dict = json.loads(st.secrets["gcp_json"])
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        
        sheet = client.open("施設予約データ").sheet1
        
        row = [
            b["room"], b["date"].strftime("%Y-%m-%d"), b["start_time"].strftime("%H:%M"), b["end_time"].strftime("%H:%M"),
            b["fee"], b["name"], b["email"], b["address"], b["phone"], b["purpose"], b["num_people"],
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ]
        sheet.append_row(row)
        return True
    except Exception as e:
        st.error(f"⚠️ スプレッドシート保存エラー: {e}")
        return False


# --- Gmail自動送信関数 ---
def send_email(to_email, subject, body):
    try:
        gmail_user = st.secrets["gmail_user"]
        gmail_password = st.secrets["gmail_password"]
        msg = MIMEMultipart()
        msg['From'] = gmail_user
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        server = smtplib.SMTP_SSL('smtp.gmail.com', 464 + 1)
        server.login(gmail_user, gmail_password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.error(f"⚠️ メール送信エラー: {e}")
        return False


# --- 状態の管理（セッション状態） ---
if "page" not in st.session_state:
    st.session_state.page = "input_datetime"
if "temp_booking" not in st.session_state:
    st.session_state.temp_booking = {}

# 起動時・または手動更新ボタン押下時にスプレッドシートからデータを読み込む
if "bookings" not in st.session_state or st.sidebar.button("🔄 データを最新に更新"):
    st.session_state.bookings = load_bookings_from_sheets()

st.title("庄原市交通交流施設オンライン予約")


# ==========================================
# 画面1：申請日時と使用場所選択
# ==========================================
if st.session_state.page == "input_datetime":
    st.write("利用可能時間：9:00〜21:00（※12月29日〜1月3日は年末年始のため終日貸出不可）")
    st.subheader("申請日時と使用場所選択")

    room = st.selectbox("部屋を選択してください", ["地域交流室１（会議室）", "地域交流室２（多目的スペース）"])

    today = datetime.date.today()
    if today.month <= 3: fiscal_end_year = today.year
    else: fiscal_end_year = today.year + 1
    max_date = datetime.date(fiscal_end_year, 3, 31)

    selected_date = st.date_input("日付を選択してください", min_value=today, max_value=max_date, value=today)
    st.write(f"### 🕒 {selected_date.strftime('%Y年%m月%d日')} の空き状況および時間帯選択")
    
    is_closed_date = (selected_date.month == 12 and selected_date.day >= 29) or (selected_date.month == 1 and selected_date.day <= 3)
    selected_slots = []
    
    for h in range(9, 21):
        slot_text = f"{h}:00 〜 {h+1}:00"
        if is_closed_date:
            status = "⚪ 休館日"
            is_disabled = True
        else:
            booked = False
            for b in st.session_state.bookings:
                if b['date'] == selected_date and b['room'] == room:
                    if not (datetime.time(h+1, 0) <= b['start_time'] or datetime.time(h, 0) >= b['end_time']):
                        booked = True
                        break
            if booked:
                status = "🔴 予約不可（先約あり）"
                is_disabled = True
            else:
                status = "🟢 予約可能"
                is_disabled = False
        
        if is_disabled: st.checkbox(f"{slot_text}  【 {status} 】", value=False, disabled=True, key=f"slot_{h}")
        else:
            if st.checkbox(f"{slot_text}  【 {status} 】", value=False, key=f"slot_{h}"): selected_slots.append(h)

    st.write("---")
    usage_type = st.radio("利用区分", ["一般使用", "営利、宣伝等での使用"])
    use_ac = st.checkbox("冷暖房を使用する")

    hours, total_fee, start_time, end_time, has_slot_error = 0, 0, None, None, False

    if selected_slots:
        selected_slots.sort()
        is_continuous = True
        for i in range(len(selected_slots) - 1):
            if selected_slots[i+1] - selected_slots[i] != 1:
                is_continuous = False
                break
        if not is_continuous:
            st.error("❌ エラー：ご利用時間は、途切れることなく連続した時間帯で選択してください。")
            has_slot_error = True
        else:
            start_time = datetime.time(selected_slots[0], 0)
            end_time = datetime.time(selected_slots[-1] + 1, 0)
            hours = len(selected_slots)
            if usage_type == "営利、宣伝等での使用":
                total_fee += (1040 if room == "地域交流室１（会議室）" else 520) * hours
                if use_ac: total_fee += 310 * hours
            st.info(f"📋 選択中の時間帯: {start_time.strftime('%H:%M')} 〜 {end_time.strftime('%H:%M')}")
    else:
        st.warning("⚠️ 上記の一覧より、ご利用になる時間帯にチェックを入れてください。")

    st.markdown(f"### 💰 現在の概算料金: **{total_fee:,} 円** *(利用時間: {hours}時間)*")

    if st.button("次へ進む（連絡先等の入力へ）"):
        if not selected_slots: st.error("❌ エラー：時間帯が選択されていません。")
        elif has_slot_error: st.error("❌ エラー：時間帯の選択内容に不備があります。")
        elif is_closed_date: st.error("❌ エラー：年末年始の休館期間のため、予約手続きを進めることはできません。")
        else:
            st.session_state.temp_booking = {
                "room": room, "date": selected_date, "start_time": start_time, "end_time": end_time,
                "usage_type": usage_type, "use_ac": use_ac, "fee": total_fee, "hours": hours
            }
            st.session_state.page = "input_personal_info"
            st.rerun()

    st.write("---")
    with st.expander("🗓️ 全体の予約状況（月間カレンダー）を見る"):
        start_grid_date = selected_date.replace(day=1)
        calendar_options = {
            "editable": False, "selectable": False, "locale": "ja",
            "headerToolbar": {"left": "prev,next today", "center": "title", "right": "dayGridMonth"}, "initialView": "dayGridMonth",
        }
        tab1, tab2 = st.tabs(["地域交流室１（会議室）の状況", "地域交流室２（多目的スペース）の状況"])
        
        with tab1:
            calendar_events_room1 = []
            loop_date = start_grid_date
            while loop_date <= max_date:
                is_closed = (loop_date.month == 12 and loop_date.day >= 29) or (loop_date.month == 1 and loop_date.day <= 3)
                if is_closed: calendar_events_room1.append({"title": "⚪ 休館", "start": loop_date.strftime('%Y-%m-%d'), "allDay": True, "color": "#e0e0e0"})
                else:
                    has_booking = any(b['date'] == loop_date and b['room'] == "地域交流室１（会議室）" for b in st.session_state.bookings)
                    calendar_events_room1.append({"title": "🔴 予約不可" if has_booking else "🟢 予約可能", "start": loop_date.strftime('%Y-%m-%d'), "allDay": True, "color": "#ff4b4b" if has_booking else "#2cd15a"})
                loop_date += datetime.timedelta(days=1)
            calendar(events=calendar_events_room1, options=calendar_options, key="calendar_room1")

        with tab2:
            calendar_events_room2 = []
            loop_date = start_grid_date
            while loop_date <= max_date:
                is_closed = (loop_date.month == 12 and loop_date.day >= 29) or (loop_date.month == 1 and loop_date.day <= 3)
                if is_closed: calendar_events_room2.append({"title": "⚪ 休館", "start": loop_date.strftime('%Y-%m-%d'), "allDay": True, "color": "#e0e0e0"})
                else:
                    has_booking = any(b['date'] == loop_date and b['room'] == "地域交流室２（多目的スペース）" for b in st.session_state.bookings)
                    calendar_events_