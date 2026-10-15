"""Bounded read-only KCI connection check; never prints URLs, XML or credentials."""
import argparse
import json
import re
import xml.etree.ElementTree as ET

from sources import KCIClient


def article_id(result):
    """Read only the documented articleInfo article-id attribute."""
    for record in result.get("records", [])[:1]:
        try:
            root = ET.fromstring(record["xml"])
        except (KeyError, TypeError, ET.ParseError):
            return None
        for node in root.iter():
            if node.tag.rsplit("}", 1)[-1] == "articleInfo":
                value = node.get("article-id", "")
                if re.fullmatch(r"ART[0-9]{1,20}", value):
                    return value
    return None


def probe(title, client=None):
    client = client or KCIClient(retries=0)
    rows = []

    def request(operation, **params):
        result = client.request(operation, **params)
        row = {"operation": operation, "status": result.get("status", "unexpected_schema")}
        if isinstance(result.get("total"), int):
            row["total"] = result["total"]
        row["returned_records"] = len(result.get("records", []))
        rows.append(row)
        return result

    search = request("articleSearch", title=title, page=1, displayCount=1)
    if search.get("status") not in {"ok", "zero_results"}:
        return {"status": search.get("status", "unexpected_schema"), "checks": rows,
                "evidence_verified": False}
    identifier = article_id(search)
    if identifier:
        request("articleDetail", id=identifier)
    else:
        rows.append({"operation": "articleDetail", "status": "skipped_no_article_id"})
    request("referenceSearch", title=title, page=1, displayCount=1)
    failures = [row["status"] for row in rows if row["status"] not in
                {"ok", "zero_results", "skipped_no_article_id"}]
    status = failures[0] if failures else ("partial_no_article_id" if not identifier else "ok")
    return {"status": status, "checks": rows, "evidence_verified": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--title", default="컴퓨터", help="Public search term; never put a key here")
    args = parser.parse_args()
    result = probe(args.title)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
