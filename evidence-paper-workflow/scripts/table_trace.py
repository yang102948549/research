"""Structural checks for selected scanned table cells, not automatic semantics."""
def trace_errors(evidence, checked_box, page_rect):
    t = evidence.get('table_context', {})
    if not isinstance(t, dict):
        return ['PDF scanned table context required']
    trace = t.get('cell_trace')
    if not isinstance(trace, dict):
        return ['PDF scanned table cell trace required']
    errors = []
    context = evidence['locator']['context_bbox']
    def box(value):
        b = checked_box(value, page_rect)
        if not (context[0] <= b[0] < b[2] <= context[2] and context[1] <= b[1] < b[3] <= context[3]):
            raise ValueError('table trace outside reviewed context')
        return b
    try:
        if trace.get('value') != evidence.get('quote') or not trace.get('value'):
            errors.append('PDF table cell value differs from quotation')
        if box(trace.get('bbox')) != evidence['locator']['bbox']:
            errors.append('PDF table cell bbox differs from locator')
        for axis in ('row', 'column'):
            index = trace.get(axis + '_index')
            headers = trace.get(axis + '_headers')
            if type(index) is not int or index < 0 or not isinstance(headers, list) or not headers:
                raise ValueError('table row/column index and header chain required')
            parent = None
            labels = []
            for h in headers:
                span = h.get('span')
                if (not isinstance(span, list) or len(span) != 2 or
                        any(type(x) is not int for x in span) or not 0 <= span[0] <= index <= span[1]):
                    raise ValueError('table cell outside header span')
                if parent and not parent[0] <= span[0] <= span[1] <= parent[1]:
                    raise ValueError('table merged header spans not nested')
                if not h.get('text'): raise ValueError('table header text required')
                box(h.get('bbox'))
                labels.append(h['text'])
                parent = span
            if t.get(axis) != ' > '.join(labels):
                errors.append('PDF table header labels differ from context')
        unit = trace.get('unit', {})
        if unit.get('text') != t.get('unit') or unit.get('status') not in ('printed', 'not_printed'):
            raise ValueError('table unit origin required')
        if unit['status'] == 'printed': box(unit.get('bbox'))
        elif not unit.get('rationale'): raise ValueError('absent unit explanation required')
        notes = trace.get('notes')
        if not isinstance(notes, list) or not notes:
            raise ValueError('table notes inventory required (explicit none if absent)')
        for note in notes:
            if not note.get('text') or type(note.get('applies_to_cell')) is not bool or not note.get('scope'):
                raise ValueError('table note text, scope and applicability required')
            box(note.get('bbox'))
        if not trace.get('population_scope'):
            raise ValueError('table denominator/population scope required')
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        errors.append('PDF table trace invalid: ' + str(exc))
    return errors
