import fitz  # PyMuPDF
import streamlit as st
import io

# 웹 페이지 레이아웃을 넓게 설정 (미리보기를 크게 보기 위함)
st.set_page_config(layout="wide")

st.title("📄 PDF 텍스트 및 좌표 추출기")
st.write("PDF 파일을 업로드하면 텍스트를 추출하고, 추출 영역이 표시된 원문 이미지를 탭으로 나누어 확인할 수 있습니다.")

uploaded_file = st.file_uploader("PDF 파일을 업로드하세요", type=["pdf"])

if uploaded_file is not None:
    pdf_bytes = uploaded_file.read()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    
    # 상단: 목차 정보 출력
    st.subheader("📑 목차 정보")
    toc = doc.get_toc()
    if toc:
        for item in toc:
            level, title, page = item
            st.write(f"L{level} | 페이지 {page} | {title}")
    else:
        st.info("이 PDF 문서에는 메타데이터로 저장된 목차 정보가 없습니다.")
        
    st.divider()
    
    # 두 개의 탭 생성
    tab1, tab2 = st.tabs(["📝 추출 결과 (텍스트 및 좌표)", "🖼️ 원문 좌표 표기 (미리보기)"])
    
    with tab1:
        st.subheader("텍스트 및 좌표 추출 내역")
    
    with tab2:
        st.subheader("원문 적용 미리보기")

    # 페이지별 순회 처리
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        blocks = page.get_text("blocks")
        
        with tab1:
            st.markdown(f"#### 📄 Page {page_num + 1}")
        
        for b in blocks:
            block_type = b[6]
            
            if block_type == 0:  # 텍스트 블록
                x0, y0, x1, y1 = b[:4]
                text = b[4].strip()
                
                if text:
                    # 탭 1: 텍스트 및 좌표 출력
                    with tab1:
                        st.markdown(f"**좌표:** `(X0: {x0:.1f}, Y0: {y0:.1f}, X1: {x1:.1f}, Y1: {y1:.1f})`")
                        st.text(text)
                        st.markdown("---")
                    
                    # 탭 2를 위해 메모리상의 PDF 페이지에 빨간색 사각형 그리기
                    rect = fitz.Rect(x0, y0, x1, y1)
                    page.draw_rect(rect, color=(1, 0, 0), width=1)
        
        # 페이지 처리가 끝난 후, 탭 2에 이미지로 렌더링하여 출력
        with tab2:
            # 해상도(dpi)를 높여서 텍스트가 깨지지 않게 변환 (기본값보다 선명함)
            pix = page.get_pixmap(dpi=150)
            img_bytes = pix.tobytes("png")
            
            # Streamlit 이미지 컴포넌트로 출력
            st.image(img_bytes, caption=f"페이지 {page_num + 1} 미리보기", use_column_width=True)
            st.markdown("---")

    # 3. 처리가 완료된 전체 PDF를 메모리 버퍼에 저장
    output_pdf_buffer = io.BytesIO()
    doc.save(output_pdf_buffer)
    doc.close()
    
    st.success("✅ PDF 처리가 완료되었습니다! 아래 버튼을 눌러 전체 결과 파일을 다운로드하세요.")
    
    # 4. 결과 PDF 다운로드 버튼
    st.download_button(
        label="📥 전체 좌표 확인용 PDF 다운로드",
        data=output_pdf_buffer.getvalue(),
        file_name=f"좌표표시_{uploaded_file.name}",
        mime="application/pdf"
    )
