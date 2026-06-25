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
    
    /* --- 新しい時間割テーブル風スタイル（文字の視認性を最優先） --- */
    .timetable-header-marker + div {{
        background-color: #f2f2f2 !important;
        border: 1px solid #ddd;
        padding: 10px 5px;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        text-align: center;
    }}
    .timetable-header-marker + div * {{
        color: black !important;
        text-shadow: none !important;
        font-weight: bold !important;
    }}
    
    /* 予約可能行（薄緑・不透明） */
    .timetable-row-marker-available + div {{
        background-color: #ccffcc !important;
        border-left: 1px solid #ddd;
        border-right: 1px solid #ddd;
        border-bottom: 1px solid #ddd;
        padding: 6px 5px;
        text-align: center;
    }}
    .timetable-row-marker-available + div * {{
        color: black !important;
        text-shadow: none !important;
    }}
    
    /* 予約不可行（薄赤・不透明） */
    .timetable-row-marker-booked + div {{
        background-color: #ffcccc !important;
        border-left: 1px solid #ddd;
        border-right: 1px solid #ddd;
        border-bottom: 1px solid #ddd;
        padding: 6px 5px;
        text-align: center;
    }}
    .timetable-row-marker-booked + div * {{
        color: black !important;
        text-shadow: none !important;
    }}
    
    /* 休館日行（グレー・不透明） */
    .timetable-row-marker-closed + div {{
        background-color: #e0e0e0 !important;
        border-left: 1px solid #ddd;
        border-right: 1px solid #ddd;
        border-bottom: 1px solid #ddd;
        padding: 6px 5px;
        text-align: center;
    }}
    .timetable-row-marker-closed + div * {{
        color: black !important;
        text-shadow: none !important;
    }}
    
    /* テーブル内チェックボックスの中央配置調整 */
    .timetable-cb-container {{
        display: flex;
        justify-content: center;
        align-items: center;
        height: 100%;
    }}
    .timetable-cb-container div[data-testid="stCheckbox"] {{
        margin-bottom: 0px;
        padding-top: 4px;
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

st.title("庄原市交通交流施設オンライン予約")


# ==========================================
# 画面1：申請日時と使用場所選択
# ==========================================
if st.session_state.page == "input_datetime":
    st.write("利用可能時間：9:00〜21:00（※12月29日〜1月3日は年末年始のため終日貸出不可）")
    st.subheader("申請日時と使用場所選択")

    room = st.selectbox("部屋を選択してください", [
        "地域交流室１（会議室）", 
        "地域交流室２（多目的スペース）"
    ])

    # 日付のガードレール（過去や今年度末以降を選択不可にする）
    today = datetime.date.today()
    if today.month <= 3:
        fiscal_end_year = today.year
    else:
        fiscal_end_year = today.year + 1
    max_date = datetime.date(fiscal_end_year, 3, 31)

    selected_date = st.date_input(
        "日付を選択してください", 
        min_value=today, 
        max_value=max_date, 
        value=today
    )

    # --- 【大改良】美しさと利便性を両立した「チェックボックス一体型・時間割表」 ---
    st.write(f"### 🕒 {selected_date.strftime('%Y年%m月%d日')} の空き状況および時間帯選択")
    st.write("ご利用を希望される時間帯の「選択」欄にチェックを入れてください（複数選択可）。")
    
    is_closed_date = (selected_date.month == 12 and selected_date.day >= 29) or \
                     (selected_date.month == 1 and selected_date.day <= 3)
                     
    # テーブルヘッダーの描画
    st.markdown('<div class="timetable-header-marker"></div>', unsafe_allow_html=True)
    with st.container():
        h_col1, h_col2, h_col3 = st.columns([1, 2, 2])
        h_col1.markdown("選択")
        h_col2.markdown("時間帯")
        h_col3.markdown("空き状況")

    selected_slots = []
    
    # 9:00から21:00まで1時間ごとにテーブル行を生成
    for h in range(9, 21):
        slot_start = datetime.time(h, 0)
        slot_end = datetime.time(h+1, 0)
        slot_text = f"{h}:00 〜 {h+1}:00"
        
        if is_closed_date:
            st.markdown('<div class="timetable-row-marker-closed"></div>', unsafe_allow_html=True)
            with st.container():
                col1, col2, col3 = st.columns([1, 2, 2])
                with col1:
                    st.markdown('<div class="timetable-cb-container">', unsafe_allow_html=True)
                    st.checkbox("", disabled=True, key=f"slot_cb_{h}")
                    st.markdown('</div>', unsafe_allow_html=True)
                col2.write(slot_text)
                col3.write("⚪ 休館日")
        else:
            # 先約の重複チェック
            booked = False
            for b in st.session_state.bookings:
                if b['date'] == selected_date and b['room'] == room:
                    if not (slot_end <= b['start_time'] or slot_start >= b['end_time']):
                        booked = True
                        break
            
            if booked:
                st.markdown('<div class="timetable-row-marker-booked"></div>', unsafe_allow_html=True)
                with st.container():
                    col1, col2, col3 = st.columns([1, 2, 2])
                    with col1:
                        st.markdown('<div class="timetable-cb-container">', unsafe_allow_html=True)
                        st.checkbox("", disabled=True, key=f"slot_cb_{h}")
                        st.markdown('</div>', unsafe_allow_html=True)
                    col2.write(slot_text)
                    col3.write("🔴 予約不可（先約あり）")
            else:
                # 予約可能な行（薄緑背景の中に、チェックボックスを配置）
                st.markdown('<div class="timetable-row-marker-available"></div>', unsafe_allow_html=True)
                with st.container():
                    col1, col2, col3 = st.columns([1, 2, 2])
                    with col1:
                        st.markdown('<div class="timetable-cb-container">', unsafe_allow_html=True)
                        if st.checkbox("", key=f"slot_cb_{h}"):
                            selected_slots.append(h)
                        st.markdown('</div>', unsafe_allow_html=True)
                    col2.write(slot_text)
                    col3.write("🟢 予約可能")

    st.write("---")

    usage_type = st.radio("利用区分", ["一般使用", "営利、宣伝等での使用"])
    use_ac = st.checkbox("冷暖房を使用する")

    # --- 選択された時間の自動計算およびリアルタイム料金表示 ---
    hours = 0
    total_fee = 0
    start_time = None
    end_time = None
    has_slot_error = False

    if selected_slots:
        selected_slots.sort()
        # 連続して選択されているかの検証（飛び飛びの選択を抑止）
        is_continuous = True
        for i in range(len(selected_slots) - 1):
            if selected_slots[i+1] - selected_slots[i] != 1:
                is_continuous = False
                break
        
        if not is_continuous:
            st.error("❌ エラー：ご利用時間は、途切れることなく連続した時間帯で選択してください。")
            has_slot_error = True
        else:
            start_h = selected_slots[0]
            end_h = selected_slots[-1] + 1
            start_time = datetime.time(start_h, 0)
            end_time = datetime.time(end_h, 0)
            hours = len(selected_slots)
            
            # 料金算出
            if usage_type == "営利、宣伝等での使用":
                if room == "地域交流室１（会議室）":
                    total_fee += 1040 * hours
                else:
                    total_fee += 520 * hours
                if use_ac:
                    total_fee += 310 * hours
            
            # 選択された時間帯の確認表示
            st.info(f"📋 選択中の時間帯: {start_time.strftime('%H:%M')} 〜 {end_time.strftime('%H:%M')}")
    else:
        st.warning("⚠️ 上記の時間割表より、ご利用になる時間帯にチェックを入れてください。")

    # リアルタイム料金の提示
    st.markdown(f"### 💰 現在の概算料金: **{total_fee:,} 円** *(利用時間: {hours}時間)*")

    if st.button("次へ進む（連絡先等の入力へ）"):
        if not selected_slots:
            st.error("❌ エラー：時間帯が選択されていません。時間割表の「選択」欄にチェックを入れてください。")
        elif has_slot_error:
            st.error("❌ エラー：時間帯の選択内容に不備があります。修正してください。")
        elif is_closed_date:
            st.error("❌ エラー：年末年始の休館期間のため、予約手続きを進めることはできません。")
        else:
            # 入力検証を通過した場合、次画面へ遷移
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
    
    # 月間カレンダー（折りたたみ式）
    with st.expander("🗓️ 全体の予約状況（月間カレンダー）を見る"):
        st.write("※緑表示の場合は予約可能、赤表示の場合は予約不可となります")
        
        start_grid_date = selected_date.replace(day=1)
        
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

        tab1, tab2 = st.tabs(["地域交流室１（会議室）の状況", "地域交流室２（多目的スペース）の状況"])
        
        # --- タブ1: 地域交流室1 ---
        with tab1:
            calendar_events_room1 = []
            loop_date = start_grid_date
            while loop_date <= max_date:
                is_closed = (loop_date.month == 12 and loop_date.day >= 29) or \
                            (loop_date.month == 1 and loop_date.day <= 3)
                if is_closed:
                    calendar_events_room1.append({"title": "⚪ 休館", "start": loop_date.strftime('%Y-%m-%d'), "allDay": True, "color": "#e0e0e0"})
                else:
                    has_booking = False
                    for b in st.session_state.bookings:
                        if b['date'] == loop_date and b['room'] == "地域交流室１（会議室）":
                            has_booking = True
                            break
                    if has_booking:
                        calendar_events_room1.append({"title": "🔴 予約不可", "start": loop_date.strftime('%Y-%m-%d'), "allDay": True, "color": "#ff4b4b"})
                    else:
                        calendar_events_room1.append({"title": "🟢 予約可能", "start": loop_date.strftime('%Y-%m-%d'), "allDay": True, "color": "#2cd15a"})
                loop_date += datetime.timedelta(days=1)
                
            calendar(events=calendar_events_room1, options=calendar_options, key="calendar_room1")

        # --- タブ2: 地域交流室2 ---
        with tab2:
            calendar_events_room2 = []
            loop_date = start_grid_date
            while loop_date <= max_date:
                is_closed = (loop_date.month == 12 and loop_date.day >= 29) or \
                            (loop_date.month == 1 and loop_date.day <= 3)
                if is_closed:
                    calendar_events_room2.append({"title": "⚪ 休館", "start": loop_date.strftime('%Y-%m-%d'), "allDay": True, "color": "#e0e0e0"})
                else:
                    has_booking = False
                    for b in st.session_state.bookings:
                        if b['date'] == loop_date and b['room'] == "地域交流室２（多目的スペース）":
                            has_booking = True
                            break
                    if has_booking:
                        calendar_events_room2.append({"title": "🔴 予約不可", "start": loop_date.strftime('%Y-%m-%d'), "allDay": True, "color": "#ff4b4b"})
                    else:
                        calendar_events_room2.append({"title": "🟢 予約可能", "start": loop_date.strftime('%Y-%m-%d'), "allDay": True, "color": "#2cd15a"})
                loop_date += datetime.timedelta(days=1)
                
            calendar(events=calendar_events_room2, options=calendar_options, key="calendar_room2")


# ==========================================
# 画面2：使用者情報の入力
# ==========================================
elif st.session_state.page == "input_personal_info":
    st.subheader("使用者情報の入力")
    
    temp = st.session_state.temp_booking
    st.info(f"📋 選択中の日時: {temp['date'].strftime('%Y/%m/%d')} {temp['start_time'].strftime('%H:%M')}〜{temp['end_time'].strftime('%H:%M')} ({temp['room']})")

    user_name = st.text_input("お名前 / 団体名（必須）")
    user_address = st.text_input("ご住所（必須）")
    user_phone = st.text_input