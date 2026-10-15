"""Bind a PDF quotation to actual page pixels and an explicit independent review.

These checks do not decide meaning. A reviewer must actually view the crop and
surrounding page; a self-declared review is an audit record, not authentication.
"""
import hashlib
import json
import math
from pathlib import Path
import re


def sha(data):
    return hashlib.sha256(data).hexdigest()


def binding(evidence):
    fields = {k:v for k,v in evidence.items() if k not in ('hash', 'pdf_review')}
    return sha(json.dumps(fields, ensure_ascii=False, sort_keys=True,
                          separators=(',', ':')).encode('utf-8'))


def checked_box(values, page_rect):
    if (not isinstance(values, list) or len(values) != 4
            or any(type(v) not in (int, float) or not math.isfinite(v) for v in values)):
        raise ValueError('PDF finite bbox required')
    x0,y0,x1,y1=values
    if not (page_rect.x0 <= x0 < x1 <= page_rect.x1 and page_rect.y0 <= y0 < y1 <= page_rect.y1):
        raise ValueError('PDF bbox outside page or empty')
    return values


def page_and_boxes(doc, locator):
    number=locator.get('pdf_page')
    if type(number) is not int or not 1 <= number <= len(doc):
        raise ValueError('PDF sequence page outside actual document')
    page=doc[number-1]
    box=checked_box(locator.get('bbox'), page.rect)
    context=checked_box(locator.get('context_bbox', box), page.rect)
    if not (context[0] <= box[0] and context[1] <= box[1]
            and context[2] >= box[2] and context[3] >= box[3]):
        raise ValueError('PDF context bbox must contain quote bbox')
    return page, box, context


def render_proof(source, locator, destination, dpi=150):
    """Produce review input only: no verdict or reviewed status is generated."""
    import fitz
    if type(dpi) is not int or not 100 <= dpi <= 300:
        raise ValueError('PDF proof dpi must be integer 100..300')
    with fitz.open(source) as doc:
        if not doc.is_pdf or doc.needs_pass:
            raise ValueError('Readable original PDF required')
        page, _, context=page_and_boxes(doc, locator)
        pix=page.get_pixmap(dpi=dpi, clip=fitz.Rect(context), alpha=False, annots=False)
        Path(destination).parent.mkdir(parents=True, exist_ok=True)
        pix.save(destination)
    return {'source_sha256':sha(Path(source).read_bytes()), 'dpi':dpi,
            'crop_sha256':sha(Path(destination).read_bytes()), 'pixel_sha256':sha(pix.samples),
            'width':pix.width, 'height':pix.height, 'annotations':False}


def pdf_evidence_errors(source, evidence, contained):
    errors=[]
    review=evidence.get('pdf_review', {})
    if not isinstance(review, dict):
        return ['PDF review record required']
    if (not evidence.get('author') or not review.get('reviewer')
            or evidence.get('author') == review.get('reviewer')
            or review.get('verdict') != 'pass' or not review.get('timestamp')
            or not review.get('rationale')):
        errors.append('PDF independent visual review missing/failed')
    if review.get('evidence_binding') != binding(evidence):
        errors.append('PDF visual review stale for quote/context/locator')
    kind=evidence.get('excerpt_kind')
    required={'reading_order','context','negation','numbers','page_label','citation_status'}
    if evidence.get('citation_type') not in ('direct','secondary'):
        errors.append('PDF direct/secondary citation status required')
    if kind == 'table':
        required.update(('table_headers','table_units','table_notes'))
        if evidence.get('transcription_method') == 'manual_visual' or (isinstance(evidence.get('table_context'), dict) and evidence['table_context'].get('cell_trace')):
            required.update(('merged_headers','cell_mapping','note_scope','unit_origin'))
        table=evidence.get('table_context', {})
        if not isinstance(table,dict) or not all(table.get(k) for k in ('label','row','column','unit')):
            errors.append('PDF table label/row/column/unit context required')
        if 'context_bbox' not in evidence.get('locator', {}):
            errors.append('PDF table context bbox required')
    elif kind == 'footnote':
        required.add('footnote_marker')
        if not evidence.get('footnote_marker'):
            errors.append('PDF footnote marker required')
    elif kind != 'prose':
        errors.append('PDF excerpt kind required')
    features=review.get('checked_features', [])
    if not isinstance(features, list) or not all(isinstance(x,str) for x in features) or not required.issubset(features):
        errors.append('PDF critical features not reviewed')
    method=evidence.get('transcription_method')
    if method not in ('native_text', 'manual_visual'):
        errors.append('PDF raw OCR is not approved transcription')
    if method == 'manual_visual' and not evidence.get('transcription_note'):
        errors.append('PDF visual transcription rationale required')
    try:
        import fitz
        with fitz.open(source) as doc:
            if not doc.is_pdf or doc.needs_pass:
                raise ValueError('Readable original PDF required')
            page, box, context=page_and_boxes(doc, evidence.get('locator', {}))
            if kind == 'table' and (method == 'manual_visual' or (isinstance(evidence.get('table_context'), dict) and evidence['table_context'].get('cell_trace'))):
                from table_trace import trace_errors
                errors.extend(trace_errors(evidence, checked_box, page.rect))
            if method == 'native_text':
                normalize=lambda x: re.sub(r'\s+', '', x)
                quote=normalize(evidence.get('quote',''))
                if not quote or quote not in normalize(page.get_text('text',clip=fitz.Rect(box))):
                    errors.append('PDF quote absent from selected native-text region')
            proof=review.get('proof', {})
            if not isinstance(proof,dict):
                raise ValueError('PDF proof record required')
            if proof.get('source_sha256') != sha(Path(source).read_bytes()):
                errors.append('PDF proof source hash mismatch')
            dpi=proof.get('dpi')
            if type(dpi) is not int or not 100 <= dpi <= 300:
                raise ValueError('PDF proof dpi required')
            crop=contained(proof.get('crop_path', ''))
            if not crop.is_file() or sha(crop.read_bytes()) != proof.get('crop_sha256'):
                errors.append('PDF reviewed crop missing or modified')
            else:
                original=page.get_pixmap(dpi=dpi, clip=fitz.Rect(context), alpha=False, annots=False)
                saved=fitz.Pixmap(str(crop))
                if (sha(original.samples) != proof.get('pixel_sha256')
                        or (saved.width,saved.height,saved.n,saved.samples) !=
                           (original.width,original.height,original.n,original.samples)):
                    errors.append('PDF reviewed image does not match original page region')
    except (ImportError, OSError, ValueError, TypeError, KeyError, RuntimeError) as exc:
        errors.append('PDF original/proof verification failed: ' + str(exc)[:160])
    return errors
