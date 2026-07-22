import os
import sqlite3
import streamlit as st
import json

st.set_page_config(page_title="Starter TOEIC Học Tập & Quản Trị", layout="wide")

DB_NAME = "starter_toeic_pro.db"

# ==========================================
# CONSTANTS & HELPERS
# ==========================================
CHAPTER_TYPES = ["GRAMMAR", "SKILLS"]
PART_TYPES = ["PART1", "PART2", "PART3", "PART4", "PART5", "PART6", "PART7"]

def get_audio_path(unit_id, audio_file):
    """Trả về đường dẫn chuẩn hóa theo từng phân mục unit như anh Khải cấu hình"""
    if not audio_file:
        return ""
    unit_str = f"unit_{str(unit_id).zfill(2)}"
    return f"processed_audio/{unit_str}/{audio_file}.mp3"

# ==========================================
# LAZY LOADING DATABASE FUNCTIONS
# ==========================================
def get_grammar_theory(unit_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT theory_content FROM grammar_theory WHERE unit_id = ?", (unit_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def get_questions_by_tab(unit_id, chapter_type):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM questions WHERE unit_id = ? AND chapter_type = ? ORDER BY part_type, question_number", 
        (unit_id, chapter_type)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ==========================================
# ADMIN MANAGEMENT FUNCTIONS (CRUD)
# ==========================================
def update_theory_db(unit_id, content):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO grammar_theory (unit_id, theory_content) VALUES (?, ?)", (unit_id, content))
    conn.commit()
    conn.close()

def delete_question_db(q_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM questions WHERE id = ?", (q_id,))
    conn.commit()
    conn.close()

def save_question_db(q_id, data):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    if q_id == "NEW":
        cursor.execute("""
            INSERT INTO questions (unit_id, chapter_type, part_type, question_number, question_text, 
                                   option_a, option_b, option_c, option_d, correct_answer, explanation, audio_file, image_file, passage_text)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (data['unit_id'], data['chapter_type'], data['part_type'], data['question_number'], data['question_text'],
              data['option_a'], data['option_b'], data['option_c'], data['option_d'], data['correct_answer'], data['explanation'],
              data['audio_file'], data['image_file'], data['passage_text']))
    else:
        cursor.execute("""
            UPDATE questions SET 
                unit_id=?, chapter_type=?, part_type=?, question_number=?, question_text=?, 
                option_a=?, option_b=?, option_c=?, option_d=?, correct_answer=?, explanation=?, audio_file=?, image_file=?, passage_text=?
            WHERE id=?
        """, (data['unit_id'], data['chapter_type'], data['part_type'], data['question_number'], data['question_text'],
              data['option_a'], data['option_b'], data['option_c'], data['option_d'], data['correct_answer'], data['explanation'],
              data['audio_file'], data['image_file'], data['passage_text'], q_id))
    conn.commit()
    conn.close()

# ==========================================
# SMART TOEIC RENDERER (PART 1 -> PART 7)
# ==========================================
def render_toeic_item(q, prefix_key):
    """Hiển thị động linh hoạt cho cả câu đơn lẫn đoạn văn phức hợp (Part 3,4,6,7)"""
    # 1. Nếu có đoạn văn bối cảnh chung (Bài đọc, hội thoại)
    if q.get('passage_text'):
        st.info("📖 ĐOẠN VĂN / BỐI CẢNH ĐỌC HIỂU HOẶC HỘI THOẠI CHUNG:")
        st.markdown(f"*{q['passage_text']}*")
    
    # 2. Tiêu đề câu hỏi
    st.markdown(f"**Câu {q['question_number']}:** {q['question_text'] if q['question_text'] else '(Nghe và chọn đáp án đúng)'}")
    
    # 3. Audio xử lý động theo thư mục phân tầng unit_XX
    if q.get('audio_file'):
        audio_path = get_audio_path(q['unit_id'], q['audio_file'])
        if os.path.exists(audio_path):
            st.audio(audio_path, format="audio/mp3")
        else:
            st.caption(f"🎵 [File âm thanh: {q['audio_file']}.mp3]")
            
    # 4. Hình ảnh minh họa (Part 1 hoặc biểu đồ)
    if q.get('image_file'):
        img_path = f"extracted_images/{q['image_file']}"
        if os.path.exists(img_path):
            st.image(img_path, width=400)
        else:
            st.caption(f"🖼️ [Hình ảnh minh họa: {q['image_file']}]")

    # 5. Lựa chọn đáp án
    options = [f"A. {q['option_a']}", f"B. {q['option_b']}", f"C. {q['option_c']}", f"D. {q['option_d']}"]
    choice = st.radio(f"Chọn đáp án câu {q['question_number']}:", options, index=None, key=f"{prefix_key}_{q['id']}_{q['question_number']}")
    return choice

# ==========================================
# MAIN INTERFACE LAYOUT
# ==========================================
st.sidebar.title("🎛️ BÀN ĐIỀU KHIỂN")
app_mode = st.sidebar.radio("CHẾ ĐỘ ỨNG DỤNG:", ["👨‍🎓 HỌC VIÊN LUYỆN TẬP", "🛠️ QUẢN TRỊ VIÊN (CRUD)"])

unit_list = {i: f"Unit {str(i).zfill(2)}" for i in range(1, 13)}
selected_unit = st.sidebar.selectbox("CHỌN UNIT:", list(unit_list.keys()), format_func=lambda x: unit_list[x])

if app_mode == "👨‍🎓 HỌC VIÊN LUYỆN TẬP":
    st.title(f"📊 LUYỆN TẬP TOÀN DIỆN - {unit_list[selected_unit]}")
    tab1, tab2, tab3 = st.tabs(["📘 LÝ THUYẾT TIẾNG VIỆT", "✍️ BÀI TẬP NGỮ PHÁP (Ch1)", "🎧 LUYỆN KỸ NĂNG NGHE & ĐỌC (Ch2)"])

    # TAB 1: LÝ THUYẾT (Lazy Loaded)
    with tab1:
        theory = get_grammar_theory(selected_unit)
        if theory:
            st.markdown(theory)
        else:
            st.info("📚 Nội dung lý thuyết của Unit này đang được cập nhật...")

    # TAB 2: BÀI TẬP NGỮ PHÁP (Lazy Loaded)
    with tab2:
        st.subheader("🏋️ Grammar Practice")
        grammar_qs = get_questions_by_tab(selected_unit, "GRAMMAR")
        
        if not grammar_qs:
            st.info("ℹ️ Hiện chưa có dữ liệu câu hỏi ngữ pháp cho Unit này.")
        else:
            with st.form(key=f"form_grammar_{selected_unit}"):
                user_choices = {}
                for q in grammar_qs:
                    user_choices[q['id']] = render_toeic_item(q, "student_gr")
                    st.write("---")
                
                # FIX LỖI: Đảm bảo nút submit nằm hoàn toàn trong form
                submit_grammar = st.form_submit_button("🎯 CHẤM ĐIỂM BÀI LÀM")
                
            if submit_grammar:
                st.write("### 📊 KẾT QUẢ CHI TIẾT:")
                for q in grammar_qs:
                    ans = user_choices[q['id']][0] if user_choices[q['id']] else "Chưa chọn"
                    correct = str(q['correct_answer']).strip().upper()
                    if ans == correct:
                        st.success(f"Câu {q['question_number']}: ĐÚNG! ({ans})")
                    else:
                        st.error(f"Câu {q['question_number']}: SAI! Đáp án của anh: {ans} | Đúng: {correct}")
                    if q['explanation']:
                        st.caption(f"💡 Giải thích: {q['explanation']}")

    # TAB 3: LUYỆN KỸ NĂNG NGHE & ĐỌC (Lazy Loaded - Full Part 1 -> Part 7)
    with tab3:
        st.subheader("🎧 Skills Practice (Part 1 - Part 7)")
        skills_qs = get_questions_by_tab(selected_unit, "SKILLS")
        
        if not skills_qs:
            st.info("ℹ️ Hiện chưa có dữ liệu Skills cho Unit này.")
        else:
            with st.form(key=f"form_skills_{selected_unit}"):
                user_skills_choices = {}
                
                # Phân nhóm hiển thị theo Part để cấu trúc bài thi trực quan hơn
                for part in PART_TYPES:
                    part_qs = [q for q in skills_qs if q['part_type'] == part]
                    if part_qs:
                        st.markdown(f"### ⚡ {part}")
                        for q in part_qs:
                            user_skills_choices[q['id']] = render_toeic_item(q, f"student_sk_{part}")
                            st.write("---")
                
                # FIX LỖI: Đút nút submit vào trong khối form
                submit_skills = st.form_submit_button("🎯 CHẤM ĐIỂM PHẦN THI KỸ NĂNG")
                
            if submit_skills:
                st.write("### 📊 KẾT QUẢ PHẦN THI KỸ NĂNG:")
                for q in skills_qs:
                    ans = user_skills_choices[q['id']][0] if user_skills_choices[q['id']] else "Chưa chọn"
                    correct = str(q['correct_answer']).strip().upper()
                    if ans == correct:
                        st.success(f"Câu {q['question_number']} ({q['part_type']}): ĐÚNG! ({ans})")
                    else:
                        st.error(f"Câu {q['question_number']} ({q['part_type']}): SAI! Anh chọn: {ans} | Đúng: {correct}")
                    if q['explanation']:
                        st.caption(f"💡 Giải thích: {q['explanation']}")

# ==========================================
# MODE INTERFACE: ADMIN CRUD MANAGEMENT
# ==========================================
else:
    st.title(f"🛠️ PHÂN HỆ QUẢN TRỊ - {unit_list[selected_unit]}")
    adm_tab1, adm_tab2 = st.tabs(["📝 SỬA LÝ THUYẾT UNIT", "🗂️ QUẢN LÝ CÂU HỎI (GRAMMAR & SKILLS)"])
    
    with adm_tab1:
        st.subheader("Chỉnh sửa nội dung Lý thuyết dịch tiếng Việt")
        current_theory = get_grammar_theory(selected_unit) or ""
        theory_input = st.text_area("Nội dung (Hỗ trợ định dạng Markdown):", value=current_theory, height=350)
        if st.button("💾 LƯU LÝ THUYẾT"):
            update_theory_db(selected_unit, theory_input)
            st.success("Đã cập nhật lý thuyết thành công!")
            
    with adm_tab2:
        st.subheader("Danh sách câu hỏi hiện tại")
        c_type = st.selectbox("Lọc theo phân loại Chapter:", CHAPTER_TYPES)
        all_qs = get_questions_by_tab(selected_unit, c_type)
        
        # Chọn câu hỏi để Sửa hoặc Thêm câu hỏi mới
        q_options = {"NEW": "➕ Thêm câu hỏi mới hoàn toàn"}
        for q in all_qs:
            q_options[q['id']] = f"[{q['part_type']}] Câu số {q['question_number']} - ID: {q['id']}"
            
        selected_q_id = st.selectbox("Chọn câu hỏi cần thao tác:", list(q_options.keys()), format_func=lambda x: q_options[x])
        
        # Đổ dữ liệu cũ lên form nếu là sửa
        target_q = next((q for q in all_qs if q['id'] == selected_q_id), None) if selected_q_id != "NEW" else None
        
        with st.form(key="crud_question_form"):
            st.write("### THÔNG TIN CHI TIẾT CÂU HỎI")
            col1, col2, col3 = st.columns(3)
            with col1:
                q_num = st.number_input("Số thứ tự câu hỏi:", value=target_q['question_number'] if target_q else 1, step=1)
                p_type = st.selectbox("Phân hệ Part:", PART_TYPES, index=PART_TYPES.index(target_q['part_type']) if target_q else 0)
            with col2:
                aud_file = st.text_input("Tên file Audio (không điền đuôi mp3):", value=target_q['audio_file'] if target_q else "")
                img_file = st.text_input("Tên file Ảnh minh họa:", value=target_q['image_file'] if target_q else "")
            with col3:
                corr_ans = st.selectbox("Đáp án đúng:", ["A", "B", "C", "D"], index=["A", "B", "C", "D"].index(target_q['correct_answer'].strip().upper()) if target_q else 0)
            
            pass_txt = st.text_area("Đoạn văn bối cảnh / Văn bản dùng chung (Part 3, 4, 6, 7):", value=target_q['passage_text'] if target_q else "")
            q_txt = st.text_area("Nội dung câu hỏi chữ (Để trống nếu chỉ có Audio/Part 1):", value=target_q['question_text'] if target_q else "")
            
            c4, c5, c6, c7 = st.columns(4)
            with c4: opt_a = st.text_input("Lựa chọn A:", value=target_q['option_a'] if target_q else "")
            with c5: opt_b = st.text_input("Lựa chọn B:", value=target_q['option_b'] if target_q else "")
            with c6: opt_c = st.text_input("Lựa chọn C:", value=target_q['option_c'] if target_q else "")
            with c7: opt_d = st.text_input("Lựa chọn D:", value=target_q['option_d'] if target_q else "")
            
            expl_txt = st.text_area("Giải thích chi tiết đáp án:", value=target_q['explanation'] if target_q else "")
            
            submit_crud = st.form_submit_button("💾 XÁC NHẬN LƯU DỮ LIỆU CÂU HỎI")
            
        if submit_crud:
            new_data = {
                'unit_id': selected_unit, 'chapter_type': c_type, 'part_type': p_type, 'question_number': q_num,
                'question_text': q_txt, 'option_a': opt_a, 'option_b': opt_b, 'option_c': opt_c, 'option_d': opt_d,
                'correct_answer': corr_ans, 'explanation': expl_txt, 'audio_file': aud_file, 'image_file': img_file, 'passage_text': pass_txt
            }
            save_question_db(selected_q_id, new_data)
            st.success("Hệ thống đã cập nhật dữ liệu vào cơ sở dữ liệu thành công!")
            st.rerun()
            
        # Nút xóa câu hỏi nằm ngoài form để tránh xung đột
        if selected_q_id != "NEW":
            st.write("---")
            if st.button("❌ XÓA CÂU HỎI NÀY KHỎI HỆ THỐNG"):
                delete_question_db(selected_q_id)
                st.warning("Đã xóa câu hỏi khỏi cơ sở dữ liệu.")
                st.rerun()