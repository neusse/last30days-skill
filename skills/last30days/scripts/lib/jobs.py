"""Public jobs/careers retrieval for Hiring Signals."""

from __future__ import annotations

import re
from html import unescape
from typing import Any

from . import grounding, http


ATS_PROVIDER_GREENHOUSE = "greenhouse"


def search_jobs(
    company: str,
    date_range: tuple[str, str],
    config: dict[str, Any],
    *,
    depth: str = "default",
    web_backend: str = "auto",
    explicit: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Fetch public job postings for a company.

    The first pass uses predictable public ATS endpoints. Generic web search is
    only a fallback because web snippets are weaker evidence than structured
    job posts.
    """
    company = company.strip()
    if not company:
        return [], {}

    items: list[dict[str, Any]] = []
    attempted: list[str] = []
    for token in _greenhouse_board_tokens(company):
        attempted.append(f"greenhouse:{token}")
        try:
            gh_items = search_greenhouse_board(token)
        except http.HTTPError as exc:
            if exc.status_code in {400, 401, 403, 404}:
                continue
            raise
        if gh_items:
            items.extend(gh_items)
            break

    if not items:
        fallback_items, artifact = search_jobs_web(
            company, date_range, config, backend=web_backend,
        )
        items.extend(fallback_items)
        if artifact:
            artifact.setdefault("attempted", attempted)
            return items, artifact

    return items, {
        "label": "jobs",
        "company": company,
        "attempted": attempted,
        "resultCount": len(items),
        "explicit": explicit,
    }


def search_greenhouse_board(board_token: str) -> list[dict[str, Any]]:
    """Return jobs from Greenhouse's public Job Board API."""
    url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs"
    data = http.get(url, params={"content": "true"}, timeout=15, retries=2)
    jobs = data.get("jobs") if isinstance(data, dict) else []
    if not isinstance(jobs, list):
        return []
    return [
        _greenhouse_job_to_item(job, board_token)
        for job in jobs
        if isinstance(job, dict)
    ]


def search_jobs_web(
    company: str,
    date_range: tuple[str, str],
    config: dict[str, Any],
    *,
    backend: str = "auto",
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Fallback to configured web search for public careers/jobs pages."""
    if backend == "none":
        return [], {}
    query = f'{company} careers jobs hiring'
    raw_items, artifact = grounding.web_search(query, date_range, config, backend=backend)
    items: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_items):
        if not isinstance(raw, dict):
            continue
        title = str(raw.get("title") or "").strip()
        url = str(raw.get("url") or "").strip()
        snippet = str(raw.get("snippet") or "").strip()
        if not _looks_like_jobs_page(title, url, snippet):
            continue
        items.append({
            "id": raw.get("id") or f"JW{index + 1}",
            "title": title,
            "url": url,
            "description": snippet,
            "date": raw.get("date"),
            "date_confidence": raw.get("date_confidence") or "low",
            "provider": "web",
            "source_domain": raw.get("source_domain"),
            "relevance": raw.get("relevance", 0.45),
            "why_relevant": "Public careers/jobs web result",
        })
    artifact = dict(artifact or {})
    artifact.update({"label": "jobs-web", "company": company, "resultCount": len(items)})
    return items, artifact


def parse_greenhouse_response(payload: dict[str, Any], board_token: str = "") -> list[dict[str, Any]]:
    """Parse a Greenhouse jobs payload for tests and callers with cached data."""
    jobs = payload.get("jobs") if isinstance(payload, dict) else []
    if not isinstance(jobs, list):
        return []
    return [
        _greenhouse_job_to_item(job, board_token)
        for job in jobs
        if isinstance(job, dict)
    ]


def _greenhouse_job_to_item(job: dict[str, Any], board_token: str) -> dict[str, Any]:
    departments = [
        str(dept.get("name") or "").strip()
        for dept in (job.get("departments") or [])
        if isinstance(dept, dict) and str(dept.get("name") or "").strip()
    ]
    offices = [
        str(office.get("name") or office.get("location") or "").strip()
        for office in (job.get("offices") or [])
        if isinstance(office, dict) and str(office.get("name") or office.get("location") or "").strip()
    ]
    location = ""
    if isinstance(job.get("location"), dict):
        location = str(job["location"].get("name") or "").strip()
    description = _clean_html(str(job.get("content") or ""))
    return {
        "id": f"GH{job.get('id') or job.get('internal_job_id') or board_token}",
        "title": str(job.get("title") or "").strip(),
        "url": str(job.get("absolute_url") or "").strip(),
        "description": description,
        "date": _date_part(job.get("updated_at")),
        "date_confidence": "high" if job.get("updated_at") else "low",
        "provider": ATS_PROVIDER_GREENHOUSE,
        "board_token": board_token,
        "department": departments[0] if departments else "",
        "departments": departments,
        "location": location,
        "offices": offices,
        "relevance": 0.75,
        "why_relevant": "Public Greenhouse job posting",
    }


def _greenhouse_board_tokens(company: str) -> list[str]:
    base = _company_slug(company)
    if not base:
        return []
    suffixes = ("", "careers", "jobs")
    candidates = [base]
    for suffix in suffixes[1:]:
        candidates.append(f"{base}{suffix}")
    compact = re.sub(r"(inc|labs|ai|hq|app|tech)$", "", base)
    if compact and compact != base:
        candidates.append(compact)
    deduped: list[str] = []
    for token in candidates:
        if token and token not in deduped:
            deduped.append(token)
    return deduped[:4]


def _company_slug(company: str) -> str:
    text = company.lower()
    text = re.sub(r"\b(inc|inc\.|llc|ltd|corp|corporation|company|co\.)\b", "", text)
    return re.sub(r"[^a-z0-9]+", "", text).strip()


def _date_part(value: Any) -> str | None:
    text = str(value or "")
    if not text:
        return None
    match = re.search(r"\d{4}-\d{2}-\d{2}", text)
    return match.group(0) if match else None


def _clean_html(value: str) -> str:
    value = unescape(value)
    value = re.sub(r"<br\s*/?>", "\n", value, flags=re.I)
    value = re.sub(r"</p\s*>", "\n", value, flags=re.I)
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def _looks_like_jobs_page(title: str, url: str, snippet: str) -> bool:
    haystack = " ".join([title, url, snippet]).lower()
    return bool(re.search(r"\b(careers?|jobs?|job openings?|hiring|greenhouse|lever|ashby|workable)\b", haystack))
