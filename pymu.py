import fitz  # PyMuPDF
import streamlit as st
import io

# 웹 페이지 제목 및 설명
st.title("📄 PDF 텍스트 및 좌표 추출기")
st.write("PDF 파일을 업로드하면 문단별 텍스트를 추출하고, 추출 영역이 빨간색 박스로 표시된 PDF를 확인 및 다운로드할 수 있습니다.")

# 1. 웹에서 PDF 파일 업로드 받기
uploaded_file = st.file_uploader("PDF 파일을 업로드하세요", type=["pdf"])

if uploaded_file is not None:
    # 2. 업로드된 파일을 바이트 스트림으로 읽어 PyMuPDF 객체로 변환
    pdf_bytes = uploaded_file.read()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    
    st.subheader("📑 목차 정보")
    toc = doc.get_toc()
    if toc:
        for item in toc:
            level, title, page = item
            st.write(f"L{level} | 페이지 {page} | {title}")
    else:
        st.info("이 PDF 문서에는 메타데이터로 저장된 목차 정보가 없습니다.")
        
    st.divider()
    st.subheader("📝 문단 및 문단내용 추출 결과")
    
    # 텍스트가 길 수 있으므로 접었다 펼칠 수 있는 Expander 사용
    with st.expander("추출된 텍스트 자세히 보기", expanded=True):
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            blocks = page.get_text("blocks")
            
            for b in blocks:
                block_type = b[6]
                
                # 텍스트 블록(0)인 경우만 처리
                if block_type == 0:
                    x0, y0, x1, y1 = b[:4]
                    text = b[4].strip()
                    
                    if text:
                        # 웹 화면에 좌표 및 텍스트 출력
                        st.markdown(f"**[페이지 {page_num + 1}] 좌표:** `(X0: {x0:.1f}, Y0: {y0:.1f}, X1: {x1:.1f}, Y1: {y1:.1f})`")
                        st.text(text)
                        st.markdown("---")
                        
                        # 원문 PDF 메모리 객체에 빨간색 사각형 그리기
                        rect = fitz.Rect(x0, y0, x1, y1)
                        page.draw_rect(rect, color=(1, 0, 0), width=1)
    
    # 3. 처리가 완료된 PDF를 메모리 버퍼(io.BytesIO)에 저장
    output_pdf_buffer = io.BytesIO()
    doc.save(output_pdf_buffer)
    doc.close()
    
    st.success("✅ PDF 처리가 완료되었습니다! 아래 버튼을 눌러 결과 파일을 다운로드하세요.")
    
    # 4. 웹에서 다운로드할 수 있는 버튼 생성
    st.download_button(
        label="📥 좌표 확인용 PDF 다운로드",
        data=output_pdf_buffer.getvalue(),
        file_name=f"좌표표시_{uploaded_file.name}",
        mime="application/pdf"
    )
