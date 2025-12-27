import os
import fitz
import traceback
from PyQt6.QtCore import QThread, pyqtSignal

class WorkerThread(QThread):
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)

    def __init__(self, mode, **kwargs):
        super().__init__()
        self.mode = mode
        self.kwargs = kwargs

    def run(self):
        try:
            method = getattr(self, self.mode, None)
            if method:
                method()
            else:
                self.error_signal.emit(f"알 수 없는 작업: {self.mode}")
        except Exception as e:
            traceback.print_exc()
            self.error_signal.emit(str(e))

    def merge(self):
        files = self.kwargs.get('files')
        output_path = self.kwargs.get('output_path')
        doc_merged = fitz.open()
        for idx, path in enumerate(files):
            try:
                doc = fitz.open(path)
                doc_merged.insert_pdf(doc)
                doc.close()
            except Exception as e:
                print(f"Skipping {path}: {e}")
            self.progress_signal.emit(int((idx + 1) / len(files) * 100))
        doc_merged.save(output_path)
        doc_merged.close()
        self.finished_signal.emit(f"✅ 병합 완료!\n{len(files)}개 파일 → 1개 PDF")

    def convert_to_img(self):
        # 다중 파일 지원
        file_paths = self.kwargs.get('file_paths') or [self.kwargs.get('file_path')]
        output_dir = self.kwargs.get('output_dir')
        fmt = self.kwargs.get('fmt', 'png')
        dpi = self.kwargs.get('dpi', 200)
        zoom = dpi / 72
        mat = fitz.Matrix(zoom, zoom)
        
        total_files = len(file_paths)
        total_pages_done = 0
        
        for file_idx, file_path in enumerate(file_paths):
            if not file_path or not os.path.exists(file_path):
                continue
            doc = fitz.open(file_path)
            base = os.path.splitext(os.path.basename(file_path))[0]
            for i, page in enumerate(doc):
                pix = page.get_pixmap(matrix=mat)
                save_path = os.path.join(output_dir, f"{base}_p{i+1:03d}.{fmt}")
                pix.save(save_path)
                total_pages_done += 1
            doc.close()
            self.progress_signal.emit(int((file_idx + 1) / total_files * 100))
        
        self.finished_signal.emit(f"✅ 변환 완료!\n{total_files}개 파일 → {fmt.upper()} 이미지")

    def extract_text(self):
        # 다중 파일 지원
        file_paths = self.kwargs.get('file_paths') or [self.kwargs.get('file_path')]
        output_path = self.kwargs.get('output_path')
        output_dir = self.kwargs.get('output_dir')
        
        total_files = len(file_paths)
        
        for file_idx, file_path in enumerate(file_paths):
            if not file_path or not os.path.exists(file_path):
                continue
            doc = fitz.open(file_path)
            full_text = ""
            for i, page in enumerate(doc):
                full_text += f"\n--- Page {i+1} ---\n"
                full_text += page.get_text()
            doc.close()
            
            # 출력 경로 결정
            if output_dir:
                base = os.path.splitext(os.path.basename(file_path))[0]
                out_path = os.path.join(output_dir, f"{base}.txt")
            else:
                out_path = output_path
            
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(full_text)
            
            self.progress_signal.emit(int((file_idx + 1) / total_files * 100))
        
        self.finished_signal.emit(f"✅ 텍스트 추출 완료!\n{total_files}개 파일")

    def split(self):
        file_path = self.kwargs.get('file_path')
        output_dir = self.kwargs.get('output_dir')
        page_range = self.kwargs.get('page_range')
        doc_src = fitz.open(file_path)
        total_pages = len(doc_src)
        pages_to_keep = []
        parts = page_range.split(',')
        for part in parts:
            part = part.strip()
            if '-' in part:
                s, e = map(int, part.split('-'))
                for p in range(s-1, e):
                    if 0 <= p < total_pages: pages_to_keep.append(p)
            elif part.isdigit():
                p = int(part) - 1
                if 0 <= p < total_pages: pages_to_keep.append(p)
        pages_to_keep = sorted(list(set(pages_to_keep)))
        if not pages_to_keep:
            raise ValueError("유효한 페이지가 없습니다.")
        doc_final = fitz.open()
        for idx, p_num in enumerate(pages_to_keep):
            doc_final.insert_pdf(doc_src, from_page=p_num, to_page=p_num)
            self.progress_signal.emit(int((idx+1)/len(pages_to_keep)*100))
        base = os.path.splitext(os.path.basename(file_path))[0]
        out = os.path.join(output_dir, f"{base}_extracted.pdf")
        doc_final.save(out)
        doc_src.close()
        doc_final.close()
        self.finished_signal.emit(f"✅ 추출 완료!\n{len(pages_to_keep)}페이지 추출됨")

    def delete_pages(self):
        file_path = self.kwargs.get('file_path')
        output_path = self.kwargs.get('output_path')
        page_range = self.kwargs.get('page_range')
        doc = fitz.open(file_path)
        total_pages = len(doc)
        pages_to_delete = []
        parts = page_range.split(',')
        for part in parts:
            part = part.strip()
            if '-' in part:
                s, e = map(int, part.split('-'))
                for p in range(s-1, e):
                    if 0 <= p < total_pages: pages_to_delete.append(p)
            elif part.isdigit():
                p = int(part) - 1
                if 0 <= p < total_pages: pages_to_delete.append(p)
        pages_to_delete = sorted(list(set(pages_to_delete)), reverse=True)
        if not pages_to_delete:
            raise ValueError("삭제할 페이지가 없습니다.")
        for p in pages_to_delete:
            doc.delete_page(p)
        doc.save(output_path)
        doc.close()
        self.progress_signal.emit(100)
        self.finished_signal.emit(f"✅ 삭제 완료!\n{len(pages_to_delete)}페이지 삭제됨")

    def rotate(self):
        file_path = self.kwargs.get('file_path')
        output_path = self.kwargs.get('output_path')
        angle = self.kwargs.get('angle')
        doc = fitz.open(file_path)
        for i, page in enumerate(doc):
            page.set_rotation(page.rotation + angle)
            self.progress_signal.emit(int((i+1)/len(doc) * 100))
        doc.save(output_path)
        doc.close()
        self.finished_signal.emit(f"✅ 회전 완료!\n{angle}° 회전됨")

    def watermark(self):
        file_path = self.kwargs.get('file_path')
        output_path = self.kwargs.get('output_path')
        text = self.kwargs.get('text')
        opacity = self.kwargs.get('opacity', 0.3)
        color = self.kwargs.get('color', (0.5, 0.5, 0.5))
        doc = fitz.open(file_path)
        for i, page in enumerate(doc):
            page.insert_text(
                fitz.Point(page.rect.width/2, page.rect.height/2),
                text, fontsize=40, fontname="helv",
                rotate=45, color=color, fill_opacity=opacity, align=1
            )
            self.progress_signal.emit(int((i+1)/len(doc) * 100))
        doc.save(output_path)
        doc.close()
        self.finished_signal.emit(f"✅ 워터마크 적용 완료!")

    def metadata_update(self):
        file_path = self.kwargs.get('file_path')
        output_path = self.kwargs.get('output_path')
        new_meta = self.kwargs.get('metadata')
        doc = fitz.open(file_path)
        meta = doc.metadata
        for k, v in new_meta.items():
            if v: meta[k] = v
        doc.set_metadata(meta)
        doc.save(output_path)
        doc.close()
        self.progress_signal.emit(100)
        self.finished_signal.emit(f"✅ 메타데이터 저장 완료!")

    def protect(self):
        file_path = self.kwargs.get('file_path')
        output_path = self.kwargs.get('output_path')
        pw = self.kwargs.get('password')
        doc = fitz.open(file_path)
        perm = int(fitz.PDF_PERM_ACCESSIBILITY | fitz.PDF_PERM_PRINT | fitz.PDF_PERM_COPY)
        doc.save(output_path, encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw=pw, user_pw=pw, permissions=perm)
        doc.close()
        self.progress_signal.emit(100)
        self.finished_signal.emit(f"✅ 암호화 완료!")

    def compress(self):
        file_path = self.kwargs.get('file_path')
        output_path = self.kwargs.get('output_path')
        doc = fitz.open(file_path)
        original_size = os.path.getsize(file_path)
        doc.save(output_path, garbage=4, deflate=True)
        doc.close()
        new_size = os.path.getsize(output_path)
        ratio = (1 - new_size / original_size) * 100 if original_size > 0 else 0
        self.progress_signal.emit(100)
        self.finished_signal.emit(f"✅ 압축 완료!\n{original_size//1024}KB → {new_size//1024}KB ({ratio:.1f}% 감소)")

    def images_to_pdf(self):
        files = self.kwargs.get('files')
        output_path = self.kwargs.get('output_path')
        doc = fitz.open()
        for idx, img_path in enumerate(files):
            img = fitz.open(img_path)
            rect = img[0].rect
            pdf_bytes = img.convert_to_pdf()
            img.close()
            img_pdf = fitz.open("pdf", pdf_bytes)
            doc.insert_pdf(img_pdf)
            img_pdf.close()
            self.progress_signal.emit(int((idx + 1) / len(files) * 100))
        doc.save(output_path)
        doc.close()
        self.finished_signal.emit(f"✅ 이미지 → PDF 변환 완료!\n{len(files)}개 이미지 → 1개 PDF")

    def reorder(self):
        """페이지 순서 변경"""
        file_path = self.kwargs.get('file_path')
        output_path = self.kwargs.get('output_path')
        page_order = self.kwargs.get('page_order')
        
        doc_src = fitz.open(file_path)
        doc_out = fitz.open()
        
        for idx, page_num in enumerate(page_order):
            doc_out.insert_pdf(doc_src, from_page=page_num, to_page=page_num)
            self.progress_signal.emit(int((idx + 1) / len(page_order) * 100))
        
        doc_out.save(output_path)
        doc_src.close()
        doc_out.close()
        self.finished_signal.emit(f"✅ 페이지 순서 변경 완료!\n{len(page_order)}페이지 재정렬됨")

    def batch(self):
        """일괄 처리"""
        files = self.kwargs.get('files')
        output_dir = self.kwargs.get('output_dir')
        operation = self.kwargs.get('operation')
        option = self.kwargs.get('option', '')
        
        success_count = 0
        for idx, file_path in enumerate(files):
            try:
                base = os.path.splitext(os.path.basename(file_path))[0]
                out_path = os.path.join(output_dir, f"{base}_processed.pdf")
                
                doc = fitz.open(file_path)
                
                if "압축" in operation:
                    doc.save(out_path, garbage=4, deflate=True)
                elif "워터마크" in operation and option:
                    for page in doc:
                        page.insert_text(fitz.Point(page.rect.width/2, page.rect.height/2),
                            option, fontsize=40, fontname="helv", rotate=45, 
                            color=(0.5, 0.5, 0.5), fill_opacity=0.3, align=1)
                    doc.save(out_path)
                elif "암호화" in operation and option:
                    perm = int(fitz.PDF_PERM_ACCESSIBILITY | fitz.PDF_PERM_PRINT | fitz.PDF_PERM_COPY)
                    doc.save(out_path, encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw=option, user_pw=option, permissions=perm)
                elif "회전" in operation:
                    for page in doc:
                        page.set_rotation(page.rotation + 90)
                    doc.save(out_path)
                else:
                    doc.save(out_path)
                
                doc.close()
                success_count += 1
            except Exception as e:
                print(f"Batch error on {file_path}: {e}")
            
            self.progress_signal.emit(int((idx + 1) / len(files) * 100))
        
        self.finished_signal.emit(f"✅ 일괄 처리 완료!\n{success_count}/{len(files)}개 파일 처리됨")

    def split_by_pages(self):
        """PDF 분할 - 각 페이지를 개별 파일로"""
        file_path = self.kwargs.get('file_path')
        output_dir = self.kwargs.get('output_dir')
        split_mode = self.kwargs.get('split_mode', 'each')
        ranges = self.kwargs.get('ranges', '')
        
        doc = fitz.open(file_path)
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        
        if split_mode == 'each':
            for i in range(len(doc)):
                new_doc = fitz.open()
                new_doc.insert_pdf(doc, from_page=i, to_page=i)
                out_path = os.path.join(output_dir, f"{base_name}_page_{i+1}.pdf")
                new_doc.save(out_path)
                new_doc.close()
                self.progress_signal.emit(int((i + 1) / len(doc) * 100))
            self.finished_signal.emit(f"✅ PDF 분할 완료!\n{len(doc)}개 파일 생성됨")
        else:
            count = 0
            for part_idx, rng in enumerate(ranges.split(',')):
                rng = rng.strip()
                if '-' in rng:
                    start, end = map(int, rng.split('-'))
                else:
                    start = end = int(rng)
                new_doc = fitz.open()
                new_doc.insert_pdf(doc, from_page=start-1, to_page=end-1)
                out_path = os.path.join(output_dir, f"{base_name}_part_{part_idx+1}.pdf")
                new_doc.save(out_path)
                new_doc.close()
                count += 1
            self.finished_signal.emit(f"✅ PDF 분할 완료!\n{count}개 파일 생성됨")
        doc.close()

    def add_page_numbers(self):
        """페이지 번호 삽입"""
        file_path = self.kwargs.get('file_path')
        output_path = self.kwargs.get('output_path')
        position = self.kwargs.get('position', 'bottom')
        format_str = self.kwargs.get('format', '{n} / {total}')
        
        doc = fitz.open(file_path)
        total = len(doc)
        
        for i, page in enumerate(doc):
            text = format_str.replace('{n}', str(i+1)).replace('{total}', str(total))
            rect = page.rect
            if position == 'bottom':
                r = fitz.Rect(0, rect.height - 40, rect.width, rect.height - 10)
            else:
                r = fitz.Rect(0, 10, rect.width, 40)
            
            # align=1 (fitz.TEXT_ALIGN_CENTER)
            page.insert_textbox(r, text, fontsize=10, fontname="helv", color=(0, 0, 0), align=1)
            self.progress_signal.emit(int((i + 1) / total * 100))
        
        doc.save(output_path)
        doc.close()
        self.finished_signal.emit(f"✅ 페이지 번호 삽입 완료!\n{total}페이지")

    def insert_blank_page(self):
        """빈 페이지 삽입"""
        file_path = self.kwargs.get('file_path')
        output_path = self.kwargs.get('output_path')
        position = self.kwargs.get('position', 0)
        
        doc = fitz.open(file_path)
        doc.insert_page(position, width=595, height=842)  # A4 size
        doc.save(output_path)
        doc.close()
        self.progress_signal.emit(100)
        self.finished_signal.emit(f"✅ 빈 페이지 삽입 완료!\n위치: {position + 1}페이지")

    def replace_page(self):
        """특정 페이지 교체"""
        file_path = self.kwargs.get('file_path')
        output_path = self.kwargs.get('output_path')
        replace_path = self.kwargs.get('replace_path')
        target_page = self.kwargs.get('target_page', 1) - 1
        source_page = self.kwargs.get('source_page', 1) - 1
        
        doc = fitz.open(file_path)
        replace_doc = fitz.open(replace_path)
        
        doc.delete_page(target_page)
        doc.insert_pdf(replace_doc, from_page=source_page, to_page=source_page, start_at=target_page)
        
        doc.save(output_path)
        replace_doc.close()
        doc.close()
        self.progress_signal.emit(100)
        self.finished_signal.emit(f"✅ 페이지 교체 완료!")

    def image_watermark(self):
        """이미지 워터마크"""
        file_path = self.kwargs.get('file_path')
        output_path = self.kwargs.get('output_path')
        image_path = self.kwargs.get('image_path')
        position = self.kwargs.get('position', 'center')
        
        doc = fitz.open(file_path)
        
        for i, page in enumerate(doc):
            rect = page.rect
            if position == 'center':
                x, y = (rect.width - 150) / 2, (rect.height - 150) / 2
            elif position == 'top-left':
                x, y = 20, 20
            elif position == 'top-right':
                x, y = rect.width - 170, 20
            elif position == 'bottom-left':
                x, y = 20, rect.height - 170
            else:
                x, y = rect.width - 170, rect.height - 170
            
            img_rect = fitz.Rect(x, y, x + 150, y + 150)
            page.insert_image(img_rect, filename=image_path, overlay=True)
            self.progress_signal.emit(int((i + 1) / len(doc) * 100))
        
        doc.save(output_path)
        doc.close()
        self.finished_signal.emit(f"✅ 이미지 워터마크 완료!")

    def crop_pdf(self):
        """PDF 자르기"""
        file_path = self.kwargs.get('file_path')
        output_path = self.kwargs.get('output_path')
        margins = self.kwargs.get('margins', {'left': 0, 'top': 0, 'right': 0, 'bottom': 0})
        
        doc = fitz.open(file_path)
        
        for i, page in enumerate(doc):
            rect = page.rect
            new_rect = fitz.Rect(
                rect.x0 + margins['left'], rect.y0 + margins['top'],
                rect.x1 - margins['right'], rect.y1 - margins['bottom']
            )
            page.set_cropbox(new_rect)
            self.progress_signal.emit(int((i + 1) / len(doc) * 100))
        
        doc.save(output_path)
        doc.close()
        self.finished_signal.emit(f"✅ PDF 자르기 완료!")

    def add_stamp(self):
        """PDF 스탬프 추가"""
        file_path = self.kwargs.get('file_path')
        output_path = self.kwargs.get('output_path')
        stamp_text = self.kwargs.get('stamp_text', '기밀')
        position = self.kwargs.get('position', 'top-right')
        color = self.kwargs.get('color', (1, 0, 0))  # 빨강
        
        doc = fitz.open(file_path)
        
        for i, page in enumerate(doc):
            rect = page.rect
            if position == 'top-right':
                point = fitz.Point(rect.width - 100, 40)
            elif position == 'top-left':
                point = fitz.Point(30, 40)
            elif position == 'bottom-right':
                point = fitz.Point(rect.width - 100, rect.height - 30)
            else:
                point = fitz.Point(30, rect.height - 30)
            
            # 스탬프 테두리 (좌표 기반 간단 구현)
            stamp_rect = fitz.Rect(point.x - 10, point.y - 20, point.x + 80, point.y + 5)
            page.draw_rect(stamp_rect, color=color, width=2)
            page.insert_text(point, stamp_text, fontsize=14, fontname="helv", color=color)
            self.progress_signal.emit(int((i + 1) / len(doc) * 100))
        
        doc.save(output_path)
        doc.close()
        self.finished_signal.emit(f"✅ 스탬프 추가 완료!")

    def extract_links(self):
        """PDF에서 모든 링크 추출"""
        file_path = self.kwargs.get('file_path')
        output_path = self.kwargs.get('output_path')
        
        doc = fitz.open(file_path)
        all_links = []
        
        for i, page in enumerate(doc):
            links = page.get_links()
            for link in links:
                if 'uri' in link:
                    all_links.append({
                        'page': i + 1,
                        'url': link['uri']
                    })
            self.progress_signal.emit(int((i + 1) / len(doc) * 100))
        
        doc.close()
        
        # 결과 파일로 저장
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"# {os.path.basename(file_path)} - 링크 목록\n\n")
            for link in all_links:
                f.write(f"Page {link['page']}: {link['url']}\n")
        
        self.finished_signal.emit(f"✅ 링크 추출 완료!\n{len(all_links)}개 링크 발견")
    
    def get_form_fields(self):
        """PDF 양식 필드 목록 반환"""
        file_path = self.kwargs.get('file_path')
        
        doc = fitz.open(file_path)
        fields = []
        
        for page_num, page in enumerate(doc):
            widgets = page.widgets()
            if widgets:
                for widget in widgets:
                    fields.append({
                        'page': page_num + 1,
                        'name': widget.field_name or f"field_{len(fields)}",
                        'type': widget.field_type_string,
                        'value': widget.field_value or "",
                        'rect': list(widget.rect)
                    })
        
        doc.close()
        
        # 결과를 kwargs에 저장 (메인 스레드에서 접근)
        self.kwargs['result_fields'] = fields
        self.finished_signal.emit(f"✅ 양식 필드 감지 완료!\n{len(fields)}개 필드 발견")
    
    def fill_form(self):
        """PDF 양식 필드에 값 채우기"""
        file_path = self.kwargs.get('file_path')
        output_path = self.kwargs.get('output_path')
        field_values = self.kwargs.get('field_values', {})
        
        doc = fitz.open(file_path)
        filled_count = 0
        
        for page in doc:
            widgets = page.widgets()
            if widgets:
                for widget in widgets:
                    field_name = widget.field_name
                    if field_name and field_name in field_values:
                        widget.field_value = field_values[field_name]
                        widget.update()
                        filled_count += 1
        
        doc.save(output_path)
        doc.close()
        self.progress_signal.emit(100)
        self.finished_signal.emit(f"✅ 양식 작성 완료!\n{filled_count}개 필드 채움")
    
    def compare_pdfs(self):
        """두 PDF 비교"""
        file_path1 = self.kwargs.get('file_path1')
        file_path2 = self.kwargs.get('file_path2')
        output_path = self.kwargs.get('output_path')
        
        doc1 = fitz.open(file_path1)
        doc2 = fitz.open(file_path2)
        
        results = []
        max_pages = max(len(doc1), len(doc2))
        
        for i in range(max_pages):
            self.progress_signal.emit(int((i + 1) / max_pages * 100))
            
            if i >= len(doc1):
                results.append(f"페이지 {i+1}: 파일1에 없음")
                continue
            if i >= len(doc2):
                results.append(f"페이지 {i+1}: 파일2에 없음")
                continue
            
            text1 = doc1[i].get_text()
            text2 = doc2[i].get_text()
            
            if text1 != text2:
                # 간단한 차이 분석
                lines1 = set(text1.split('\n'))
                lines2 = set(text2.split('\n'))
                only_in_1 = lines1 - lines2
                only_in_2 = lines2 - lines1
                
                if only_in_1 or only_in_2:
                    results.append(f"페이지 {i+1}: 차이 발견")
                    if only_in_1:
                        results.append(f"  - 파일1에만: {len(only_in_1)}줄")
                    if only_in_2:
                        results.append(f"  - 파일2에만: {len(only_in_2)}줄")
        
        doc1.close()
        doc2.close()
        
        # 결과 저장
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# PDF 비교 결과\n\n")
            f.write(f"파일1: {os.path.basename(file_path1)}\n")
            f.write(f"파일2: {os.path.basename(file_path2)}\n\n")
            if results:
                for r in results:
                    f.write(r + "\n")
            else:
                f.write("두 파일의 텍스트 내용이 동일합니다.\n")
        
        diff_count = len([r for r in results if "차이 발견" in r])
        self.finished_signal.emit(f"✅ PDF 비교 완료!\n{diff_count}개 페이지에서 차이 발견")
