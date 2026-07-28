import fitz  # PyMuPDF 라이브러리 설치 필요: pip install pymupdf

def extract_pdf_with_coordinates(input_pdf_path, output_pdf_path):
    # PDF 문서 열기
    doc = fitz.open(input_pdf_path)
    
    # 1. 목차(TOC) 정보 추출 (PDF에 메타데이터로 목차가 있는 경우)
    toc = doc.get_toc()
    if toc:
        print("=== [목차 정보] ===")
        for item in toc:
            level, title, page = item
            print(f"L{level} | 페이지 {page} | {title}")
        print("=" * 50 + "\n")

    print("=== [문단 및 문단내용 추출] ===")
    
    # 2. 페이지별 문단(블록) 추출
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        
        # get_text("blocks")는 페이지의 텍스트를 문단 단위로 묶어서 반환합니다.
        # 반환 형태: (x0, y0, x1, y1, "text", block_no, block_type)
        blocks = page.get_text("blocks")
        
        for b in blocks:
            block_type = b[6]
            
            # block_type 0은 텍스트 블록을 의미합니다. (1은 이미지)
            if block_type == 0:
                # 좌표 정보 (왼쪽 위 x0, y0 / 오른쪽 아래 x1, y1)
                x0, y0, x1, y1 = b[:4]
                text = b[4].strip()
                
                # 내용이 있는 문단만 출력
                if text:
                    # 콘솔에 좌표와 내용 출력
                    print(f"[페이지 {page_num + 1}] 좌표: (X0: {x0:.1f}, Y0: {y0:.1f}, X1: {x1:.1f}, Y1: {y1:.1f})")
                    print(f"{text}\n{'-' * 40}")
                    
                    # 3. 추출한 좌표를 원문 PDF에 그리기 (시각적 확인용)
                    # 빨간색 테두리 사각형을 그립니다.
                    rect = fitz.Rect(x0, y0, x1, y1)
                    page.draw_rect(rect, color=(1, 0, 0), width=1)
                    
    # 좌표가 그려진 새로운 PDF로 저장
    doc.save(output_pdf_path)
    doc.close()
    print(f"\n완료되었습니다. 추출 영역이 표시된 PDF가 '{output_pdf_path}'로 저장되었습니다.")

# 실행 예시 (실제 파일 경로로 변경하여 실행하세요)
# extract_pdf_with_coordinates("논문원본.pdf", "좌표확인용_결과.pdf")
