import streamlit as st
import datetime
import base64

# --- 【追加機能】背景に動画を設定する関数 ---
def set_bg_video(video_file):
    with open(video_file, "rb") as f:
        video_bytes = f.read()
    # 動画をプログラムで扱える文字列（Base64）に変換
    b64_video = base64.b64encode(video_bytes).decode()
    
    # --- 【劇的改善】文字の可読性を高めるためのCSS ---
    video_html = f'''
    <style>
    /* アプリ本来の背景を透明にする */
    .stApp {{
        background: transparent;
    }}
    /* 動画を画面いっぱいに固定する */
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
    /* 【改善点】文字の背後の白座布団を不透明度100%にする */
    .main .block-container {{
        background-color: rgba(255, 255, 255, 1.0); /* 不透明 */
        padding: 2.5rem;
        border-radius: 15px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }}
    
    /* 【最重要】すべての文字に黒いドロップシャドウ（アウトライン効果）を追加 */
    .stApp, .stApp *, .stMarkdown, .stSubheader, .stTitle, .stSelectbox label, .stRadio label, .stCheckbox label {{
        color: white !important; /* 文字自体を白にする */
        text-shadow: 1px 1px 1px black, -1px -1px 1px black, 1px -1px 1px black, -1px 1px 1px black, 2px 2px 3px rgba(0,0,0,0.8) !important;
    }}
    
    /* 入力欄やボタンの中の文字はそのまま */
    input, select, textarea, button {{
        color: black !important;
        text-shadow: none !important;
    }}
    </style>
    <video autoplay loop muted playsinline id="bg-video">
        <source src="data:video/mp4;base64,{b64_video}" type="video/mp4">
    </video>
    '''
    st.markdown(video_html, unsafe_allow_html=True)

# 背景動画の読み込み
try:
    set_bg_video("background.mp4")
except FileNotFoundError:
    st.warning("⚠️ 背景動画ファイル（background.mp4）が見つかりません。app.pyと同じフォルダに配置してください。")


# --- 以下は元のアプリ機能（文字色はCSSで制御） ---
st.title("施設予約システム")
st.write("利用可能期間：12月29日〜翌年1月3日 (9:00〜21:00)")

if "bookings" not in st.session_state:
    st.session_state.bookings = []

st.subheader("予約内容の入力")

room = st.selectbox("部屋を選択してください", [
    "地域交流室１（会議室）", 
    "地域交流室２（多目的スペース）"
])

selected_date = st.date_input("日付を選択してください")

time_options = [datetime.time(h, 0) for h in range(9, 22)]
col1, col2 = st.columns(2)
with col1:
    start_time = st.selectbox("開始時間", time_options[:-1])
with col2:
    end_time = st.selectbox("終了時間", time_options[1:])

usage_type = st.radio("利用区分", ["一般使用", "営利、宣伝等での使用"])
use_ac = st.checkbox("冷暖房を使用する")

if st.button("予約する"):
    has_error = False

    is_valid_date = (selected_date.month == 12 and selected_date.day >= 29) or \
                    (selected_date.month == 1 and selected_date.day <= 3)
    if not is_valid_date:
        st.error("❌ エラー：予約可能な日時は「12月29日から翌年の1月3日まで」です。")
        has_error = True

    if start_time >= end_time:
        st.error("❌ エラー：終了時間は開始時間より後に設定してください。")
        has_error = True

    for b in st.session_state.bookings:
        if b['date'] == selected_date and b['room'] == room:
            if not (end_time <= b['start_time'] or start_time >= b['end_time']):
                st.error("❌ エラー：選択された日時はすでに予約が入っています。（重複予約不可）")
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

        st.session_state.bookings.append({
            "room": room,
            "date": selected_date,
            "start_time": start_time,
            "end_time": end_time,
            "usage_type": usage_type,
            "use_ac": use_ac,
            "fee": total_fee,
            "hours": hours
        })

        st.success(f"🎉 予約が完了しました！ 合計金額: {total_fee}円 （利用時間: {hours}時間）")

st.write("---")
st.subheader("現在の予約状況")
if len(st.session_state.bookings) == 0:
    st.info("現在、予約はありません。")
else:
    for i, b in enumerate(st.session_state.bookings):
        ac_text = "冷暖房あり" if b['use_ac'] else "冷暖房なし"
        st.write(f"**予約{i+1}**: {b['date'].strftime('%Y/%m/%d')} {b['start_time'].strftime('%H:%M')}〜{b['end_time'].strftime('%H:%M')} | "
                 f"{b['room']} | {b['usage_type']} ({ac_text}) | **{b['fee']}円**")