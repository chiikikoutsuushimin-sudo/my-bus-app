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
    
    # === 【視認性の大改良】白い箱を消し、動画の上に「白文字＋くっきり黒ぶち」を表示 === #
    .main .block-container {{
        background-color: transparent !important; /* 白い背景の箱を完全に撤廃 */
        padding: 2.5rem;
        box-shadow: none !important;
    }}
    
    /* 通常の文字、チェックボックス、ラジオボタンの文字をすべて「白文字＋強力な黒ぶち」にする */
    .main .block-container, 
    .main .block-container *, 
    .stMarkdown, .stSubheader, .stTitle {{
        color: #ffffff !important; /* 文字は純白 */
        /* 上下左右・斜めの全方向に1ピクセルの黒い影を敷き詰め、クッキリした綺麗な縁取りを作ります */
        text-shadow: 
            1px 1px 0px #000000,
            -1px -1px 0px #000000,
            1px -1px 0px #000000,
            -1px 1px 0px #000000,
            0px 1px 0px #000000,
            0px -1px 0px #000000,
            1px 0px 0px #000000,
            -1px 0px 0px #000000,
            2px 2px 4px rgba(0,0,0,0.8) !important;
    }}
    
    /* 【安全ガード】入力フォーム（名前や住所の欄）は、文字が見えなくならないよう白背景・黒文字（ぶちなし）に固定 */
    input, select, textarea {{
        color: #111111 !important;
        background-color: #ffffff !important;
        text-shadow: none !important;
    }}
    
    /* ボタンは目立つように「青背景に白文字（ぶちなし）」にします */
    button, p[data-testid="stFormSubmitButton"] button {{
        color: #ffffff !important;
        background-color: #007bff !important;
        border-radius: 5px !important;
        text-shadow: none !important;
    }}
    
    /* 【安全ガード】カレンダーが入っている折りたたみ（Expander）は、カレンダーが動画と混ざらないよう全体を白背景にする */
    div[data-testid="stExpander"] {{
        background-color: #ffffff !important;
        border-radius: 10px !important;
        padding: 15px !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1) !important;
    }}
    
    /* カレンダーと折りたたみの中の文字は、すべて通常の読みやすい黒文字（ぶちなし）に戻す */
    div[data-testid="stExpander"] *, .fc * {{
        color: #111111 !important;
        text-shadow: none !important;
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

    # --- シンプルで迷わない、通常の縦並びチェックボックス形式 ---
    st.write(f"### 🕒 {selected_date.strftime('%Y年%m月%d日')} の空き状況および時間帯選択")
    st.write("ご利用を希望される時間帯にチェックを入れてください（複数選択可）。")
    
    is_closed_date = (selected_date.month == 12 and selected_date.day >= 29) or \
                     (selected_date.month == 1 and selected_date.day <= 3)
                     
    selected_slots = []
    
    # 9:00〜21:00まで、1時間ごとに1つずつチェックボックスを並べる
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
        
        # 予約できない時間帯は、最初からグレーアウト（disabled=True）にして触らせない安全設計
        if is_disabled:
            st.checkbox(f"{slot_text}  【 {status} 】", value=False, disabled=True, key=f"slot_{h}")
        else:
            if st.checkbox(f"{slot_text}  【 {status} 】", value=False, key=f"slot_{h}"):
                selected_slots.append(h)

    st.write("---")

    usage_type = st.radio("利用区分", ["一般使用", "営利、宣伝等での使用"])
    use_ac = st.checkbox("冷暖房を使用する")

    # --- チェック内容のリアルタイム検証と料金計算 ---
    hours = 0
    total_fee = 0
    start_time = None
    end_time = None
    has_slot_error = False

    if selected_slots:
        selected_slots.sort()
        # 連続した時間帯が選ばれているかのチェック
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
            
            # 料金計算
            if usage_type == "営利、宣伝等での使用":
                if room == "地域交流室１（会議室）":
                    total_fee += 1040 * hours
                else:
                    total_fee += 520 * hours
                if use_ac:
                    total_fee += 310 * hours
            
            # 選択中の確定時間を明示
            st.info(f"📋 選択中の時間帯: {start_time.strftime('%H:%M')} 〜 {end_time.strftime('%H:%M')}")
    else:
        st.warning("⚠️ 上記の一覧より、ご利用になる時間帯にチェックを入れてください。")

    # リアルタイム料金の提示
    st.markdown(f"### 💰 現在の概算料金: **{total_fee:,} 円** *(利用時間: {hours}時間)*")

    if st.button("次へ進む（連絡先等の入力へ）"):
        if not selected_slots:
            st.error("❌ エラー：時間帯が選択されていません。ご希望の時間帯にチェックを入れてください。")
        elif has_slot_error:
            st.error("❌ エラー：時間帯の選択内容に不備があります。連続した時間になるよう修正してください。")
        elif is_closed_date:
            st.error("❌ エラー：年末年始の休館期間のため、予約手続きを進めることはできません。")
        else:
            # すべてのガードレールを通過したら次画面へ
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