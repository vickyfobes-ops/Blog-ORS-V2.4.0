#!/usr/bin/env python3
"""Run an isolated, end-to-end reliability test for the installed Skill.

The test never calls Shopify or the public internet. It creates a realistic
local review bundle, runs the publication gate, builds and verifies a DOCX,
renders it with the Codex document renderer, compares the locked first-page
typography/layout region, and proves that known-invalid bundles and DOCX files
are rejected.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


SKILL_VERSION = "2.4.3"
SKILL_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_ROOT / "scripts"
REFERENCE_PAGE = SKILL_ROOT / "assets" / "format-reference" / "latest-format-page-1.png"
VISUAL_DIFF_LIMIT = 0.010
VISUAL_QA_KEYS = (
    "inspected",
    "noScreenUiTextLogo",
    "realisticMaterialScale",
    "sectionRelevant",
)


class SelfTestError(RuntimeError):
    pass


def run(command: list[str], *, expected: int = 0) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if result.returncode != expected:
        output = "\n".join(value for value in (result.stdout.strip(), result.stderr.strip()) if value)
        raise SelfTestError(
            f"command returned {result.returncode}; expected {expected}: {' '.join(command)}\n{output}"
        )
    return result


def required_runtime() -> None:
    try:
        import PIL  # noqa: F401
        import docx  # noqa: F401
    except ImportError as exc:
        raise SelfTestError(
            "run self_test.py with the Codex workspace document Python runtime; "
            f"missing dependency: {exc.name}"
        ) from exc


def sfnt_tables(data: bytes) -> dict[bytes, tuple[int, int]]:
    if len(data) < 12:
        raise SelfTestError("font file is too small to contain an SFNT directory")
    table_count = struct.unpack(">H", data[4:6])[0]
    tables: dict[bytes, tuple[int, int]] = {}
    for index in range(table_count):
        start = 12 + index * 16
        if start + 16 > len(data):
            raise SelfTestError("font table directory is truncated")
        tag, _checksum, offset, length = struct.unpack(">4sIII", data[start : start + 16])
        if offset + length > len(data):
            raise SelfTestError(f"font table {tag!r} is truncated")
        tables[tag] = (offset, length)
    return tables


def font_names(font_path: Path) -> dict[int, set[str]]:
    data = font_path.read_bytes()
    tables = sfnt_tables(data)
    if b"name" not in tables:
        raise SelfTestError(f"font has no name table: {font_path}")
    offset, _length = tables[b"name"]
    _format, count, string_offset = struct.unpack(">HHH", data[offset : offset + 6])
    storage = offset + string_offset
    names: dict[int, set[str]] = {}
    for index in range(count):
        start = offset + 6 + index * 12
        platform, _encoding, _language, name_id, length, name_offset = struct.unpack(
            ">HHHHHH", data[start : start + 12]
        )
        raw = data[storage + name_offset : storage + name_offset + length]
        try:
            value = raw.decode("utf-16-be" if platform in {0, 3} else "mac_roman").strip()
        except UnicodeDecodeError:
            continue
        if value:
            names.setdefault(name_id, set()).add(value)
    return names


def verify_font_assets() -> dict[str, str]:
    font_dir = SKILL_ROOT / "assets" / "fonts"
    expected = {
        "Poppins-Regular.ttf": ("Poppins", "Regular"),
        "Poppins-Bold.ttf": ("Poppins", "Bold"),
        "LibreBaskerville-Regular.ttf": ("Libre Baskerville", "Regular"),
        "LibreBaskerville-Bold.ttf": ("Libre Baskerville", "Bold"),
    }
    report: dict[str, str] = {}
    for filename, (family, face) in expected.items():
        path = font_dir / filename
        if not path.is_file():
            raise SelfTestError(f"required font asset is missing: {path}")
        data = path.read_bytes()
        tables = sfnt_tables(data)
        names = font_names(path)
        family_names = names.get(1, set()) | names.get(16, set())
        face_names = names.get(2, set()) | names.get(17, set())
        if family not in family_names:
            raise SelfTestError(f"{filename} family is {sorted(family_names)!r}; expected {family!r}")
        if face not in face_names:
            raise SelfTestError(f"{filename} face is {sorted(face_names)!r}; expected {face!r}")
        os2 = tables.get(b"OS/2")
        if not os2 or os2[1] < 10:
            raise SelfTestError(f"{filename} has no usable OS/2 embedding record")
        fs_type = struct.unpack(">H", data[os2[0] + 8 : os2[0] + 10])[0]
        if fs_type & 0x0002:
            raise SelfTestError(f"{filename} forbids document embedding (fsType={fs_type})")
        report[filename] = f"{family} {face}; fsType={fs_type}"
    return report


def markdown_inline_to_html(value: str) -> str:
    output: list[str] = []
    position = 0
    for match in re.finditer(r"\[([^\]]+)\]\(([^)]+)\)", value):
        output.append(html.escape(value[position : match.start()]))
        output.append(
            f'<a href="{html.escape(match.group(2), quote=True)}">{html.escape(match.group(1))}</a>'
        )
        position = match.end()
    output.append(html.escape(value[position:]))
    return "".join(output)


class FixtureArticle:
    def __init__(self) -> None:
        self.markdown: list[str] = []
        self.body_html: list[str] = []

    def h2(self, value: str) -> None:
        self.markdown.extend([f"## {value}", ""])
        self.body_html.append(f"<h2>{html.escape(value)}</h2>")

    def h3(self, value: str) -> None:
        self.markdown.extend([f"### {value}", ""])
        self.body_html.append(f"<h3>{html.escape(value)}</h3>")

    def paragraph(self, value: str) -> None:
        self.markdown.extend([value, ""])
        self.body_html.append(f"<p>{markdown_inline_to_html(value)}</p>")

    def bullets(self, values: list[str]) -> None:
        self.markdown.extend([*(f"- {value}" for value in values), ""])
        items = "".join(f"<li>{markdown_inline_to_html(value)}</li>" for value in values)
        self.body_html.append(f"<ul>{items}</ul>")

    def numbers(self, values: list[str]) -> None:
        self.markdown.extend([*(f"{index}. {value}" for index, value in enumerate(values, 1)), ""])
        items = "".join(f"<li>{markdown_inline_to_html(value)}</li>" for value in values)
        self.body_html.append(f"<ol>{items}</ol>")

    def table(self, headers: list[str], rows: list[list[str]]) -> None:
        self.markdown.append("| " + " | ".join(headers) + " |")
        self.markdown.append("| " + " | ".join("---" for _ in headers) + " |")
        self.markdown.extend("| " + " | ".join(row) + " |" for row in rows)
        self.markdown.append("")
        head = "".join(f"<th>{html.escape(value)}</th>" for value in headers)
        body = "".join(
            "<tr>" + "".join(f"<td>{html.escape(value)}</td>" for value in row) + "</tr>"
            for row in rows
        )
        self.body_html.append(f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>")

    def image(self, slot: str, alt: str) -> None:
        self.body_html.append(f'<figure><img src="origin-asset://{slot}" alt="{html.escape(alt, quote=True)}"></figure>')

    def experience_start(self) -> None:
        self.body_html.append("<!-- origin-experience:start -->")

    def experience_end(self) -> None:
        self.body_html.append("<!-- origin-experience:end -->")


def make_fixture_images(bundle: Path) -> None:
    from PIL import Image, ImageDraw

    image_dir = bundle / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
    palettes = [
        ((230, 230, 226), (95, 115, 105)),
        ((222, 212, 198), (137, 96, 66)),
        ((215, 225, 231), (54, 104, 128)),
        ((235, 228, 215), (88, 88, 82)),
    ]
    for index, (background, accent) in enumerate(palettes, 1):
        image = Image.new("RGB", (1672, 941), background)
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 650, 1672, 941), fill=tuple(max(0, value - 18) for value in background))
        draw.ellipse((350 + index * 35, 115, 1040 + index * 45, 805), fill=accent)
        draw.ellipse((570 + index * 20, 255, 850 + index * 20, 600), fill=background)
        draw.polygon([(920, 740), (1320, 210), (1450, 740)], fill=tuple(min(255, value + 35) for value in accent))
        image.save(image_dir / f"fixture-{index}.png", format="PNG", optimize=True)
        image.save(image_dir / f"fixture-{index}.webp", format="WEBP", quality=82, method=6)


def build_fixture(bundle: Path) -> None:
    bundle.mkdir(parents=True, exist_ok=True)
    make_fixture_images(bundle)
    title = "Sculpture Finish Guide: Choosing Bronze, Stainless Steel, Stone and Fiberglass Finishes"
    seo_title = "Sculpture Finishes Guide: Bronze, Stainless Steel, Stone & Fiberglass"
    description = (
        "Compare sculpture finish choices by material, setting, maintenance, sample approval, and the "
        "questions a buyer should resolve with Origin Sculpture."
    )
    article = FixtureArticle()
    article.paragraph(
        "Choose a sculpture finish by matching the material, site exposure, light, touch, and maintenance "
        "plan—not by color alone. Mirror or satin metal changes reflection and fingerprint visibility; "
        "polished, honed, or textured stone changes color depth and moisture retention; and gloss, satin, "
        "or matte fiberglass changes color intensity, scratch visibility, and repair requirements. Approve "
        "the final finish on a physical control sample under the project's actual lighting before production."
    )
    article.paragraph(
        "A finish connects the substrate, surface preparation, visual treatment, protective coating, "
        "environment, and future care. If the material is undecided, use the sculpture material guide first. "
        "Finish cannot correct an unsuitable alloy, stone, composite system, or drainage detail."
    )
    article.paragraph(
        "The decision sequence is: define the site, compare materials, understand cost, approve a sample, "
        "inspect production, and document maintenance."
    )

    first_heading = "Define Your Sculpture Finish Project: Site, Purpose, and Visual Intent"
    article.h2(first_heading)
    article.paragraph(
        "Start with what the customer can see and decide. The site, main viewing distance, daylight, artificial "
        "lighting, expected touch, weather, cleaning access, and surrounding materials all change how a finish "
        "looks in use. The [sculpture buying guide](https://originsculpture.com/blogs/news/sculpture-buying-guide) "
        "helps a buyer organize these choices before asking for a quotation. A nearby "
        "[mirror-polished stainless steel sample](https://originsculpture.com/products/origin-stainless-steel-color-sample-mirror-polish-sliver-finish-os-009) "
        "shows reflection more honestly than a color name on a screen."
    )
    article.image("site-scene", "Abstract metal sculpture viewed in a contemporary courtyard without screens or text")
    article.paragraph(
        "For a custom project, the useful first conversation is not a factory lecture. It is a plain description "
        "of the space, the feeling the client wants, the approximate scale, preferred materials, important "
        "colors, timing constraints, and who will approve the design. Origin pages and product examples should "
        "support that conversation by giving the buyer concrete visual references rather than forcing an early "
        "technical specification."
    )
    article.bullets(
        [
            "Share photographs and basic dimensions of the intended location.",
            "Identify the primary viewing direction and whether people can touch the sculpture.",
            "Choose two or three visual references and explain what is appealing about each one.",
            "State the maintenance tolerance and any important delivery or access constraint.",
        ]
    )

    article.h2("What Information Helps Origin Sculpture Recommend a Direction?")
    article.paragraph(
        "A concise brief lets the discussion stay useful. Customers do not need to know every fabrication term. "
        "They need to explain the setting, desired effect, decision makers, and limits that could change material, "
        "finish, size, packing, or installation. A [verdigris bronze patina sample](https://originsculpture.com/products/verdigris-bronze-patina-finish-sample-ob-007) "
        "can then be discussed as a visible option, not as proof that one finish suits every climate or project."
    )
    article.table(
        ["Customer question", "Why it matters", "Useful reference", "Decision to record"],
        [
            ["Where will it go?", "Exposure and access", "Site photographs", "Indoor or outdoor setting"],
            ["How should it feel?", "Guides form and color", "Two visual examples", "Preferred direction"],
            ["How large should it be?", "Changes presence and logistics", "Measured site view", "Approximate scale"],
            ["Who approves it?", "Prevents conflicting feedback", "Named review team", "Final decision maker"],
            ["How will it be cared for?", "Changes finish priorities", "Cleaning access notes", "Care expectations"],
        ],
    )
    article.paragraph(
        "This information is enough to begin. Detailed drawings, structural coordination, coating systems, or "
        "lifting plans belong later, after a direction is selected and only when they affect the buyer's approval, "
        "budget, site preparation, or long-term care."
    )

    article.h2("Use Origin's Site to Compare Real Choices, Not Just Process Steps")
    article.paragraph(
        "A site-led article should connect advice to pages a customer can actually explore. The "
        "[sculpture materials guide](https://originsculpture.com/blogs/news/sculpture-materials-guide) explains the "
        "main material families, while a [blue fiberglass color sample](https://originsculpture.com/products/original-fiberglass-color-sample-blue-of-001) "
        "gives a specific color reference. These links earn their place because they help the reader compare a "
        "decision; they should not be grouped into a sales paragraph merely to increase link count."
    )
    article.paragraph(
        "The buyer should leave each section knowing what to look at next. A material page can answer whether a "
        "surface is visually appropriate. A related guide can explain maintenance or placement. A consultation "
        "then resolves the project-specific facts that the website cannot know, such as exact dimensions, site "
        "access, approval sequence, and the desired degree of natural variation."
    )

    article.experience_start()
    article.h2("How Origin Sculpture Uses Samples and Review Points to Keep the Choice Clear")
    article.paragraph(
        "Origin Sculpture can use the customer's site information and selected references to connect material "
        "selection with finish approval. A physical sample gives the discussion a stable reference for color, "
        "gloss, texture, and acceptable variation. The customer can review that reference under relevant light "
        "before the approved finish is carried into production."
    )
    article.paragraph(
        "During production and quality control, the approved sample is more useful than a vague phrase such as "
        "warm bronze or soft silver. Inspection can compare visible appearance with the agreed reference, while "
        "site conditions, packing, installation access, and future maintenance remain separate checks. This is "
        "the amount of process detail a buyer needs: what is approved, when it is reviewed, and what information "
        "must remain consistent. It avoids pretending that every project follows an identical sequence or that a "
        "small sample can predict every natural or fabricated variation."
    )
    article.experience_end()

    approval_heading = "What Should the Customer Approve Before Production?"
    article.image("approval-scene", "Finish samples reviewed beside a sculpture maquette in a studio without visible labels")
    article.h2(approval_heading)
    article.paragraph(
        "Approvals should be easy to understand and tied to visible outcomes. The customer normally benefits from "
        "confirming the design direction, approximate scale, material family, finish reference, important color or "
        "texture limits, base relationship, and the information needed for delivery and installation planning. "
        "Technical documents can support those decisions without taking over the article."
    )
    article.numbers(
        [
            "Confirm the preferred concept and the views that matter most.",
            "Confirm the material and the representative finish reference.",
            "Record acceptable variation instead of promising impossible uniformity.",
            "Identify the site, access, base, and installation questions that still need answers.",
            "Keep the latest approved reference available for final review and care planning.",
        ]
    )
    article.paragraph(
        "The broader [custom sculpture cost guide](https://originsculpture.com/blogs/news/custom-sculpture-cost) "
        "shows why these choices also affect pricing, packing, delivery, and installation. Linking to that guide "
        "is more useful than inserting a long generic explanation of workshop labor into a customer-facing "
        "process article."
    )

    article.h2("Common Ways a Custom Sculpture Process Article Loses the Customer")
    article.paragraph(
        "A process article becomes difficult when it lists every workshop stage before explaining what the buyer "
        "needs to decide. Long sections about welding sequences, mold systems, internal support, inspection codes, "
        "or lifting calculations can sound authoritative while hiding the next action. Include such detail only "
        "when it changes appearance, approval, safety, site preparation, maintenance, or cost."
    )
    article.paragraph(
        "The article also loses trust when it invents a project, client preference, factory statistic, material "
        "grade, lead time, or guaranteed outcome. Use verified Origin pages for Origin-specific statements and "
        "authoritative technical sources for general claims. If a business fact is unavailable, leave it out or "
        "request it before publication."
    )

    article.h2("Frequently Asked Customer Questions")
    article.h3("Do I need a complete technical specification before contacting Origin?")
    article.paragraph(
        "No. A useful starting brief can contain site photographs, approximate dimensions, preferred visual "
        "references, material or color ideas, timing constraints, and the people responsible for approval. The "
        "remaining technical questions can be organized after the project direction is understood."
    )
    article.h3("Why is a physical finish sample useful?")
    article.paragraph(
        "A physical sample lets the customer compare color, gloss, texture, and variation under relevant light. "
        "It does not reproduce the scale, curvature, fabrication, or natural variation of the entire sculpture, "
        "so the approval should record both the target and reasonable limits."
    )
    article.h3("Can every custom project follow the same process?")
    article.paragraph(
        "No. Material, scale, site, access, installation responsibility, and review requirements change the "
        "sequence. A customer-facing guide should explain stable decision points while avoiding an unsupported "
        "claim that every sculpture uses one fixed production workflow."
    )

    closing_heading = "Start With a Clear Project Brief"
    article.image("project-review", "Customer and designer reviewing sculpture references and material samples at a clear table")
    article.h2(closing_heading)
    article.paragraph(
        "Begin with the space, desired experience, approximate size, material or finish references, timing, budget "
        "boundaries, and decision makers. Origin Sculpture can use that information to identify the choices that "
        "need discussion without requiring the customer to translate an internal production manual. A clear brief "
        "creates a practical path from website inspiration to a project-specific conversation."
    )

    meta = {
        "siteDomain": "originsculpture.com",
        "blogHandle": "news",
        "title": title,
        "seoTitle": seo_title,
        "metaDescription": description,
        "handle": "origin-skill-self-test",
        "author": "Origin Sculpture",
        "publicationAction": "create",
        "contentTier": "supporting",
        "editorialMode": "site-led",
        "tags": ["Buying Guide", "Self Test"],
        "blogFilters": ["Sculpture Buying Guide"],
        "templateSuffix": None,
    }
    (bundle / "meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    review = "\n".join(
        [
            "# Review Pack",
            "",
            "## SEO Pack",
            "",
            f"- SEO title: {seo_title}",
            f"- H1: {title}",
            "- Slug: `origin-skill-self-test`",
            f"- Meta description: {description}",
            "- Primary query: custom sculpture process",
            "",
            "## Article",
            "",
            f"# {title}",
            "",
            *article.markdown,
        ]
    ).strip() + "\n"
    (bundle / "article.md").write_text(review, encoding="utf-8")
    (bundle / "article.html").write_text("\n".join(article.body_html) + "\n", encoding="utf-8")
    (bundle / "summary.html").write_text(
        "<p>A customer-readable guide to choosing, reviewing, and approving a custom sculpture direction.</p>\n",
        encoding="utf-8",
    )
    (bundle / "brief.md").write_text(
        "# Brief\n\n- Tier: supporting\n- Editorial mode: site-led\n- Purpose: deterministic Skill self-test only\n",
        encoding="utf-8",
    )
    (bundle / "image-plan.md").write_text(
        "# Image plan\n\nAll generated fixtures are local self-test scenes with no claim of an Origin project.\n",
        encoding="utf-8",
    )
    (bundle / "sources.md").write_text(
        "# Sources\n\nRetrieved: 2026-08-25\n\n"
        "- [National Park Service](https://www.nps.gov/orgs/1739/upload/tech-note-metals-01-bronze-sculpture.pdf) — test source mapping.\n"
        "- [Natural Stone Institute](https://www.naturalstoneinstitute.org/default/assets/file/consumers/glossary.pdf) — test terminology mapping.\n\n"
        "## Origin experience evidence\n\n"
        "- [Origin Sculpture material guide](https://originsculpture.com/blogs/news/sculpture-materials-guide) — supports the visible material-choice context used in the fixture.\n",
        encoding="utf-8",
    )
    links = [
        ("https://originsculpture.com/blogs/news/sculpture-buying-guide", "article", "sculpture buying guide"),
        ("https://originsculpture.com/products/origin-stainless-steel-color-sample-mirror-polish-sliver-finish-os-009", "product", "mirror-polished stainless steel sample"),
        ("https://originsculpture.com/products/verdigris-bronze-patina-finish-sample-ob-007", "product", "verdigris bronze patina sample"),
        ("https://originsculpture.com/blogs/news/sculpture-materials-guide", "article", "sculpture materials guide"),
        ("https://originsculpture.com/products/original-fiberglass-color-sample-blue-of-001", "product", "blue fiberglass color sample"),
        ("https://originsculpture.com/blogs/news/custom-sculpture-cost", "article", "custom sculpture cost guide"),
    ]
    (bundle / "link-plan.json").write_text(
        json.dumps(
            [
                {
                    "url": url,
                    "type": link_type,
                    "anchor": anchor,
                    "relevance": "Self-test entry verifies a distributed, contextually described internal link.",
                }
                for url, link_type, anchor in links
            ],
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    qa_true = {key: True for key in VISUAL_QA_KEYS}
    assets = [
        {
            "slot": "cover",
            "png": "images/fixture-1.png",
            "webp": "images/fixture-1.webp",
            "placement": "Shopify article cover image",
            "alt": "Abstract sculpture in a neutral architectural environment for format testing",
            "sourceType": "generated-editorial",
            "visualRole": "environment-scene",
            "visualQa": qa_true,
        },
        {
            "slot": "site-scene",
            "png": "images/fixture-2.png",
            "webp": "images/fixture-2.webp",
            "placement": f"After {first_heading}",
            "alt": "Abstract metal sculpture viewed in a contemporary courtyard without screens or text",
            "sourceType": "generated-editorial",
            "visualRole": "environment-scene",
            "visualQa": qa_true,
        },
        {
            "slot": "approval-scene",
            "png": "images/fixture-3.png",
            "webp": "images/fixture-3.webp",
            "placement": f"Before {approval_heading}",
            "alt": "Finish samples reviewed beside a sculpture maquette in a studio without visible labels",
            "sourceType": "generated-editorial",
            "visualRole": "process-scene",
            "visualQa": qa_true,
        },
        {
            "slot": "project-review",
            "png": "images/fixture-4.png",
            "webp": "images/fixture-4.webp",
            "placement": f"Before {closing_heading}",
            "alt": "Customer and designer reviewing sculpture references and material samples at a clear table",
            "sourceType": "origin-owned",
            "visualRole": "product-evidence",
            "visualQa": qa_true,
        },
    ]
    (bundle / "image-assets.json").write_text(json.dumps(assets, indent=2) + "\n", encoding="utf-8")


def find_renderer(explicit: Path | None) -> Path:
    if explicit:
        renderer = explicit.expanduser().resolve()
        if not renderer.is_file():
            raise SelfTestError(f"document renderer does not exist: {renderer}")
        return renderer
    roots = [
        Path.home() / ".codex" / "plugins" / "cache" / "openai-primary-runtime",
        Path.home() / ".codex" / "plugins" / "cache" / "openai-bundled",
    ]
    candidates: list[Path] = []
    for root in roots:
        if root.is_dir():
            candidates.extend(root.glob("**/skills/documents/render_docx.py"))
    if not candidates:
        raise SelfTestError(
            "Codex document renderer was not found; load workspace dependencies or pass --renderer /absolute/render_docx.py"
        )
    return max(candidates, key=lambda path: path.stat().st_mtime)


def compare_rendered_first_page(rendered_page: Path) -> float:
    from PIL import Image, ImageChops, ImageStat

    if not REFERENCE_PAGE.is_file():
        raise SelfTestError(f"locked format reference is missing: {REFERENCE_PAGE}")
    reference = Image.open(REFERENCE_PAGE).convert("L")
    rendered = Image.open(rendered_page).convert("L")
    if rendered.size != reference.size:
        rendered = rendered.resize(reference.size)
    # The fixture cover intentionally differs from the merchant image. Compare
    # from the title region downward so the test measures typography, spacing,
    # line wrapping, and first-page flow rather than picture pixels.
    top = int(reference.height * 0.42)
    reference = reference.crop((0, top, reference.width, reference.height))
    rendered = rendered.crop((0, top, rendered.width, rendered.height))
    reference_mask = reference.point(lambda value: 0 if value < 180 else 255)
    rendered_mask = rendered.point(lambda value: 0 if value < 180 else 255)
    difference = ImageChops.difference(reference_mask, rendered_mask)
    ratio = ImageStat.Stat(difference).mean[0] / 255.0
    if ratio > VISUAL_DIFF_LIMIT:
        raise SelfTestError(
            f"rendered first-page typography/layout drift is {ratio:.3%}; limit is {VISUAL_DIFF_LIMIT:.3%}"
        )
    return ratio


def tamper_heading_font(source: Path, target: Path) -> None:
    with zipfile.ZipFile(source, "r") as archive:
        entries = {name: archive.read(name) for name in archive.namelist()}
    styles = entries["word/styles.xml"]
    if b"Libre Baskerville" not in styles:
        raise SelfTestError("valid DOCX unexpectedly lacks Libre Baskerville in styles.xml")
    entries["word/styles.xml"] = styles.replace(b"Libre Baskerville", b"Arial")
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in entries.items():
            archive.writestr(name, data)


def run_self_test(work_dir: Path, renderer: Path) -> dict[str, object]:
    bundle = work_dir / "valid-bundle"
    build_fixture(bundle)
    prepare = SCRIPTS_DIR / "prepare_bundle.py"
    builder = SCRIPTS_DIR / "build_publish_docx.py"
    verifier = SCRIPTS_DIR / "verify_publish_docx.py"
    positive = run([sys.executable, str(prepare), str(bundle)])
    result = json.loads(positive.stdout)
    if result.get("status") != "PASS":
        raise SelfTestError(f"positive fixture did not pass: {positive.stdout}")
    output_docx = work_dir / "self-test-final-upload.docx"
    run([sys.executable, str(builder), str(bundle), str(output_docx)])
    run([sys.executable, str(verifier), str(output_docx), "--bundle", str(bundle)])

    render_dir = work_dir / "rendered"
    run([sys.executable, str(renderer), str(output_docx), "--output_dir", str(render_dir)])
    page_one = render_dir / "page-1.png"
    if not page_one.is_file():
        raise SelfTestError("document renderer did not create page-1.png")
    visual_ratio = compare_rendered_first_page(page_one)

    invalid_docx = work_dir / "invalid-heading-font.docx"
    tamper_heading_font(output_docx, invalid_docx)
    invalid_docx_result = subprocess.run(
        [sys.executable, str(verifier), str(invalid_docx)], text=True, capture_output=True, check=False
    )
    if invalid_docx_result.returncode == 0 or "expected 'Libre Baskerville'" not in (
        invalid_docx_result.stdout + invalid_docx_result.stderr
    ):
        raise SelfTestError("verifier failed to reject a DOCX with a tampered heading font")

    invalid_bundle = work_dir / "invalid-bundle"
    shutil.copytree(bundle, invalid_bundle)
    invalid_meta = json.loads((invalid_bundle / "meta.json").read_text(encoding="utf-8"))
    invalid_meta.pop("editorialMode", None)
    (invalid_bundle / "meta.json").write_text(json.dumps(invalid_meta, indent=2) + "\n", encoding="utf-8")
    invalid_assets = json.loads((invalid_bundle / "image-assets.json").read_text(encoding="utf-8"))
    for asset in invalid_assets[:3]:
        asset["sourceType"] = "origin-owned"
    (invalid_bundle / "image-assets.json").write_text(
        json.dumps(invalid_assets, indent=2) + "\n", encoding="utf-8"
    )
    invalid_bundle_result = subprocess.run(
        [sys.executable, str(prepare), str(invalid_bundle)], text=True, capture_output=True, check=False
    )
    invalid_output = invalid_bundle_result.stdout + invalid_bundle_result.stderr
    if invalid_bundle_result.returncode == 0:
        raise SelfTestError("publication gate accepted a deliberately invalid bundle")
    for expected in ("editorialMode", "at least 60%"):
        if expected not in invalid_output:
            raise SelfTestError(f"invalid bundle rejection did not report {expected!r}")

    return {
        "status": "PASS",
        "skillVersion": SKILL_VERSION,
        "python": sys.executable,
        "renderer": str(renderer),
        "positiveBundleGate": "PASS",
        "docxBuildAndStructuralVerification": "PASS",
        "renderedPages": len(list(render_dir.glob("page-*.png"))),
        "firstPageVisualDiff": round(visual_ratio, 6),
        "tamperedDocxRejected": True,
        "invalidBundleRejected": True,
        "fontAssets": verify_font_assets(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--renderer", type=Path, help="Absolute path to the Codex documents render_docx.py")
    parser.add_argument("--work-dir", type=Path, help="Keep self-test artifacts in this empty/new directory")
    args = parser.parse_args()
    try:
        required_runtime()
        renderer = find_renderer(args.renderer)
        verify_font_assets()
        if args.work_dir:
            work_dir = args.work_dir.expanduser().resolve()
            work_dir.mkdir(parents=True, exist_ok=True)
            report = run_self_test(work_dir, renderer)
        else:
            with tempfile.TemporaryDirectory(prefix="origin-blog-self-test-") as temporary:
                report = run_self_test(Path(temporary), renderer)
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(
            json.dumps(
                {"status": "FAIL", "skillVersion": SKILL_VERSION, "error": str(exc)},
                indent=2,
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
