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
        fontsize = self.kwargs.get('fontsize', 40)
        rotation = self.kwargs.get('rotation', 45)
        fontname = self.kwargs.get('fontname', 'helv')  # helv, tiro, cobo, symb
        position = self.kwargs.get('position', 'center')  # center, tile
        
        doc = fitz.open(file_path)
        for i, page in enumerate(doc):
            if position == 'tile':
                # 타일 패턴으로 반복
                for y in range(0, int(page.rect.height), 200):
                    for x in range(0, int(page.rect.width), 300):
                        page.insert_text(
                            fitz.Point(x, y), text, fontsize=fontsize,
                            fontname=fontname, rotate=rotation,
                            color=color, fill_opacity=opacity
                        )
            else:
                page.insert_text(
                    fitz.Point(page.rect.width/2, page.rect.height/2),
                    text, fontsize=fontsize, fontname=fontname,
                    rotate=rotation, color=color, fill_opacity=opacity, align=1
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
        quality = self.kwargs.get('quality', 'high')  # low, medium, high
        
        # 품질별 설정
        settings = {
            'low': {'garbage': 4, 'deflate': True, 'deflate_images': True, 'deflate_fonts': True, 'clean': True},
            'medium': {'garbage': 3, 'deflate': True, 'deflate_images': True},
            'high': {'garbage': 2, 'deflate': True},
        }
        
        doc = fitz.open(file_path)
        original_size = os.path.getsize(file_path)
        doc.save(output_path, **settings.get(quality, settings['high']))
        doc.close()
        new_size = os.path.getsize(output_path)
        ratio = (1 - new_size / original_size) * 100 if original_size > 0 else 0
        self.progress_signal.emit(100)
        quality_name = {'low': '최대 압축', 'medium': '중간', 'high': '고품질'}.get(quality, '고품질')
        self.finished_signal.emit(f"✅ 압축 완료! ({quality_name})\n{original_size//1024}KB → {new_size//1024}KB ({ratio:.1f}% 감소)")

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
        position = self.kwargs.get('position', 'bottom')  # bottom, top, bottom-left, bottom-right, top-left, top-right
        format_str = self.kwargs.get('format', '{n} / {total}')
        fontsize = self.kwargs.get('fontsize', 10)
        fontname = self.kwargs.get('fontname', 'helv')
        color = self.kwargs.get('color', (0, 0, 0))
        margin = self.kwargs.get('margin', 30)
        start_number = self.kwargs.get('start_number', 1)  # 시작 번호
        skip_first = self.kwargs.get('skip_first', False)  # 첫 페이지 건너뛰기
        
        doc = fitz.open(file_path)
        total = len(doc)
        
        for i, page in enumerate(doc):
            if skip_first and i == 0:
                continue
                
            page_num = start_number + i if not skip_first else start_number + i - 1
            text = format_str.replace('{n}', str(page_num)).replace('{total}', str(total))
            rect = page.rect
            
            # 위치별 텍스트박스 영역 설정
            if position == 'bottom' or position == 'bottom-center':
                r = fitz.Rect(0, rect.height - margin - 20, rect.width, rect.height - margin)
                align = 1  # center
            elif position == 'top' or position == 'top-center':
                r = fitz.Rect(0, margin, rect.width, margin + 20)
                align = 1
            elif position == 'bottom-left':
                r = fitz.Rect(margin, rect.height - margin - 20, 150, rect.height - margin)
                align = 0  # left
            elif position == 'bottom-right':
                r = fitz.Rect(rect.width - 150, rect.height - margin - 20, rect.width - margin, rect.height - margin)
                align = 2  # right
            elif position == 'top-left':
                r = fitz.Rect(margin, margin, 150, margin + 20)
                align = 0
            elif position == 'top-right':
                r = fitz.Rect(rect.width - 150, margin, rect.width - margin, margin + 20)
                align = 2
            else:
                r = fitz.Rect(0, rect.height - margin - 20, rect.width, rect.height - margin)
                align = 1
            
            page.insert_textbox(r, text, fontsize=fontsize, fontname=fontname, color=color, align=align)
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

    # ===================== v2.8 신규 기능 =====================
    
    def get_pdf_info(self):
        """PDF 정보 및 통계 추출"""
        file_path = self.kwargs.get('file_path')
        output_path = self.kwargs.get('output_path')
        
        doc = fitz.open(file_path)
        
        # 기본 정보
        total_chars = 0
        total_images = 0
        fonts_used = set()
        
        for i, page in enumerate(doc):
            # 텍스트 통계
            text = page.get_text()
            total_chars += len(text)
            
            # 이미지 수
            images = page.get_images()
            total_images += len(images)
            
            # 폰트 목록
            for font in page.get_fonts():
                fonts_used.add(font[3] if len(font) > 3 else font[0])
            
            self.progress_signal.emit(int((i + 1) / len(doc) * 100))
        
        # 결과 저장
        meta = doc.metadata
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"# PDF 정보: {os.path.basename(file_path)}\n\n")
            f.write(f"## 기본 정보\n")
            f.write(f"- 페이지 수: {len(doc)}\n")
            f.write(f"- 파일 크기: {os.path.getsize(file_path) / 1024:.1f} KB\n")
            f.write(f"- 제목: {meta.get('title', '-')}\n")
            f.write(f"- 작성자: {meta.get('author', '-')}\n")
            f.write(f"- 생성일: {meta.get('creationDate', '-')}\n\n")
            f.write(f"## 통계\n")
            f.write(f"- 총 글자 수: {total_chars:,}\n")
            f.write(f"- 총 이미지 수: {total_images}\n")
            f.write(f"- 사용 폰트: {', '.join(fonts_used) if fonts_used else '없음'}\n")
        
        doc.close()
        self.finished_signal.emit(f"✅ PDF 정보 추출 완료!\n{len(doc)}페이지, {total_chars:,}자, {total_images}개 이미지")
    
    def duplicate_page(self):
        """페이지 복제"""
        file_path = self.kwargs.get('file_path')
        output_path = self.kwargs.get('output_path')
        page_num = self.kwargs.get('page_num', 0)  # 0-indexed
        count = self.kwargs.get('count', 1)
        
        doc = fitz.open(file_path)
        
        for i in range(count):
            doc.fullcopy_page(page_num, page_num + 1 + i)
            self.progress_signal.emit(int((i + 1) / count * 100))
        
        doc.save(output_path)
        doc.close()
        self.finished_signal.emit(f"✅ 페이지 복제 완료!\n{page_num + 1}페이지를 {count}번 복제")
    
    def reverse_pages(self):
        """페이지 역순 정렬"""
        file_path = self.kwargs.get('file_path')
        output_path = self.kwargs.get('output_path')
        
        doc = fitz.open(file_path)
        page_count = len(doc)
        
        # 역순으로 페이지 이동
        for i in range(page_count - 1):
            doc.move_page(page_count - 1, i)
            self.progress_signal.emit(int((i + 1) / (page_count - 1) * 100))
        
        doc.save(output_path)
        doc.close()
        self.finished_signal.emit(f"✅ 역순 정렬 완료!\n{page_count}페이지")
    
    def resize_pages(self):
        """페이지 크기 변경"""
        file_path = self.kwargs.get('file_path')
        output_path = self.kwargs.get('output_path')
        target_size = self.kwargs.get('target_size', 'A4')
        
        # 표준 크기 (포인트)
        sizes = {
            'A4': (595, 842),
            'A3': (842, 1191),
            'Letter': (612, 792),
            'Legal': (612, 1008),
        }
        
        target_w, target_h = sizes.get(target_size, (595, 842))
        
        doc = fitz.open(file_path)
        
        for i, page in enumerate(doc):
            # 새 크기로 페이지 설정
            page.set_mediabox(fitz.Rect(0, 0, target_w, target_h))
            self.progress_signal.emit(int((i + 1) / len(doc) * 100))
        
        doc.save(output_path)
        doc.close()
        self.finished_signal.emit(f"✅ 페이지 크기 변경 완료!\n{len(doc)}페이지 → {target_size}")
    
    def extract_images(self):
        """PDF에서 모든 이미지 추출"""
        file_path = self.kwargs.get('file_path')
        output_dir = self.kwargs.get('output_dir')
        
        doc = fitz.open(file_path)
        image_count = 0
        
        for page_num, page in enumerate(doc):
            images = page.get_images()
            for img_idx, img in enumerate(images):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]
                
                image_path = os.path.join(output_dir, f"page{page_num + 1}_img{img_idx + 1}.{image_ext}")
                with open(image_path, "wb") as f:
                    f.write(image_bytes)
                image_count += 1
            
            self.progress_signal.emit(int((page_num + 1) / len(doc) * 100))
        
        doc.close()
        self.finished_signal.emit(f"✅ 이미지 추출 완료!\n{image_count}개 이미지 저장됨")
    
    def insert_signature(self):
        """전자 서명 이미지 삽입"""
        file_path = self.kwargs.get('file_path')
        output_path = self.kwargs.get('output_path')
        signature_path = self.kwargs.get('signature_path')
        page_num = self.kwargs.get('page_num', -1)  # -1 = 마지막 페이지
        position = self.kwargs.get('position', 'bottom_right')
        
        doc = fitz.open(file_path)
        
        if page_num == -1:
            page_num = len(doc) - 1
        
        page = doc[page_num]
        page_rect = page.rect
        
        # 서명 이미지 크기 (가로 150pt)
        sig_width = 150
        sig_height = 50
        
        # 위치 계산
        positions = {
            'bottom_right': fitz.Rect(page_rect.width - sig_width - 50, page_rect.height - sig_height - 50,
                                      page_rect.width - 50, page_rect.height - 50),
            'bottom_left': fitz.Rect(50, page_rect.height - sig_height - 50,
                                     50 + sig_width, page_rect.height - 50),
            'top_right': fitz.Rect(page_rect.width - sig_width - 50, 50,
                                   page_rect.width - 50, 50 + sig_height),
            'top_left': fitz.Rect(50, 50, 50 + sig_width, 50 + sig_height),
        }
        
        rect = positions.get(position, positions['bottom_right'])
        
        # 서명 이미지 삽입
        page.insert_image(rect, filename=signature_path)
        self.progress_signal.emit(100)
        
        doc.save(output_path)
        doc.close()
        self.finished_signal.emit(f"✅ 전자 서명 삽입 완료!\n{page_num + 1}페이지 {position}")

    # ===================== v2.9 신규 기능 =====================
    
    def get_bookmarks(self):
        """PDF 북마크(목차) 추출"""
        file_path = self.kwargs.get('file_path')
        output_path = self.kwargs.get('output_path')
        
        doc = fitz.open(file_path)
        toc = doc.get_toc()  # [[level, title, page], ...]
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"# 북마크: {os.path.basename(file_path)}\n\n")
            if toc:
                for item in toc:
                    level, title, page = item[0], item[1], item[2]
                    indent = "  " * (level - 1)
                    f.write(f"{indent}- [{title}] → 페이지 {page}\n")
            else:
                f.write("북마크가 없습니다.\n")
        
        doc.close()
        self.progress_signal.emit(100)
        self.finished_signal.emit(f"✅ 북마크 추출 완료!\n{len(toc)}개 항목")
    
    def set_bookmarks(self):
        """PDF 북마크(목차) 설정"""
        file_path = self.kwargs.get('file_path')
        output_path = self.kwargs.get('output_path')
        bookmarks = self.kwargs.get('bookmarks', [])  # [[level, title, page], ...]
        
        doc = fitz.open(file_path)
        doc.set_toc(bookmarks)
        doc.save(output_path)
        doc.close()
        
        self.progress_signal.emit(100)
        self.finished_signal.emit(f"✅ 북마크 설정 완료!\n{len(bookmarks)}개 항목")
    
    def search_text(self):
        """PDF 내 텍스트 검색"""
        file_path = self.kwargs.get('file_path')
        search_term = self.kwargs.get('search_term', '')
        output_path = self.kwargs.get('output_path')
        
        doc = fitz.open(file_path)
        results = []
        
        for page_num, page in enumerate(doc):
            text_instances = page.search_for(search_term)
            if text_instances:
                results.append({
                    'page': page_num + 1,
                    'count': len(text_instances),
                    'positions': [(r.x0, r.y0) for r in text_instances[:5]]  # 최대 5개 위치
                })
            self.progress_signal.emit(int((page_num + 1) / len(doc) * 100))
        
        # 결과 저장
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"# 검색 결과: '{search_term}'\n")
            f.write(f"파일: {os.path.basename(file_path)}\n\n")
            if results:
                total = sum(r['count'] for r in results)
                f.write(f"총 {total}개 발견 ({len(results)}페이지)\n\n")
                for r in results:
                    f.write(f"## 페이지 {r['page']}: {r['count']}개\n")
            else:
                f.write("검색 결과가 없습니다.\n")
        
        doc.close()
        total_found = sum(r['count'] for r in results) if results else 0
        self.finished_signal.emit(f"✅ 검색 완료!\n'{search_term}': {total_found}개 발견")
    
    def highlight_text(self):
        """PDF 내 텍스트 하이라이트"""
        file_path = self.kwargs.get('file_path')
        search_term = self.kwargs.get('search_term', '')
        output_path = self.kwargs.get('output_path')
        color = self.kwargs.get('color', (1, 1, 0))  # 기본 노란색
        
        doc = fitz.open(file_path)
        highlight_count = 0
        
        for page_num, page in enumerate(doc):
            text_instances = page.search_for(search_term)
            for inst in text_instances:
                highlight = page.add_highlight_annot(inst)
                highlight.set_colors(stroke=color)
                highlight.update()
                highlight_count += 1
            self.progress_signal.emit(int((page_num + 1) / len(doc) * 100))
        
        doc.save(output_path)
        doc.close()
        self.finished_signal.emit(f"✅ 하이라이트 완료!\n'{search_term}': {highlight_count}개 표시")

    # ===================== v3.0 신규 기능 =====================
    
    def extract_tables(self):
        """PDF에서 테이블 데이터 추출"""
        import csv
        file_path = self.kwargs.get('file_path')
        output_path = self.kwargs.get('output_path')
        
        doc = fitz.open(file_path)
        all_tables = []
        
        for page_num, page in enumerate(doc):
            try:
                tables = page.find_tables()
                for idx, table in enumerate(tables):
                    table_data = table.extract()
                    all_tables.append({
                        'page': page_num + 1,
                        'table_idx': idx + 1,
                        'data': table_data
                    })
            except Exception as e:
                print(f"Page {page_num + 1} table extraction error: {e}")
            self.progress_signal.emit(int((page_num + 1) / len(doc) * 100))
        
        # CSV로 저장
        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            for table in all_tables:
                writer.writerow([f"--- Page {table['page']}, Table {table['table_idx']} ---"])
                for row in table['data']:
                    cleaned_row = [str(cell) if cell else '' for cell in row]
                    writer.writerow(cleaned_row)
                writer.writerow([])
        
        doc.close()
        self.finished_signal.emit(f"✅ 테이블 추출 완료!\n{len(all_tables)}개 테이블 발견")
    
    def decrypt_pdf(self):
        """암호화된 PDF 복호화"""
        file_path = self.kwargs.get('file_path')
        output_path = self.kwargs.get('output_path')
        password = self.kwargs.get('password', '')
        
        doc = fitz.open(file_path)
        if doc.is_encrypted:
            if not doc.authenticate(password):
                doc.close()
                raise ValueError("비밀번호가 올바르지 않습니다.")
        
        # 암호 없이 저장
        doc.save(output_path)
        doc.close()
        self.progress_signal.emit(100)
        self.finished_signal.emit("✅ PDF 복호화 완료!")
    
    def list_annotations(self):
        """PDF 주석 목록 추출"""
        file_path = self.kwargs.get('file_path')
        output_path = self.kwargs.get('output_path')
        
        doc = fitz.open(file_path)
        all_annots = []
        
        for page_num, page in enumerate(doc):
            annots = page.annots()
            if annots:
                for annot in annots:
                    annot_info = annot.info
                    all_annots.append({
                        'page': page_num + 1,
                        'type': annot.type[1] if annot.type else 'Unknown',
                        'content': annot_info.get('content', '') if annot_info else '',
                        'title': annot_info.get('title', '') if annot_info else '',
                        'rect': list(annot.rect)
                    })
            self.progress_signal.emit(int((page_num + 1) / len(doc) * 100))
        
        # 결과 저장
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"# 주석 목록: {os.path.basename(file_path)}\n\n")
            f.write(f"총 {len(all_annots)}개 주석\n\n")
            for annot in all_annots:
                f.write(f"## 페이지 {annot['page']} - {annot['type']}\n")
                if annot['title']:
                    f.write(f"작성자: {annot['title']}\n")
                if annot['content']:
                    f.write(f"내용: {annot['content']}\n")
                f.write("\n")
        
        doc.close()
        self.kwargs['result_annotations'] = all_annots
        self.finished_signal.emit(f"✅ 주석 추출 완료!\n{len(all_annots)}개 주석 발견")
    
    def add_annotation(self):
        """PDF에 주석 추가"""
        file_path = self.kwargs.get('file_path')
        output_path = self.kwargs.get('output_path')
        page_num = self.kwargs.get('page_num', 0)
        annot_type = self.kwargs.get('annot_type', 'text')  # text, sticky, freetext
        text = self.kwargs.get('text', '')
        point = self.kwargs.get('point', [100, 100])  # [x, y]
        rect = self.kwargs.get('rect', [100, 100, 300, 150])  # [x0, y0, x1, y1]
        
        doc = fitz.open(file_path)
        page = doc[page_num]
        
        if annot_type == 'text' or annot_type == 'sticky':
            annot = page.add_text_annot(fitz.Point(point[0], point[1]), text)
        elif annot_type == 'freetext':
            annot = page.add_freetext_annot(fitz.Rect(rect), text, fontsize=12)
        
        if annot:
            annot.update()
        
        doc.save(output_path)
        doc.close()
        self.progress_signal.emit(100)
        self.finished_signal.emit(f"✅ 주석 추가 완료!\n페이지 {page_num + 1}")
    
    def remove_annotations(self):
        """PDF에서 모든 주석 제거"""
        file_path = self.kwargs.get('file_path')
        output_path = self.kwargs.get('output_path')
        
        doc = fitz.open(file_path)
        count = 0
        
        for page in doc:
            annot = page.first_annot
            while annot:
                next_annot = annot.next
                page.delete_annot(annot)
                count += 1
                annot = next_annot
        
        doc.save(output_path)
        doc.close()
        self.progress_signal.emit(100)
        self.finished_signal.emit(f"✅ {count}개 주석 삭제 완료!")
    
    def draw_shapes(self):
        """PDF에 도형 그리기"""
        file_path = self.kwargs.get('file_path')
        output_path = self.kwargs.get('output_path')
        page_num = self.kwargs.get('page_num', 0)
        shapes = self.kwargs.get('shapes', [])  # [{type, params, color, width}]
        
        doc = fitz.open(file_path)
        page = doc[page_num]
        
        for shape_info in shapes:
            shape_type = shape_info.get('type', 'line')
            color = tuple(shape_info.get('color', [1, 0, 0]))
            width = shape_info.get('width', 1)
            fill = shape_info.get('fill')
            
            if shape_type == 'line':
                p1 = fitz.Point(shape_info['p1'][0], shape_info['p1'][1])
                p2 = fitz.Point(shape_info['p2'][0], shape_info['p2'][1])
                page.draw_line(p1, p2, color=color, width=width)
            elif shape_type == 'rect':
                rect = fitz.Rect(shape_info['rect'])
                page.draw_rect(rect, color=color, width=width, fill=fill)
            elif shape_type == 'circle':
                center = fitz.Point(shape_info['center'][0], shape_info['center'][1])
                radius = shape_info.get('radius', 50)
                page.draw_circle(center, radius, color=color, width=width, fill=fill)
            elif shape_type == 'oval':
                rect = fitz.Rect(shape_info['rect'])
                page.draw_oval(rect, color=color, width=width, fill=fill)
        
        doc.save(output_path)
        doc.close()
        self.progress_signal.emit(100)
        self.finished_signal.emit(f"✅ {len(shapes)}개 도형 추가 완료!")
    
    def add_link(self):
        """PDF에 하이퍼링크 추가"""
        file_path = self.kwargs.get('file_path')
        output_path = self.kwargs.get('output_path')
        page_num = self.kwargs.get('page_num', 0)
        link_type = self.kwargs.get('link_type', 'uri')  # uri, goto
        rect = self.kwargs.get('rect', [100, 100, 200, 120])  # [x0, y0, x1, y1]
        target = self.kwargs.get('target')  # URL 또는 페이지 번호
        
        doc = fitz.open(file_path)
        page = doc[page_num]
        
        link = {
            'kind': fitz.LINK_URI if link_type == 'uri' else fitz.LINK_GOTO,
            'from': fitz.Rect(rect),
        }
        
        if link_type == 'uri':
            link['uri'] = target
        else:
            link['page'] = int(target) - 1  # 0-indexed
            link['to'] = fitz.Point(0, 0)
        
        page.insert_link(link)
        doc.save(output_path)
        doc.close()
        self.progress_signal.emit(100)
        self.finished_signal.emit(f"✅ 링크 추가 완료!\n페이지 {page_num + 1}")
    
    def list_attachments(self):
        """PDF 첨부 파일 목록"""
        file_path = self.kwargs.get('file_path')
        
        doc = fitz.open(file_path)
        attachments = []
        
        count = doc.embfile_count()
        for i in range(count):
            info = doc.embfile_info(i)
            attachments.append({
                'index': i,
                'name': info.get('name', 'Unknown'),
                'size': info.get('size', 0),
                'created': info.get('creationDate', ''),
            })
        
        doc.close()
        self.kwargs['result_attachments'] = attachments
        self.progress_signal.emit(100)
        self.finished_signal.emit(f"✅ 첨부 파일 목록!\n{len(attachments)}개 발견")
    
    def add_attachment(self):
        """PDF에 파일 첨부"""
        file_path = self.kwargs.get('file_path')
        output_path = self.kwargs.get('output_path')
        attach_path = self.kwargs.get('attach_path')
        
        doc = fitz.open(file_path)
        
        with open(attach_path, 'rb') as f:
            data = f.read()
        
        doc.embfile_add(os.path.basename(attach_path), data)
        doc.save(output_path)
        doc.close()
        self.progress_signal.emit(100)
        self.finished_signal.emit(f"✅ 파일 첨부 완료!\n{os.path.basename(attach_path)}")
    
    def extract_attachments(self):
        """PDF 첨부 파일 추출"""
        file_path = self.kwargs.get('file_path')
        output_dir = self.kwargs.get('output_dir')
        
        doc = fitz.open(file_path)
        count = 0
        
        for i in range(doc.embfile_count()):
            info = doc.embfile_info(i)
            data = doc.embfile_get(i)
            
            out_path = os.path.join(output_dir, info.get('name', f'attachment_{i}'))
            with open(out_path, 'wb') as f:
                f.write(data)
            count += 1
            self.progress_signal.emit(int((i + 1) / doc.embfile_count() * 100) if doc.embfile_count() > 0 else 100)
        
        doc.close()
        self.finished_signal.emit(f"✅ {count}개 첨부 파일 추출 완료!")
    
    def redact_text(self):
        """PDF에서 텍스트 영구 삭제 (교정)"""
        file_path = self.kwargs.get('file_path')
        output_path = self.kwargs.get('output_path')
        search_term = self.kwargs.get('search_term', '')
        fill_color = self.kwargs.get('fill_color', (0, 0, 0))  # 검정색 기본
        
        doc = fitz.open(file_path)
        redact_count = 0
        
        for page_num, page in enumerate(doc):
            text_instances = page.search_for(search_term)
            for inst in text_instances:
                page.add_redact_annot(inst, fill=fill_color)
                redact_count += 1
            page.apply_redactions()
            self.progress_signal.emit(int((page_num + 1) / len(doc) * 100))
        
        doc.save(output_path)
        doc.close()
        self.finished_signal.emit(f"✅ {redact_count}개 영역 교정 완료!")
    
    def extract_markdown(self):
        """PDF를 Markdown으로 추출"""
        file_path = self.kwargs.get('file_path')
        output_path = self.kwargs.get('output_path')
        
        doc = fitz.open(file_path)
        markdown_text = f"# {os.path.basename(file_path)}\n\n"
        
        for page_num, page in enumerate(doc):
            text = page.get_text("text")
            markdown_text += f"\n---\n\n## Page {page_num + 1}\n\n"
            # 기본 텍스트 변환 (단순 줄바꿈 정리)
            lines = text.split('\n')
            for line in lines:
                line = line.strip()
                if line:
                    markdown_text += line + "\n\n"
            self.progress_signal.emit(int((page_num + 1) / len(doc) * 100))
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown_text)
        
        doc.close()
        self.finished_signal.emit(f"✅ Markdown 추출 완료!\n{len(doc)}페이지")
    
    def copy_page_between_docs(self):
        """다른 PDF에서 페이지 복사"""
        source_path = self.kwargs.get('source_path')
        target_path = self.kwargs.get('target_path')
        output_path = self.kwargs.get('output_path')
        source_pages = self.kwargs.get('source_pages', [0])  # 복사할 페이지 번호들 (0-indexed)
        insert_at = self.kwargs.get('insert_at', -1)  # 삽입 위치 (-1 = 끝)
        
        source_doc = fitz.open(source_path)
        target_doc = fitz.open(target_path)
        
        insert_pos = insert_at if insert_at >= 0 else len(target_doc)
        
        for i, page_num in enumerate(source_pages):
            if 0 <= page_num < len(source_doc):
                target_doc.insert_pdf(source_doc, from_page=page_num, to_page=page_num, start_at=insert_pos + i)
            self.progress_signal.emit(int((i + 1) / len(source_pages) * 100))
        
        target_doc.save(output_path)
        source_doc.close()
        target_doc.close()
        self.finished_signal.emit(f"✅ {len(source_pages)}페이지 복사 완료!")
    
    def add_background(self):
        """PDF 페이지에 배경색 추가"""
        file_path = self.kwargs.get('file_path')
        output_path = self.kwargs.get('output_path')
        color = tuple(self.kwargs.get('color', [1, 1, 0.9]))  # 연한 노란색 기본
        
        doc = fitz.open(file_path)
        
        for page_num, page in enumerate(doc):
            rect = page.rect
            shape = page.new_shape()
            shape.draw_rect(rect)
            shape.finish(color=color, fill=color)
            shape.commit(overlay=False)  # 배경으로 삽입
            self.progress_signal.emit(int((page_num + 1) / len(doc) * 100))
        
        doc.save(output_path)
        doc.close()
        self.finished_signal.emit(f"✅ 배경색 추가 완료!\n{len(doc)}페이지")
    
    def add_text_markup(self):
        """검색어에 밑줄 또는 취소선 추가"""
        file_path = self.kwargs.get('file_path')
        output_path = self.kwargs.get('output_path')
        search_term = self.kwargs.get('search_term', '')
        markup_type = self.kwargs.get('markup_type', 'underline')  # underline, strikeout, squiggly
        
        doc = fitz.open(file_path)
        count = 0
        
        for page_num, page in enumerate(doc):
            instances = page.search_for(search_term)
            for inst in instances:
                if markup_type == 'underline':
                    annot = page.add_underline_annot(inst)
                elif markup_type == 'strikeout':
                    annot = page.add_strikeout_annot(inst)
                elif markup_type == 'squiggly':
                    annot = page.add_squiggly_annot(inst)
                if annot:
                    annot.update()
                count += 1
            self.progress_signal.emit(int((page_num + 1) / len(doc) * 100))
        
        doc.save(output_path)
        doc.close()
        markup_name = {'underline': '밑줄', 'strikeout': '취소선', 'squiggly': '물결선'}.get(markup_type, markup_type)
        self.finished_signal.emit(f"✅ {markup_name} 추가 완료!\n'{search_term}': {count}개")
    
    def insert_textbox(self):
        """PDF에 텍스트 상자 삽입"""
        file_path = self.kwargs.get('file_path')
        output_path = self.kwargs.get('output_path')
        page_num = self.kwargs.get('page_num', 0)
        rect = self.kwargs.get('rect', [100, 100, 300, 150])  # [x0, y0, x1, y1]
        text = self.kwargs.get('text', '')
        fontsize = self.kwargs.get('fontsize', 12)
        color = tuple(self.kwargs.get('color', [0, 0, 0]))
        align = self.kwargs.get('align', 0)  # 0=left, 1=center, 2=right
        
        doc = fitz.open(file_path)
        page = doc[page_num]
        
        page.insert_textbox(fitz.Rect(rect), text, fontsize=fontsize, 
                           fontname="helv", color=color, align=align)
        
        doc.save(output_path)
        doc.close()
        self.progress_signal.emit(100)
        self.finished_signal.emit(f"✅ 텍스트 상자 삽입 완료!\n페이지 {page_num + 1}")
