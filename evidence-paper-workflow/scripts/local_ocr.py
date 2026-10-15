"""Local Windows OCR. Never marks evidence as verified; no network or fallback language."""
import json
import os
from pathlib import Path
import subprocess
import tempfile


def ocr_image(path, language='ko', timeout=90):
    path = Path(path).resolve(strict=True)
    if os.name != 'nt':
        raise RuntimeError('windows_ocr_unavailable')
    if language != 'ko':
        raise ValueError('Only explicitly tested Korean OCR is supported')
    if path.suffix.lower() not in {'.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff'}:
        raise ValueError('Unsupported image format')
    if path.stat().st_size > 50 * 1024 * 1024:
        raise ValueError('Image exceeds 50 MiB bound')
    executable = Path(os.environ.get('SystemRoot', 'C:/Windows')) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
    result = subprocess.run([str(executable), '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
        '-File', str(Path(__file__).with_name('windows_ocr.ps1')), '-ImagePath', str(path), '-Language', language],
        capture_output=True, timeout=min(max(timeout, 1), 120))
    if result.returncode:
        raise RuntimeError('Local OCR failed: ' + result.stderr.decode('utf-8', errors='replace')[-2000:])
    payload = json.loads(result.stdout.decode('utf-8-sig'))
    if payload['language'].split('-')[0] != 'ko':
        raise RuntimeError('OCR language mismatch')
    return payload


def ocr_pdf_regions(path, page_record, dpi=200, scratch_dir=None):
    """Render only queued failed regions; coordinates returned in original PDF points.

    Must consume the page record returned by pdf_blocks. No implicit full-document OCR.
    """
    import fitz
    if not 100 <= dpi <= 300:
        raise ValueError('OCR dpi must be 100..300')
    requests = page_record.get('ocr_regions', [])
    if len(requests) > 32:
        raise ValueError('At most 32 OCR regions per call')
    if not requests:
        return {'status': 'not_requested', 'regions': []}
    results = []
    with fitz.open(path) as doc, tempfile.TemporaryDirectory(dir=scratch_dir) as temporary:
        number = page_record['pdf_page']
        if not isinstance(number, int) or not 1 <= number <= len(doc):
            raise ValueError('Invalid one-based PDF page number')
        page = doc[number - 1]
        for index, request in enumerate(requests):
            clip = fitz.Rect(request['bbox']) & page.rect
            if clip.is_empty:
                raise ValueError('Invalid OCR region')
            image = Path(temporary) / f'region-{index}.png'
            pixmap = page.get_pixmap(dpi=dpi, clip=clip, alpha=False)
            pixmap.save(image)
            result = ocr_image(image)
            # Pixmap origin accounts for integer-pixel clipping at the chosen scale.
            for line in result['lines']:
                for word in line['words']:
                    x0, y0, x1, y1 = word['bbox']
                    word['pdf_bbox'] = [(x0+pixmap.x)*72/dpi, (y0+pixmap.y)*72/dpi,
                                        (x1+pixmap.x)*72/dpi, (y1+pixmap.y)*72/dpi]
            result.update(pdf_page=number, printed_page=None, requested_bbox=list(clip), reason=request['reason'])
            result['review_requirements'] = ['Visually compare negation, numbers, names and table cells.',
                'Do not treat OCR line order as verified column/table order.']
            results.append(result)
    return {'status': 'needs_visual_review', 'evidence_verified': False, 'regions': results}
