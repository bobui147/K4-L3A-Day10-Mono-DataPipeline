from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from html.parser import HTMLParser
import json
from pathlib import Path

from core.config import Settings
from core.utils import ensure_parent, normalize_whitespace, read_json, write_json


CROSSREF_WORKS_URL = "https://api.crossref.org/works"


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def _plain_text(value: object) -> str:
    if isinstance(value, list):
        value = value[0] if value else ""
    if not isinstance(value, str):
        return ""
    parser = _TextExtractor()
    parser.feed(value)
    parser.close()
    return normalize_whitespace(" ".join(parser.parts))


def _crossref_date(value: object) -> str:
    if not isinstance(value, dict):
        return ""
    parts = value.get("date-parts")
    if isinstance(parts, list) and parts and isinstance(parts[0], list) and parts[0]:
        try:
            numbers = [int(part) for part in parts[0][:3]]
            return date(numbers[0], numbers[1] if len(numbers) > 1 else 1,
                        numbers[2] if len(numbers) > 2 else 1).isoformat()
        except (TypeError, ValueError):
            return ""
    timestamp = value.get("date-time")
    if isinstance(timestamp, str):
        try:
            return date.fromisoformat(timestamp[:10]).isoformat()
        except ValueError:
            return ""
    return ""


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Extract usable paper metadata from a Crossref works response."""
    message = payload.get("message") if isinstance(payload, dict) else None
    items = message.get("items") if isinstance(message, dict) else None
    if not isinstance(items, list):
        raise ValueError("Crossref response has no items list")

    records: list[PaperRecord] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        paper_id = _plain_text(item.get("DOI"))
        title = _plain_text(item.get("title"))
        summary = _plain_text(item.get("abstract"))
        published = next(
            (
                day for key in ("published", "published-online", "published-print", "issued", "created")
                if (day := _crossref_date(item.get(key)))
            ),
            "",
        )
        if not (paper_id and title and summary and published):
            continue

        authors = []
        for author in item.get("author") or []:
            if isinstance(author, dict):
                name = _plain_text(author.get("name")) or normalize_whitespace(
                    f"{_plain_text(author.get('given'))} {_plain_text(author.get('family'))}"
                )
                if name:
                    authors.append(name)
        categories = [_plain_text(subject) for subject in item.get("subject") or []]
        categories = [category for category in categories if category]
        abs_url = _plain_text(item.get("URL")) or f"https://doi.org/{paper_id}"
        pdf_url = next(
            (
                link["URL"] for link in item.get("link") or []
                if isinstance(link, dict) and isinstance(link.get("URL"), str)
                and (link.get("content-type") == "application/pdf" or link["URL"].lower().endswith(".pdf"))
            ),
            abs_url,
        )
        updated = _crossref_date(item.get("updated")) or _crossref_date(item.get("deposited")) or published
        records.append(PaperRecord(
            paper_id=paper_id,
            title=title,
            summary=summary,
            authors=authors,
            categories=categories,
            primary_category=categories[0] if categories else "",
            published=published,
            updated=updated,
            abs_url=abs_url,
            pdf_url=pdf_url,
            comment=f"Crossref record {paper_id}",
        ))
    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Use the preserved snapshot by default; refresh from Crossref on request."""
    snapshot = settings.paths.raw_api_response
    if not settings.refresh_source and snapshot.is_file():
        records = parse_crossref_payload(read_json(snapshot))
    else:
        try:
            import requests
            from requests.adapters import HTTPAdapter
            from urllib3.util.retry import Retry

            session = requests.Session()
            retry = Retry(
                total=3,
                backoff_factor=1,
                status_forcelist=(429, 500, 502, 503, 504),
                allowed_methods=frozenset({"GET"}),
            )
            session.mount("https://", HTTPAdapter(max_retries=retry))
            try:
                response = session.get(
                    CROSSREF_WORKS_URL,
                    params={
                        "query": settings.source_query,
                        "filter": settings.source_filter,
                        "rows": settings.max_results,
                    },
                    headers={"User-Agent": "day10-data-observability-lab/0.1 (training pipeline)"},
                    timeout=20,
                )
                response.raise_for_status()
                raw_bytes = response.content
                records = parse_crossref_payload(json.loads(raw_bytes))
                if not records:
                    raise ValueError("Crossref returned no usable records")
            finally:
                session.close()
        except (requests.RequestException, ValueError, TypeError, KeyError):
            if not snapshot.is_file():
                raise
            records = parse_crossref_payload(read_json(snapshot))
        else:
            ensure_parent(snapshot)
            snapshot.write_bytes(raw_bytes)

    if not records:
        raise ValueError("No usable Crossref records in API response or snapshot")
    write_json(settings.paths.raw_records_json, [asdict(record) for record in records])
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load the extracted raw record artifact for later pipeline stages."""
    payload = read_json(path)
    if not isinstance(payload, list):
        raise ValueError(f"Expected a list of paper records in {path}")
    return [PaperRecord(**item) for item in payload]
