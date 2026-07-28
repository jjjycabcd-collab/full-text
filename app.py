import streamlit as st
import requests
from bs4 import BeautifulSoup
import time
import fitz  # PyMuPDF 라이브러리 추가 (PDF 렌더링용)

# GROBID 공식 퍼블릭 API 엔드포인트 (Hugging Face Spaces 기반 신규 안정화 서버)
GROBID_PUBLIC_URL = "https://grobidOrg-grobid.hf.space/api/processFulltextDocument"

# 추출된 좌표를 모아둘 리스트 (UI 렌더링용)
extracted_coords_list = []

def classify_reference_type(title: str, raw_type: str) -> str:
    """
    참고문헌 제목과 기본 메타데이터를 기반으로 자료유형을 자동 재분류합니다.
    """
    title_lower = title.lower()
    
    # 1. 단행본 분류 (도서, 표준, 지침)
    book_keywords = ['표준', '지침', '도서', 'standard', 'guideline', 'book', 'manual']
    if raw_type == 'book' or any(kw in title_lower for kw in book_keywords):
        return "단행본"
        
    # 2. 기타 분류 (보도자료, 신문, 연보)
    etc_keywords = ['보도자료', '신문', '연보', 'press release', 'newspaper', 'annals', 'report']
    if raw_type in ['web', 'legal'] or any(kw in title_lower for kw in etc_keywords):
        return "기타"
        
    # 3. 기본 학술지/논문
    return "학술지/논문"

def extract_coords(tag) -> str:
    """TEI-XML 태그 내 PDF 상의 좌표(page, x, y, width, height) 정보를 추출하고 리스트에 저장합니다."""
    coords = tag.get('coords') if tag else None
    if coords:
        # 하이라이트 렌더링을 위해 전역 리스트에 수집
        extracted_coords_list.append(coords)
        return f"📍 `[좌표: {coords}]`"
    return ""

# UI 기본 설정
st.set_page_config(page_title="GROBID Open Access 논문 파서", layout="wide")
st.title("📄 Open Access 논문 자동 파싱 & 메타데이터 추출기")
st.caption("GROBID Cloud Public API를 활용하여 PDF 논문의 구조, 위치 좌표 및 참고문헌을 분석합니다.")

uploaded_file = st.file_uploader("분석할 PDF 논문을 업로드하세요", type=["pdf"])

if uploaded_file is not None:
    if st.button("🚀 파싱 시작", type="primary"):
        start_time = time.time()
        # 이전 파싱 좌표 초기화
        extracted_coords_list.clear()
        
        with st.spinner("GROBID 서버에서 문헌을 파싱하는 중입니다... (OA 논문 용량이 큰 경우 15~30초 소요)"):
            files = {'input': (uploaded_file.name, uploaded_file.getvalue(), 'application/pdf')}
            
            # 파싱에 필요한 좌표 대상 태그 지정
            data = {
                'teiCoordinates': ['persName', 'figure', 'table', 'head', 'p', 'biblStruct', 'formula']
            }
            
            try:
                response = requests.post(GROBID_PUBLIC_URL, files=files, data=data, timeout=180)
                
                if response.status_code == 200:
                    st.success(f"파싱 성공! (소요 시간: {round(time.time() - start_time, 2)}초)")
                    soup = BeautifulSoup(response.text, 'xml')
                    
                    # 4번째 탭(원문 뷰어) 추가
                    tab1, tab2, tab3, tab4 = st.tabs(["📌 메타데이터 & 헤더", "📖 본문 구조", "📚 참고문헌", "👁️ 원문 PDF 하이라이트"])
                    
                    # ----------------------------------------------------
                    # TAB 1: 헤더 및 메타데이터
                    # ----------------------------------------------------
                    with tab1:
                        st.subheader("1. 기본 정보")
                        title_tag = soup.find('titleStmt').find('title') if soup.find('titleStmt') else None
                        title_text = title_tag.text.strip() if title_tag else "제목 없음"
                        st.markdown(f"**논문 제목:** {title_text} {extract_coords(title_tag)}")
                        
                        # 초록
                        abstract_tag = soup.find('abstract')
                        if abstract_tag:
                            st.markdown("**초록 (Abstract):**")
                            st.info(abstract_tag.text.strip())
                            
                        # 키워드
                        keywords_tag = soup.find('keywords')
                        if keywords_tag:
                            terms = [t.text.strip() for t in keywords_tag.find_all('term')]
                            st.markdown(f"**주요 키워드:** `{', '.join(terms)}`")
                            
                        st.divider()
                        st.subheader("2. 저자 및 소속 기관 (정규화)")
                        
                        authors = soup.find_all('author')
                        if authors:
                            for author in authors:
                                pers_name = author.find('persName')
                                if pers_name:
                                    forenames = [f.text for f in pers_name.find_all('forename')]
                                    surname = pers_name.find('surname').text if pers_name.find('surname') else ""
                                    full_name = f"{' '.join(forenames)} {surname}".strip()
                                    
                                    affil = author.find('affiliation')
                                    org_name = affil.find('orgName').text if affil and affil.find('orgName') else "소속 미기재"
                                    
                                    email = author.find('email')
                                    email_str = f" | ✉️ {email.text.strip()}" if email else ""
                                    
                                    st.markdown(f"- **{full_name}** ({org_name}){email_str} {extract_coords(pers_name)}")
                        else:
                            st.write("저자 정보를 찾을 수 없습니다.")

                    # ----------------------------------------------------
                    # TAB 2: 본문 구조화 (저자소개 제외)
                    # ----------------------------------------------------
                    with tab2:
                        st.subheader("본문 파싱 (Sections & Paragraphs)")
                        body = soup.find('text').find('body') if soup.find('text') else None
                        
                        if body:
                            sections = body.find_all('div')
                            for sec in sections:
                                head = sec.find('head')
                                sec_title = head.text.strip() if head else "섹션"
                                
                                # 저자소개(Biography) 관련 섹션 제외
                                sec_title_clean = sec_title.replace(" ", "").lower()
                                if any(bio in sec_title_clean for bio in ["저자소개", "biography", "authorprofile"]):
                                    continue
                                
                                with st.expander(f"📁 {sec_title} {extract_coords(head)}", expanded=False):
                                    paragraphs = sec.find_all('p')
                                    for p in paragraphs:
                                        for ref in p.find_all('ref', type='bibr'):
                                            ref.string = f" **[{ref.text}]** "
                                        st.write(f"{p.text.strip()} {extract_coords(p)}")
                                        
                                    figures = sec.find_all('figure')
                                    for fig in figures:
                                        fig_type = "표 (Table)" if fig.get('type') == "table" else "그림 (Figure)"
                                        fig_head = fig.find('head').text if fig.find('head') else ""
                                        fig_desc = fig.find('figDesc').text if fig.find('figDesc') else ""
                                        st.caption(f"📊 **{fig_type}:** {fig_head} - {fig_desc} {extract_coords(fig)}")
                        else:
                            st.warning("본문 텍스트를 추출할 수 없습니다.")

                    # ----------------------------------------------------
                    # TAB 3: 참고문헌 추출 및 자동 분류
                    # ----------------------------------------------------
                    with tab3:
                        st.subheader("참고문헌 추출 및 자료유형 자동 분류")
                        back = soup.find('back')
                        
                        if back:
                            references = back.find_all('biblStruct')
                            st.write(f"총 **{len(references)}** 건의 참고문헌이 추출되었습니다.")
                            
                            for idx, bibl in enumerate(references, 1):
                                title_tag = bibl.find('title', level='a') or bibl.find('title')
                                ref_title = title_tag.text.strip() if title_tag else "제목 정보 없음"
                                
                                raw_type = bibl.get('type', 'article')
                                doc_type = classify_reference_type(ref_title, raw_type)
                                
                                doi_tag = bibl.find('idno', type='DOI')
                                doi_str = f" | **DOI:** `https://doi.org/{doi_tag.text.strip()}`" if doi_tag else ""
                                
                                ref_authors = [
                                    a.find('persName').text.strip() 
                                    for a in bibl.find_all('author') if a.find('persName')
                                ]
                                author_str = f"저자: {', '.join(ref_authors)}" if ref_authors else "저자 정보 미기재"
                                
                                date_tag = bibl.find('date')
                                year_str = f" ({date_tag.get('when', date_tag.text)})" if date_tag else ""
                                
                                st.markdown(f"**{idx}. [{doc_type}]** {ref_title}{year_str}{doi_str} {extract_coords(bibl)}")
                                st.caption(f"{author_str}")
                                st.markdown("---")
                        else:
                            st.warning("참고문헌 목록을 발견하지 못했습니다.")

                    # ----------------------------------------------------
                    # TAB 4: 원문 PDF 하이라이트 매핑
                    # ----------------------------------------------------
                    with tab4:
                        st.subheader("PDF 원문 위 추출 정보 매핑")
                        if extracted_coords_list:
                            with st.spinner("PDF 원문에 추출된 좌표를 렌더링하고 있습니다..."):
                                try:
                                    # PyMuPDF를 이용해 메모리에 있는 PDF 열기
                                    doc = fitz.open(stream=uploaded_file.getvalue(), filetype="pdf")
                                    
                                    for coords_str in extracted_coords_list:
                                        # 하나의 태그에 여러 좌표 박스가 있을 수 있으므로 세미콜론(;)으로 분리
                                        boxes = coords_str.split(';')
                                        for box in boxes:
                                            parts = box.split(',')
                                            if len(parts) >= 5:
                                                try:
                                                    page_num = int(parts[0]) - 1  # GROBID는 1페이지부터, PyMuPDF는 0페이지부터 시작
                                                    x = float(parts[1])
                                                    y = float(parts[2])
                                                    w = float(parts[3])
                                                    h = float(parts[4])
                                                    
                                                    # 해당 페이지가 존재하는지 확인
                                                    if 0 <= page_num < len(doc):
                                                        page = doc[page_num]
                                                        # (좌상단 x, 좌상단 y, 우하단 x, 우하단 y)
                                                        rect = fitz.Rect(x, y, x + w, y + h)
                                                        
                                                        # 빨간색 테두리
                                                        page.draw_rect(rect, color=(1, 0, 0), width=1.5)
                                                        # 반투명한 노란색 배경으로 하이라이트 효과
                                                        page.draw_rect(rect, color=(1, 1, 0), fill=(1, 1, 0), fill_opacity=0.2)
                                                except ValueError:
                                                    continue
                                    
                                    # 렌더링된 각 페이지를 이미지로 변환하여 출력
                                    for i, page in enumerate(doc):
                                        # 해상도(dpi) 조절 (기본 해상도를 높여 글씨가 깨지지 않게 함)
                                        pix = page.get_pixmap(dpi=150)
                                        img_bytes = pix.tobytes("png")
                                        st.image(img_bytes, caption=f"Page {i+1}", use_container_width=True)
                                        st.divider()
                                        
                                except Exception as e:
                                    st.error(f"PDF 렌더링 중 오류가 발생했습니다: {e}")
                        else:
                            st.info("추출된 좌표 정보가 없습니다.")

                elif response.status_code == 503:
                    st.error("퍼블릭 GROBID 서버가 현재 과부하 상태입니다(503 Service Unavailable). 잠시 후 다시 시도해 주세요.")
                else:
                    st.error(f"서버 응답 오류 (Status Code: {response.status_code})")
                    
            except requests.exceptions.Timeout:
                st.error("요청 시간이 초과되었습니다. 퍼블릭 API 서버 응답이 지연되고 있으니 잠시 후 다시 시도해 주세요.")
            except requests.exceptions.RequestException as e:
                st.error(f"API 연결 에러가 발생했습니다: {e}")
