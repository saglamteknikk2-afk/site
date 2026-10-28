"""Small, reproducible truth corrections to the uploaded SEO additions.

``correct_content`` updates the supplied in-memory file mapping and returns an
audit report.  It never opens the uploaded archive or rewrites older articles.
Only newly added ``st-hub`` sections and their JSON-LD are considered.
"""

from __future__ import annotations

import html
import json
import re


HUB = re.compile(r'<section\b[^>]*class="st-hub\b[^"\n]*"[^>]*>.*?</section>', re.S)
JSON_LD = re.compile(
    r'(<script\b[^>]*type="application/ld\+json"[^>]*>)(.*?)(</script>)', re.S
)
DISTRICT_ANSWER = (
    "İstanbul Avrupa Yakası’ndaki 25 ilçeden servis talebi alınır. "
    "Aşağıdaki bağlantılar bazı hizmet bölgelerini gösterir; "
    "randevu uygunluğu görüşmede netleştirilir."
)
ADDRESS_NOTE = (
    "Randevu sırasında mahalle adının yanında sokak, bina ve kat bilgisini "
    "paylaşmanız, servis adresinin doğru kaydedilmesine yardımcı olur."
)


def correct_content(files: dict[str, bytes]) -> dict:
    """Mutate *files* with narrowly scoped corrections; return change evidence."""
    report = {"files_changed": [], "counts": {}, "details": []}

    def count(key: str, amount: int = 1) -> None:
        report["counts"][key] = report["counts"].get(key, 0) + amount

    for filename in sorted(files):
        if not filename.endswith(".html"):
            continue
        source = files[filename].decode("utf-8")
        replacements: dict[str, str] = {}

        def correct_hub(match: re.Match) -> str:
            section = match.group(0)
            section, amount = re.subn(
                r'sık gelen (kombi|klima) şikâyetleri', r'\1 belirtileri', section
            )
            count("unsupported_frequency_headings", amount)
            section, amount = re.subn(
                r'<p>Randevu sırasında mahalle adının yanında sokak, bina ve kat '
                r'bilgisini paylaşmanız, [^<]*?sınırına yakın adreslerde '
                r'ekibin doğru güzergâhı seçmesini kolaylaştırır\.</p>',
                '<p>' + ADDRESS_NOTE + '</p>', section,
            )
            count("unverified_border_sentences", amount)
            section, amount = re.subn(
                r'(<nav\b[^>]*aria-label=")([^"<>]+) komşu ilçeler(")',
                r'\1\2 diğer hizmet bölgeleri\3', section,
            )
            count("unverified_neighbor_labels", amount)
            section, amount = re.subn(
                r'<h2>[^<]+ çevresindeki ilçelerde (kombi|klima) servisi</h2>',
                r'<h2>Diğer ilçelerde \1 servisi</h2>', section,
            )
            count("nearby_heading_neutralized", amount)

            # The nine links are rotating examples, not a nine-district limit.
            def district_answer(match: re.Match) -> str:
                old = html.unescape(match.group(1))
                replacements[old] = DISTRICT_ANSWER
                count("brand_coverage_answers")
                return '<p>' + DISTRICT_ANSWER + '</p>'

            section = re.sub(
                r'<p>(İstanbul Avrupa Yakası(?:[\'’]|&#x27;|&#39;|&apos;)ndaki 9 ilçeye: [^<]+)</p>',
                district_answer, section,
            )

            # The catalogue can contain multiple document scopes per route.
            # State the number of published guide pages, not an ambiguous count.
            brand = re.search(
                r'<h2>([^<]+) (kombi|klima) kayıtları ve belge kapsamı</h2>', section
            )
            if brand:
                name, device = brand.groups()
                nav = re.search(
                    r'<nav\b[^>]*aria-label="' + re.escape(name) +
                    r' model rehberleri"[^>]*>(.*?)</nav>', section, re.S,
                )
                if nav:
                    routes = set(re.findall(r'<a\b[^>]*href="([^"#?]+)', nav.group(1)))
                    label = "Kombi" if device == "kombi" else "Klima"
                    replacement = (
                        f'{label} tarafında {len(routes)} ayrı model rehberi sayfası '
                        'yayımlanmıştır. Bu rehberlerden örnekler: '
                    )
                    section, amount = re.subn(
                        re.escape(label) +
                        r' tarafında \d+ model belgesi rehber olarak yayımlanmıştır: ',
                        replacement, section,
                    )
                    if amount:
                        count("guide_page_counts_clarified", amount)
                        report["details"].append({
                            "page": filename, "published_model_guide_pages": len(routes)
                        })
            return section

        source = HUB.sub(correct_hub, source)

        def correct_schema(match: re.Match) -> str:
            try:
                graph = json.loads(match.group(2))
            except json.JSONDecodeError:
                # The release validator reports malformed input separately.
                return match.group(0)
            changed = False

            def walk(value):
                nonlocal changed
                if isinstance(value, dict):
                    if value.get("priceRange") == "₺₺":
                        del value["priceRange"]
                        changed = True
                        count("invented_price_ranges_removed")
                    for key, item in list(value.items()):
                        if isinstance(item, str) and item in replacements:
                            value[key] = replacements[item]
                            changed = True
                        else:
                            walk(item)
                elif isinstance(value, list):
                    for item in value:
                        walk(item)

            walk(graph)
            if not changed:
                return match.group(0)
            return (
                match.group(1) + json.dumps(graph, ensure_ascii=False, separators=(",", ":"))
                + match.group(3)
            )

        source = JSON_LD.sub(correct_schema, source)
        updated = source.encode("utf-8")
        if updated != files[filename]:
            files[filename] = updated
            report["files_changed"].append(filename)

    report["counts"] = {key: value for key, value in report["counts"].items() if value}
    return report
