"""Read-only source adapters. Returned data never constitutes semantic verification.

KCI contract: https://www.kci.go.kr/kciportal/po/openapi/openDataView.kci?datasetBean.dtstSeqNo=1
No keys, raw exceptions, or unredacted request/response bodies are persisted.
"""
import hashlib
import html
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import unicodedata
from datetime import datetime, timezone
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import xml.etree.ElementTree as ET


def fetch_bytes(url):
    with urlopen(Request(url, headers={"User-Agent": "evidence-paper-workflow/0.1"}), timeout=25) as response:
        return response.read(10_000_001)


def redact(value, secret=""):
    text = str(value)
    if secret:
        for form in {secret, quote(secret, safe=""), html.escape(secret), quote(secret, safe="").replace("%20", "+")}:
            text = text.replace(form, "[REDACTED]")
    text = re.sub(r"(?i)([?&](?:key|api_key)=)[^&\s<\"']*", r"\1[REDACTED]", text)
    text = re.sub(r"(?is)(<(?:key|api_key)>).*?(</(?:key|api_key)>)", r"\1[REDACTED]\2", text)
    return text


def _tag(node):
    return node.tag.rsplit("}", 1)[-1]


def record_identity(record, operation):
    """Stable article ID, or reference content bound to its citing article."""
    try:
        root = ET.fromstring(record['xml'])
    except (KeyError, TypeError, ET.ParseError):
        return None
    if operation == 'articleSearch':
        ids = [n.get('article-id', '') for n in root.iter() if _tag(n) == 'articleInfo']
        return ids[0] if len(ids) == 1 and re.fullmatch(r'ART[0-9]{1,20}', ids[0]) else None
    parent = record.get('citing_article_id')
    if operation != 'referenceSearch' or not parent:
        return None
    canonical = ET.canonicalize(record['xml'], strip_text=True)
    return parent + ':' + hashlib.sha256(canonical.encode()).hexdigest()


def positive_integer(value):
    if isinstance(value, bool) or not re.fullmatch(r'[0-9]+', str(value)) or int(value) < 1:
        raise ValueError('Expected positive integer')
    return int(value)


def parse_kci(payload, secret="", operation=None):
    if len(payload) > 10_000_000:
        return {"status": "response_too_large"}
    try:
        text = payload.decode("utf-8-sig") if isinstance(payload, bytes) else payload
    except UnicodeDecodeError:
        return {"status": "malformed_xml"}
    if "<!DOCTYPE" in text.upper() or "<!ENTITY" in text.upper():
        return {"status": "unsafe_xml"}
    try:
        root = ET.fromstring(text)
    except (ET.ParseError, ValueError):
        return {"status": "malformed_xml"}
    error_nodes = [n for n in root.iter() if _tag(n).lower() in {"error", "errormessage", "errmsg"}]
    has_records = any(_tag(n) == "record" for n in root.iter())
    error_text = " ".join(" ".join(n.itertext()) for n in error_nodes)
    if not has_records and not error_nodes:
        error_text = " ".join(root.itertext())
    if any(s in error_text for s in ("등록되지 않은 key", "사용기간이 종료", "인증키", "INVALID_KEY", "UNAUTHORIZED")):
        return {"status": "authentication_error"}
    if error_text.strip() and error_nodes:
        return {"status": "api_error"}
    totals = [n.text for n in root.iter() if _tag(n) == "total"]
    try:
        total = int(totals[0]) if totals else None
        if total is not None and total < 0:
            raise ValueError()
    except (ValueError, TypeError):
        return {"status": "malformed_xml"}
    records = []
    parents = {child: parent for parent in root.iter() for child in parent}
    for node in root.iter():
        if _tag(node) == "record":
            provider_verified = next((n.text for n in node.iter() if _tag(n) == "verified"), None)
            records.append({"xml": redact(ET.tostring(node, encoding="unicode"), secret),
                            "provider_verified": provider_verified if provider_verified in {"Y", "N"} and provider_verified != secret else None,
                            "evidence_verification": "unreviewed"})
            if operation == 'referenceSearch':
                parent = parents.get(node)
                identifier = parent.get('article-id', '') if parent is not None and _tag(parent) == 'outputData' else ''
                if re.fullmatch(r'ART[0-9]{1,20}', identifier) and identifier != secret:
                    records[-1]['citing_article_id'] = identifier
    if operation == "articleDetail":
        # The detail contract has no total. Require one identifiable article,
        # including a nonempty title, rather than accepting an empty record.
        articles = [n for n in root.iter() if _tag(n) == "articleInfo"]
        if (total in {None, 1} and len(records) == 1 and len(articles) == 1
                and re.fullmatch(r"ART[0-9]{1,20}", articles[0].get("article-id", ""))
                and any(_tag(n) == "article-title" and "".join(n.itertext()).strip()
                        for n in articles[0].iter())):
            return {"status": "ok", "records": records}
        return {"status": "unexpected_schema"}
    if total is None:
        return {"status": "unexpected_schema"}
    if total == 0 and records:
        return {"status": "inconsistent_response"}
    return {"status": "zero_results" if total == 0 else "ok", "total": total, "records": records}


class KCIClient:
    endpoint = "https://open.kci.go.kr/po/openapi/openApiSearch.kci"
    allowed_parameters = {"title", "author", "journal", "doi", "institution", "affiliation",
                          "keyword", "abstract", "dateFrom", "dateTo", "regDateFrom", "regDateTo",
                          "modDateFrom", "modDateTo", "pubiYr", "year", "years", "id", "page", "displayCount", "sortNm"}

    def __init__(self, fetch=fetch_bytes, retries=2):
        self.fetch = fetch
        self.retries = max(0, min(int(retries), 2))

    def request(self, operation, **params):
        if operation not in {"articleSearch", "articleDetail", "referenceSearch"}:
            return {"status": "invalid_operation"}
        required = "id" if operation == "articleDetail" else "title"
        if not str(params.get(required, "")).strip():
            return {"status": "missing_" + required}
        if any(k.lower() in {"key", "api_key", "apikey", "kci_api_key", "apicode", "token", "authorization"} for k in params):
            return {"status": "reserved_parameter"}
        if set(params) - self.allowed_parameters:
            return {"status": "unknown_parameter"}
        try:
            pagination_valid = positive_integer(params.get("displayCount", 10)) <= 100 and positive_integer(params.get("page", 1)) >= 1
        except (ValueError, TypeError):
            pagination_valid = False
        if not pagination_valid:
            return {"status": "invalid_pagination"}
        params = {k: positive_integer(v) if k in {'page', 'displayCount'} else v for k, v in params.items()}
        secret = os.environ.get("KCI_API_KEY", "")
        if not secret:
            return {"status": "not_configured"}
        url = self.endpoint + "?" + urlencode({**params, "apiCode": operation, "key": secret})
        for attempt in range(self.retries + 1):
            try:
                result = parse_kci(self.fetch(url), secret, operation=operation)
                if operation == "articleDetail" and result.get("status") == "ok":
                    detail = ET.fromstring(result["records"][0]["xml"])
                    returned_ids = [n.get("article-id") for n in detail.iter() if _tag(n) == "articleInfo"]
                    if returned_ids != [params["id"]]:
                        result = {"status": "identifier_mismatch"}
                result["request_url"] = redact(url, secret)
                return result
            except HTTPError as error:
                if attempt == self.retries:
                    return {"status": "http_error", "http_status": error.code,
                            "attempts": attempt + 1, "request_url": redact(url, secret)}
            except Exception:
                # Never serialize exception strings: transports can echo the full URL/key.
                if attempt == self.retries:
                    return {"status": "network_error", "attempts": attempt + 1, "request_url": redact(url, secret)}

    def collect(self, title, checkpoint, operation="articleSearch", page_size=100, max_pages=100, **filters):
        page_size, max_pages = positive_integer(page_size), positive_integer(max_pages)
        if page_size > 100 or operation not in {'articleSearch', 'referenceSearch'}:
            raise ValueError("Invalid collection bounds")
        path = Path(checkpoint)
        query = {"operation": operation, "title": title, "page_size": page_size, "filters": filters}
        # Persist only non-secret request fields; request() prohibits credential overrides.
        if set(filters) - (self.allowed_parameters - {"page", "displayCount", "title"}):
            raise ValueError("Reserved query field")
        state = {"pagination_contract": 2, "query": query, "searched_at": datetime.now(timezone.utc).isoformat(), "next_page": 1, "total": None, "records": [], "completed_pages": [], "status": "pending"}
        if path.exists():
            state = json.loads(path.read_text(encoding="utf-8"))
            if state["query"] != query:
                raise ValueError("Checkpoint query mismatch")
            if state.get('pagination_contract') != 2:
                raise ValueError('Legacy checkpoint requires explicit revalidation; use a new checkpoint')
            if state["status"] == "complete":
                return state
        for _ in range(max_pages):
            page = state["next_page"]
            result = self.request(operation, title=title, page=page, displayCount=page_size, **filters)
            if result["status"] not in {"ok", "zero_results"}:
                state["status"] = result["status"]
            else:
                incoming = [record_identity(r, operation) for r in result['records']]
                prior = [record_identity(r, operation) for r in state['records']]
                expected = min(page_size, max(0, result['total'] - len(state['records'])))
                if state["total"] is not None and state["total"] != result["total"]:
                    state["status"] = "result_set_changed"
                elif len(state['records']) + len(incoming) > result['total']:
                    state['status'] = 'total_exceeded'
                elif len(incoming) != expected:
                    state['status'] = 'page_size_mismatch'
                elif None in incoming or None in prior:
                    state['status'] = 'unverifiable_record_identity'
                elif len(incoming) != len(set(incoming)):
                    state['status'] = 'duplicate_records_in_page'
                elif set(incoming).intersection(prior):
                    state["status"] = "overlapping_pages"
                else:
                    state["total"] = result["total"]
                    state["records"].extend(result["records"])
                    state["completed_pages"].append(page)
                    state["next_page"] += 1
                    state["status"] = "complete" if len(state["records"]) == result["total"] else "partial"
            state['last_page_check'] = {'page': page, 'requested_size': page_size,
                                        'returned_records': len(result.get('records', [])), 'status': state['status']}
            state["collected_count"] = len(state["records"])
            state["updated_at"] = datetime.now(timezone.utc).isoformat()
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_suffix(path.suffix + ".tmp")
            temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
            temporary.replace(path)
            if state["status"] != "partial":
                break
        return state


def _norm(text):
    return re.sub(r"\W", "", unicodedata.normalize("NFKC", str(text)).casefold())


def classify_duplicates(records):
    """Return review candidates only; never delete or merge source records.

    Input fields: paper_id, doi, kci_id, title, authors (ordered strings), year,
    version_type (published/preprint/translation), related_to (paper_id list).
    Translation/version relations require supplied metadata, not title guessing.
    """
    def doi_id(value):
        return re.sub(r"^(?:https?://(?:dx\.)?doi.org/|doi:\s*)", "", str(value or "").strip(), flags=re.I).casefold()
    pairs = []
    for i, left in enumerate(records):
        for right in records[i + 1:]:
            ids = [left.get("paper_id"), right.get("paper_id")]
            related = ids[1] in left.get("related_to", []) or ids[0] in right.get("related_to", [])
            same_doi = bool(doi_id(left.get("doi"))) and doi_id(left.get("doi")) == doi_id(right.get("doi"))
            same_kci = bool(left.get("kci_id")) and str(left["kci_id"]).casefold() == str(right.get("kci_id", "")).casefold()
            title_match = bool(left.get("title")) and _norm(left["title"]) == _norm(right.get("title", ""))
            metadata_match = (title_match and bool(left.get("authors")) and
                              [_norm(a) for a in left["authors"]] == [_norm(a) for a in right.get("authors", [])] and
                              bool(left.get("year")) and str(left["year"]) == str(right.get("year")))
            version_difference = left.get("version_type", "published") != right.get("version_type", "published")
            if related or ((same_doi or same_kci or metadata_match) and version_difference):
                status = "related_versions_keep_distinct"
            elif same_doi or same_kci:
                status = "duplicate_candidate" if metadata_match else "identifier_conflict_review"
            elif metadata_match:
                status = "metadata_duplicate_candidate"
            else:
                continue
            pairs.append({"paper_ids": ids, "status": status, "same_doi": same_doi, "same_kci_id": same_kci,
                          "action": "retain_both_pending_review"})
    return {"records": records, "pairs": pairs}


def crossref_identity(doi, title, authors, year, fetch=fetch_bytes):
    """Conservative bibliographic match only; never validates full text or meaning."""
    doi = re.sub(r"^https?://(?:dx\.)?doi.org/", "", doi.strip(), flags=re.I)
    try:
        message = json.loads(fetch("https://api.crossref.org/works/" + quote(doi, safe="")))["message"]
    except Exception:
        return {"status": "unverified", "reason": "metadata_unavailable"}
    actual_authors = [a.get("family", "") for a in message.get("author", [])]
    date = message.get("published", message.get("issued", {})).get("date-parts", [[]])
    actual_year = date[0][0] if date and date[0] else None
    checks = {"doi": _norm(message.get("DOI", "")) == _norm(doi),
              "title": any(_norm(t) == _norm(title) for t in message.get("title", [])),
              "authors": bool(authors) and bool(actual_authors) and [_norm(a) for a in authors] == [_norm(a) for a in actual_authors],
              "year": str(actual_year) == str(year)}
    missing = not title or not authors or not year or not message.get("title") or not actual_authors or not actual_year
    return {"status": "unverified" if missing else ("matched" if all(checks.values()) else "conflict"),
            "checks": checks, "metadata": message, "scope": "bibliographic_only"}


class _HTMLBlocks(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks, self.section, self.parts, self.active, self.skip = [], "", [], None, 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.skip += 1
        if not self.skip and (tag == "p" or re.fullmatch(r"h[1-6]", tag)):
            self.active, self.parts = tag, []

    def handle_data(self, data):
        if self.active and not self.skip:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.skip = max(0, self.skip - 1)
        if tag == self.active:
            value = " ".join("".join(self.parts).split())
            if tag.startswith("h"):
                self.section = value
            elif value:
                self.blocks.append({"section": self.section, "paragraph": len(self.blocks) + 1, "text": value})
            self.active = None


def extract_html(content, source_url):
    parser = _HTMLBlocks()
    parser.feed(content)
    return {"source_url": source_url, "sha256": hashlib.sha256(content.encode()).hexdigest(),
            "format": "html", "status": "needs_reading_order_review" if parser.blocks else "parse_failed",
            "blocks": parser.blocks, "limitations": ["Paragraph extraction excludes tables; review original HTML before evidence use."]}
