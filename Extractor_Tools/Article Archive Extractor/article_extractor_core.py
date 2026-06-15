from __future__ import annotations

# cspell:words charrefs drucken itemprop mehr noscript sitename startseite tagesschau teilen thema trafilatura

import csv
import hashlib
import json
import re
import time
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


USER_AGENT = "OntologyMachineArticleArchiveExtractor/1.0 (+local archive tool)"


@dataclass(frozen=True)
class ExtractOptions:
    output_dir: Path
    save_raw_html: bool = False
    overwrite: bool = False
    timeout_seconds: int = 30
    retries: int = 2
    sleep_seconds: float = 0.5


@dataclass(frozen=True)
class Article:
    url: str
    title: str
    text: str
    published_at: str | None
    author: str | None
    source_name: str | None
    extractor: str
    html: str


@dataclass(frozen=True)
class ArticleResult:
    ok: bool
    url: str
    output_path: Path | None = None
    title: str | None = None
    error: str | None = None
    extractor: str | None = None
    content_hash: str | None = None


class FallbackArticleParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.meta: dict[str, str] = {}
        self.title_parts: list[str] = []
        self.h1_blocks: list[str] = []
        self.article_blocks: list[str] = []
        self.global_blocks: list[str] = []
        self.time_values: list[str] = []
        self._ignored_depth = 0
        self._article_depth = 0
        self._main_depth = 0
        self._title_depth = 0
        self._current_tag: str | None = None
        self._current_in_content = False
        self._current_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attr = {key.lower(): value or "" for key, value in attrs}
        if tag in {"script", "style", "nav", "header", "footer", "aside", "form", "noscript", "svg"}:
            self._ignored_depth += 1
        if tag == "article":
            self._article_depth += 1
        if tag == "main":
            self._main_depth += 1
        if tag == "title":
            self._title_depth += 1
        if tag == "meta":
            self._record_meta(attr)
        if tag == "time" and attr.get("datetime"):
            self.time_values.append(attr["datetime"].strip())
        if self._ignored_depth:
            return
        if tag in {"h1", "h2", "p"}:
            self._current_tag = tag
            self._current_in_content = self._article_depth > 0 or self._main_depth > 0
            self._current_parts = []

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == self._current_tag:
            text = clean_text(" ".join(self._current_parts))
            if text:
                if tag == "h1":
                    self.h1_blocks.append(text)
                if self._current_in_content:
                    self.article_blocks.append(text)
                else:
                    self.global_blocks.append(text)
            self._current_tag = None
            self._current_in_content = False
            self._current_parts = []
        if tag == "title" and self._title_depth:
            self._title_depth -= 1
        if tag == "article" and self._article_depth:
            self._article_depth -= 1
        if tag == "main" and self._main_depth:
            self._main_depth -= 1
        if tag in {"script", "style", "nav", "header", "footer", "aside", "form", "noscript", "svg"} and self._ignored_depth:
            self._ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._ignored_depth:
            return
        if self._title_depth:
            self.title_parts.append(data)
        if self._current_tag:
            self._current_parts.append(data)

    def _record_meta(self, attr: dict[str, str]) -> None:
        key = attr.get("property") or attr.get("name") or attr.get("itemprop")
        value = attr.get("content")
        if not key or not value:
            return
        self.meta[key.strip().lower()] = value.strip()


def parse_urls(text: str) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    for match in re.finditer(r"https?://[^\s<>\"]+", text):
        url = match.group(0).rstrip(".,);]")
        key = url.lower()
        if key not in seen:
            seen.add(key)
            urls.append(url)
    return urls


def extract_many(
    urls: list[str],
    options: ExtractOptions,
    *,
    progress: Callable[[str], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> list[ArticleResult]:
    options.output_dir.mkdir(parents=True, exist_ok=True)
    results: list[ArticleResult] = []
    for index, url in enumerate(urls, start=1):
        if should_stop and should_stop():
            _log(progress, "Stopped by user.")
            break
        _log(progress, f"[{index}/{len(urls)}] Fetching {url}")
        result = extract_one(url, options)
        results.append(result)
        if result.ok:
            _log(progress, f"  OK -> {result.output_path}")
        else:
            _log(progress, f"  FAILED -> {result.error}")
        if index < len(urls) and options.sleep_seconds > 0:
            time.sleep(options.sleep_seconds)
    write_run_reports(options.output_dir, results)
    return results


def extract_one(url: str, options: ExtractOptions) -> ArticleResult:
    try:
        html = fetch_html(url, timeout_seconds=options.timeout_seconds, retries=options.retries)
        article = extract_article(url, html)
        if not article.text.strip():
            raise ValueError("No article text could be extracted.")
        path = write_article(article, options)
        content_hash = "sha256:" + sha256_text(article.text)
        return ArticleResult(
            ok=True,
            url=url,
            output_path=path,
            title=article.title,
            extractor=article.extractor,
            content_hash=content_hash,
        )
    except Exception as exc:  # noqa: BLE001 - user-facing batch tool needs per-URL failures.
        return ArticleResult(ok=False, url=url, error=str(exc))


def fetch_html(url: str, *, timeout_seconds: int, retries: int) -> str:
    last_error: Exception | None = None
    for attempt in range(max(1, retries + 1)):
        try:
            request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"})
            with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310 - user supplied archival URLs.
                content_type = response.headers.get_content_charset() or "utf-8"
                return response.read().decode(content_type, errors="replace")
        except (HTTPError, URLError, TimeoutError) as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(1.0 + attempt)
                continue
    raise RuntimeError(f"Fetch failed: {last_error}")


def extract_article(url: str, html: str) -> Article:
    trafilatura_article = _try_trafilatura(url, html)
    if trafilatura_article is not None:
        return trafilatura_article
    return _fallback_extract(url, html)


def _try_trafilatura(url: str, html: str) -> Article | None:
    try:
        import trafilatura  # type: ignore[import-not-found]
    except Exception:
        return None
    try:
        extracted = trafilatura.extract(
            html,
            url=url,
            output_format="json",
            include_comments=False,
            include_tables=True,
            with_metadata=True,
        )
        if not extracted:
            return None
        data = json.loads(extracted)
        text = normalize_article_text(str(data.get("text") or ""))
        if len(text) < 200:
            return None
        title = clean_title(str(data.get("title") or ""), url)
        return Article(
            url=url,
            title=title,
            text=text,
            published_at=none_if_blank(data.get("date")),
            author=none_if_blank(data.get("author")),
            source_name=none_if_blank(data.get("sitename")),
            extractor="trafilatura",
            html=html,
        )
    except Exception:
        return None


def _fallback_extract(url: str, html: str) -> Article:
    parser = FallbackArticleParser()
    parser.feed(html)
    title = clean_title(
        first_non_empty(
            parser.meta.get("og:title"),
            parser.meta.get("twitter:title"),
            parser.meta.get("headline"),
            parser.h1_blocks[0] if parser.h1_blocks else "",
            " ".join(parser.title_parts),
        ),
        url,
    )
    blocks = parser.article_blocks if block_text_length(parser.article_blocks) >= 300 else parser.global_blocks
    text = normalize_article_text("\n\n".join(filter_article_blocks(blocks)))
    return Article(
        url=url,
        title=title,
        text=text,
        published_at=first_non_empty(
            parser.meta.get("article:published_time"),
            parser.meta.get("date"),
            parser.meta.get("dc.date"),
            parser.meta.get("pubdate"),
            parser.time_values[0] if parser.time_values else "",
        )
        or None,
        author=first_non_empty(parser.meta.get("author"), parser.meta.get("article:author")) or None,
        source_name=first_non_empty(parser.meta.get("og:site_name"), urlparse(url).netloc) or None,
        extractor="fallback-html",
        html=html,
    )


def write_article(article: Article, options: ExtractOptions) -> Path:
    url_hash = sha256_text(article.url)
    url_id = url_hash[:12]
    content_hash = sha256_text(article.text)
    raw_html_path: str | None = None
    if options.save_raw_html:
        raw_dir = options.output_dir / "raw_html"
        raw_dir.mkdir(parents=True, exist_ok=True)
        raw_path = raw_dir / f"{url_id}.html"
        raw_path.write_text(article.html, encoding="utf-8", newline="\n")
        raw_html_path = str(raw_path.relative_to(options.output_dir)).replace("\\", "/")
    filename = build_filename(article.title, article.published_at, url_id)
    output_path = options.output_dir / filename
    if output_path.exists() and not options.overwrite:
        output_path = unique_path(output_path)
    markdown = render_markdown(article, content_hash=content_hash, url_hash=url_hash, raw_html_path=raw_html_path)
    output_path.write_text(markdown, encoding="utf-8", newline="\n")
    return output_path


def render_markdown(article: Article, *, content_hash: str, url_hash: str, raw_html_path: str | None) -> str:
    fetched_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    frontmatter = {
        "source_url": article.url,
        "source_domain": urlparse(article.url).netloc,
        "source_name": article.source_name,
        "title": article.title,
        "author": article.author,
        "published_at": article.published_at,
        "fetched_at": fetched_at,
        "url_hash": "sha256:" + url_hash,
        "content_hash": "sha256:" + content_hash,
        "extractor": article.extractor,
        "raw_html_path": raw_html_path,
    }
    lines = ["---"]
    for key, value in frontmatter.items():
        if value is None:
            lines.append(f"{key}: null")
        else:
            lines.append(f"{key}: {json.dumps(str(value), ensure_ascii=False)}")
    lines.extend(["---", "", f"# {article.title}", "", article.text.strip(), ""])
    return "\n".join(lines)


def write_run_reports(output_dir: Path, results: list[ArticleResult]) -> None:
    failed_path = output_dir / "failed_urls.csv"
    report_path = output_dir / "extraction_report.csv"
    with report_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["ok", "url", "title", "output_path", "extractor", "content_hash", "error"])
        for result in results:
            writer.writerow(
                [
                    result.ok,
                    result.url,
                    result.title or "",
                    str(result.output_path) if result.output_path else "",
                    result.extractor or "",
                    result.content_hash or "",
                    result.error or "",
                ]
            )
    failures = [result for result in results if not result.ok]
    with failed_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["url", "error"])
        for result in failures:
            writer.writerow([result.url, result.error or ""])


def filter_article_blocks(blocks: list[str]) -> list[str]:
    filtered: list[str] = []
    seen: set[str] = set()
    for block in blocks:
        cleaned = clean_text(block)
        if not cleaned or len(cleaned) < 40:
            continue
        lower = cleaned.lower()
        if len(cleaned) < 180 and any(marker in lower for marker in ("facebook", "whatsapp", "teilen", "drucken", "mehr zum thema", "zur startseite")):
            continue
        if lower in seen:
            continue
        seen.add(lower)
        filtered.append(cleaned)
    return filtered


def normalize_article_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    paragraphs = [clean_text(part) for part in re.split(r"\n{2,}", text)]
    paragraphs = [part for part in paragraphs if part]
    return "\n\n".join(paragraphs)


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def clean_title(title: str, url: str) -> str:
    title = clean_text(title)
    title = re.sub(r"\s+\|\s*tagesschau\.de\s*$", "", title, flags=re.IGNORECASE)
    title = re.sub(r"\s+-\s+tagesschau\.de\s*$", "", title, flags=re.IGNORECASE)
    if title:
        return title
    parsed = urlparse(url)
    fallback = Path(parsed.path).stem or parsed.netloc or "article"
    return fallback.replace("-", " ").strip().title()


def build_filename(title: str, published_at: str | None, url_hash: str) -> str:
    prefix = ""
    if published_at:
        match = re.search(r"\d{4}-\d{2}-\d{2}", published_at)
        if match:
            prefix = match.group(0) + "_"
    slug = slugify(title)[:100].strip("_-") or "article"
    return f"{prefix}{slug}_{url_hash}.md"


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_text = re.sub(r"[^A-Za-z0-9]+", "_", ascii_text)
    return re.sub(r"_+", "_", ascii_text).strip("_").lower()


def unique_path(path: Path) -> Path:
    stem = path.stem
    suffix = path.suffix
    for index in range(2, 10_000):
        candidate = path.with_name(f"{stem}_{index}{suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Could not find unique output path for {path}")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def block_text_length(blocks: list[str]) -> int:
    return sum(len(block) for block in blocks)


def first_non_empty(*values: object) -> str:
    for value in values:
        text = clean_text(str(value or ""))
        if text:
            return text
    return ""


def none_if_blank(value: object) -> str | None:
    text = clean_text(str(value or ""))
    return text or None


def _log(progress: Callable[[str], None] | None, message: str) -> None:
    if progress:
        progress(message)
