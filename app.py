import streamlit as st
import datetime
import base64
from streamlit_calendar import calendar

# --- 背景に動画を設定する関数 ---
def set_bg_video(video_file):
    with open(video_file, "rb") as f:
        video_bytes = f.read()
    b64_video = base64.b64encode(video_bytes).decode()
    
    video_html = f'''
    <style>
    .stApp {{
        background: transparent;
    }}
    #bg-video {{
        position: fixed;
        right: 0;
        bottom: 0;
        min-width: 100%;
        min-height: 100%;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        z-index: -1;
        object-fit: cover;
    }}
    .main .block-container {{
        background-color: rgba(255, 255, 255, 1.0);
        padding: 2.5rem;
        border-radius: 15px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }}
    .stApp, .stApp *, .stMarkdown, .stSubheader, .stTitle, .stSelectbox label, .stRadio label, .stCheckbox label, .stTextArea label, .stNumberInput label, .stTextInput label {{
        color: white !important;
        text-shadow: 1px 1px 1px black, -1px -1px 1px black, 1px -1px 1px black, -1px 1px 1px black, 2px 2px 3px rgba(0,0,0,0.8) !important;
    }}
    input, select, textarea, button {{
        color: black !important;
        text-shadow: none !important;
    }}
    .fc * {{
        text-shadow: none !important;
        color: black !important;
    }}
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


# --- 状態の管理（セッション状態） ---
if "page" not in st.session_state:
    st.session_state.page = "input_datetime"
if "bookings" not in st.session_state:
    st.session_state.bookings = []
if "temp_booking" not in st.session_state:
    st.session_state.temp_booking = {}

# 【変更】タイトルを「庄原市交通交流施設」に変更
st.title("庄原市交通交流施設")


# ==========================================
# 画面1：申請日時と使用場所選択
# ==========================================
if st.session_state.page == "input_datetime":
    st.write("利用可能時間：9:00〜21:00（※12月29日〜1月3日は年末年始のため終日貸出不可）")
    # 【変更】ステップ1の名称を変更
    st.subheader("申請日時と使用場所選択")

    room = st.selectbox("部屋を選択してください", [
        "地域交流室１（会議室）", 
        "地域交流室２（多目的スペース）"
    ])

    selected_date = st.date_input("日付を選択してください")

    time_options = [datetime.time(h, 0) for h in range(9, 22)]
    col1, col2 = st.columns(2)
    with col1:
        start_time = st.selectbox("開始時間", time_options[:-1], format_func=lambda t: t.strftime("%H:%M"))
    with col2:
        end_time = st.selectbox("終了時間", time_options[1:], index=len(time_options[1:])-1, format_func=lambda t: t.strftime("%H:%M"))

    usage_type = st.radio("利用区分", ["一般使用", "営利、宣伝等での使用"])
    use_ac = st.checkbox("冷暖房を使用する")

    if st.button("次へ進む（連絡先等の入力へ）"):
        has_error = False

        is_closed_date = (selected_date.month == 12 and selected_date.day >= 29) or \
                         (selected_date.month == 1 and selected_date.day <= 3)

        if is_closed_date:
            st.error("❌ エラー：12月29日から翌年1月3日は年末年始の休館期間のため、予約できません。")
            has_error = True

        if start_time >= end_time:
            st.error("❌ エラー：終了時間は開始時間より後に設定してください。")
            has_error = True

        for b in st.session_state.bookings:
            if b['date'] == selected_date and b['room'] == room:
                if not (end_time <= b['start_time'] or start_time >= b['end_time']):
                    st.error("❌ エラー：選択された日時はすでに予約が入っています。")
                    has_error = True
                    break

        if not has_error:
            hours = end_time.hour - start_time.hour
            total_fee = 0
            if usage_type == "営利、宣伝等での使用":
                if room == "地域交流室１（会議室）":
                    total_fee += 1040 * hours
                else:
                    total_fee += 520 * hours
                if use_ac:
                    total_fee += 310 * hours

            st.session_state.temp_booking = {
                "room": room,
                "date": selected_date,
                "start_time": start_time,
                "end_time": end_time,
                "usage_type": usage_type,
                "use_ac": use_ac,
                "fee": total_fee,
                "hours": hours
            }
            st.session_state.page = "input_personal_info"
            st.rerun()

    st.write("---")
    # 【変更】カレンダーのタイトルを変更
    st.subheader("🗓️ 現在の予約カレンダー")
    
    # --- 【新機能】毎日・各部屋の「空きあり/空き無し」を自動計算してカレンダーに敷き詰める ---
    calendar_events = []
    
    # 選択された日付の月の1日から、約60日分（翌月末まで）の空き状況を自動作成
    start_grid_date = selected_date.replace(day=1)
    rooms_list = ["地域交流室１（会議室）", "地域交流室２（多目的スペース）"]
    
    for day_offset in range(60):
        loop_date = start_grid_date + datetime.timedelta(days=day_offset)
        
        # 年末年始（12/29〜1/3）の休館判定
        is_closed = (loop_date.month == 12 and loop_date.day >= 29) or \
                    (loop_date.month == 1 and loop_date.day <= 3)
                    
        for r in rooms_list:
            display_room_name = "交流室1" if r == "地域交流室１（会議室）" else "交流室2"
            
            if is_closed:
                # 休館日の表示
                calendar_events.append({
                    "title": f"⚪ {display_room_name}:休館",
                    "start": loop_date.strftime('%Y-%m-%d'),
                    "allDay": True,
                    "color": "#e0e0e0"  # 薄いグレー
                })
            else:
                # 予約が入っているかチェック
                has_booking = False
                for b in st.session_state.bookings:
                    if b['date'] == loop_date and b['room'] == r:
                        has_booking = True
                        break
                
                if has_booking:
                    # 【変更】予約がある日は「空き無し（赤）」
                    calendar_events.append({
                        "title": f"🔴 {display_room_name}:空き無し",
                        "start": loop_date.strftime('%Y-%m-%d'),
                        "allDay": True,
                        "color": "#ff4b4b"  # 赤色
                    })
                else:
                    # 【変更】予約がない日は「空きあり（緑）」
                    calendar_events.append({
                        "title": f"🟢 {display_room_name}:空きあり",
                        "start": loop_date.strftime('%Y-%m-%d'),
                        "allDay": True,
                        "color": "#2cd15a"  # 緑色
                    })
    
    calendar_options = {
        "editable": False,
        "selectable": False,
        "locale": "ja",
        "headerToolbar": {
            "left": "prev,next today",
            "center": "title",
            "right": "dayGridMonth"
        },
        "initialView": "dayGridMonth",
    }
    
    calendar(events=calendar_events, options=calendar_options)


# ==========================================
# 画面2：使用者情報の入力
# ==========================================
elif st.session_state.page == "input_personal_info":
    # 【変更】ステップ2の名称を変更
    st.subheader("使用者情報の入力")
    
    temp = st.session_state.temp_booking
    st.info(f"📋 選択中の日時: {temp['date'].strftime('%Y/%m/%d')} {temp['start_time'].strftime('%H:%M')}〜{temp['end_time'].strftime('%H:%M')} ({temp['room']})")

    user_name = st.text_input("お名前 / 団体名（必須）")
    user_address = st.text_input("ご住所（必須）")
    user_phone = st.text_input("ご連絡先電話番号（必須）")
    user_purpose = st.text_area("使用目的（必須）")
    user_count = st.number_input("利用人数（人）", min_value=1, max_value=500, value=1)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("⬅️ 日時選択に戻る"):
            st.session_state.page = "input_datetime"
            st.rerun()
            
    with col2:
        if st.button("予約を確定する ➡️"):
            if not user_name or not user_address or not user_phone or not user_purpose:
                st.error("❌ エラー：必須項目（お名前・ご住所・ご連絡先・使用目的）をすべて入力してください。")
            else:
                final_booking = st.session_state.temp_booking.copy()
                final_booking.update({
                    "name": user_name,
                    "address": user_address,
                    "phone": user_phone,
                    "purpose": user_purpose,
                    "num_people": user_count
                })
                st.session_state.bookings.append(final_booking)
                st.session_state.page = "completed"
                st.rerun()


# ==========================================
# 画面3：予約完了画面
# ==========================================
elif st.session_state.page == "completed":
    st.success("🎉 施設予約が確定しました！お申し込みありがとうございます。")
    
    last_b = st.session_state.bookings[-1]
    st.write("### 🔑 受付内容の控え")
    st.write(f"- **部屋名**: {last_b['room']}")
    st.write(f"- **利用日時**: {last_b['date'].strftime('%Y/%m/%d')} {last_b['start_time'].strftime('%H:%M')}〜{last_b['end_time'].strftime('%H:%M')}")
    st.write(f"- **申請者氏名**: {last_b['name']}")
    st.write(f"- **利用人数**: {last_b['num_people']} 名")
    st.write(f"- **概算料金**: {last_b['fee']} 円")
    
    st.write("---")
    if st.button("トップページ（新規予約）へ戻る"):
        st.session_state.page = "input_datetime"
        st.rerun()