"""Position-preserving extraction. Extraction never grants reading-quality approval."""
import hashlib
import json
from pathlib import Path
from xml.etree import ElementTree as ET

def jats_blocks(path):
    data = Path(path).read_bytes()
    # Standard JATS external DTD is not fetched by ElementTree. Reject entities.
    if b'<!ENTITY' in data.upper():
        raise ValueError('Entity declarations disallowed')
    root = ET.fromstring(data)
    body = root.find('body')
    if body is None:
        raise ValueError('Full-text body missing; abstract is not full text')
    blocks = []
    for index, paragraph in enumerate(body.findall('p'), 1):
        blocks.append({'locator': {'kind': 'xml', 'section': 'body', 'section_title': '',
                                   'paragraph': index, 'printed_page': None},
                       'text': ''.join(paragraph.itertext())})
    for section in body.iter('sec'):
        sid = section.get('id')
        title = ''.join(section.find('title').itertext()) if section.find('title') is not None else ''
        if not sid:
            sid = 'section-' + str(len(blocks) + 1)
        for index, paragraph in enumerate(section.findall('p'), 1):
            blocks.append({'locator': {'kind': 'xml', 'section': sid, 'section_title': title,
                                       'paragraph': index, 'printed_page': None},
                           'text': ''.join(paragraph.itertext())})
    if not blocks:
        raise ValueError('No supported body paragraphs extracted')
    supported_paragraphs = len(blocks)
    all_paragraphs = len(list(body.iter('p')))
    return {'format': 'jats', 'source_sha256': hashlib.sha256(data).hexdigest(),
            'parse_status': 'needs_reading_order_review', 'blocks': blocks,
            'unsupported_or_nested_paragraph_count': all_paragraphs - supported_paragraphs,
            'limitations': ['Tables, figures, lists, quotations and non-section nested prose require separate original-source inspection.']}

def confirm_xml_quote(path, locator, quote):
    blocks = jats_blocks(path)['blocks']
    matches = [b for b in blocks if b['locator']['section'] == locator['section']
               and b['locator']['paragraph'] == locator['paragraph']]
    return len(matches) == 1 and quote in matches[0]['text']

def pdf_blocks(path):
    """Optional PyMuPDF; retain boxes/page sequence and make failures visible.

    No automatic OCR here. Blank/garbled pages become explicit OCR requests.
    A reviewer must inspect columns, footnotes, table cells and printed labels.
    """
    try:
        import fitz
    except ImportError:
        return {'parse_status': 'blocked', 'reason': 'pymupdf_not_available', 'pages': []}
    pages = []
    with fitz.open(path) as doc:
        for i, page in enumerate(doc):
            blocks = [{'bbox': list(b[:4]), 'text': b[4], 'block_id': f'p{i+1}-b{n}'}
                      for n, b in enumerate(page.get_text('blocks')) if b[6] == 0]
            text = ''.join(b['text'] for b in blocks)
            requests = []
            if len(text.strip()) < 20 or '\ufffd' in text:
                requests.append({'bbox': list(page.rect), 'reason': 'missing_or_replacement_text'})
            else:
                # Header/footer text must not conceal an image-only body. Significant
                # raster regions are inspected independently even when the page has text.
                for image in page.get_image_info():
                    box = fitz.Rect(image['bbox']) & page.rect
                    if box.is_empty or box.get_area() / page.rect.get_area() < .05:
                        continue
                    covered = sum((box & fitz.Rect(b['bbox'])).get_area() for b in blocks
                                  if not (box & fitz.Rect(b['bbox'])).is_empty)
                    if covered / box.get_area() < .05:
                        requests.append({'bbox': list(box), 'reason': 'raster_region_without_text',
                                         'note': 'May be figure/table; OCR output still requires original-image review.'})
            midpoint = page.rect.width / 2
            left = [b for b in blocks if b['bbox'][2] <= midpoint + 5]
            left_ids = {b['block_id'] for b in left}
            right = [b for b in blocks if b['bbox'][0] >= midpoint - 5 and b['block_id'] not in left_ids]
            column_candidate = len(left) >= 3 and len(right) >= 3
            # Keep native order and expose proposed order; the reviewer must resolve
            # spanning headings, tables and footnotes before using any prose sequence.
            proposal = None
            order_blockers = []
            if column_candidate:
                ids = {b['block_id'] for b in left + right}
                spanning = [b for b in blocks if b['block_id'] not in ids]
                top = min(b['bbox'][1] for b in left + right)
                header = [b for b in spanning if b['bbox'][3] <= top]
                remainder = [b for b in spanning if b not in header]
                bottom = max(b['bbox'][3] for b in left + right)
                if any(b['bbox'][1] < bottom for b in remainder):
                    order_blockers.append('spanning_body_blocks_require_manual_order')
                else:
                    proposal = [b['block_id'] for group in (header, left, right, remainder)
                                for b in sorted(group, key=lambda b: (b['bbox'][1], b['bbox'][0]))]
            pages.append({'pdf_page': i + 1, 'printed_page': None,
                          'page_bbox': list(page.rect),
                          'status': 'ocr_required' if requests else 'needs_visual_review',
                          'blocks': blocks, 'ocr_regions': requests,
                          'two_column_candidate': column_candidate,
                          'layout_status': 'unknown_no_native_text' if not text.strip() else ('two_column_candidate' if column_candidate else 'unclassified'),
                          'proposed_block_order': proposal,
                          'reading_order_blockers': order_blockers,
                          'reading_order_verified': False,
                          'limitations': ['Column order, headers, footnotes, table cells and printed page labels require visual review.']})
    return {'parse_status': 'needs_review', 'source_sha256': hashlib.sha256(Path(path).read_bytes()).hexdigest(),
            'pages': pages, 'ocr': 'not_executed'}
