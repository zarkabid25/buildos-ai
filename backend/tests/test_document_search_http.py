"""BUILD-076/077/080: text extraction, chunking and keyword search inside documents."""

import io
import json
import uuid
import zipfile

from app.services.document_text import CHUNK_TARGET, chunk, extract

DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def make_pdf(pages: list[str]) -> bytes:
    """A real PDF with a text layer (Helvetica, one line per page), built by hand."""
    objects = ["<< /Type /Catalog /Pages 2 0 R >>", None, "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    kids = []
    for text in pages:
        stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
        objects.append(f"<< /Length {len(stream)} >>\nstream\n{stream.decode()}\nendstream")
        content_no = len(objects)
        objects.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents {content_no} 0 R /Resources << /Font << /F1 3 0 R >> >> >>")
        kids.append(f"{len(objects)} 0 R")
    objects[1] = f"<< /Type /Pages /Kids [{' '.join(kids)}] /Count {len(kids)} >>"
    out, offsets = io.BytesIO(), []
    out.write(b"%PDF-1.4\n")
    for i, obj in enumerate(objects, start=1):
        offsets.append(out.tell())
        out.write(f"{i} 0 obj\n{obj}\nendobj\n".encode())
    xref = out.tell()
    out.write(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    for off in offsets:
        out.write(f"{off:010d} 00000 n \n".encode())
    out.write(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode())
    return out.getvalue()


def make_docx(paragraphs: list[str]) -> bytes:
    body = "".join(f"<w:p><w:r><w:t>{p}</w:t></w:r></w:p>" for p in paragraphs)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("[Content_Types].xml", "<Types/>")
        z.writestr("word/document.xml",
                   f'<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>{body}</w:body></w:document>')
    return buf.getvalue()


def make_xlsx(rows: list[list[str]]) -> bytes:
    ns = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
    strings = sorted({c for r in rows for c in r})
    sst = "".join(f"<si><t>{s}</t></si>" for s in strings)
    sheet = "".join(
        "<row>" + "".join(f'<c t="s"><v>{strings.index(c)}</v></c>' for c in r) + "</row>" for r in rows
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("xl/workbook.xml", f"<workbook {ns}/>")
        z.writestr("xl/sharedStrings.xml", f"<sst {ns}>{sst}</sst>")
        z.writestr("xl/worksheets/sheet1.xml", f"<worksheet {ns}><sheetData>{sheet}</sheetData></worksheet>")
    return buf.getvalue()


def upload(client, headers, content, content_type, name, title, project_id=None):
    data = {"title": title, "category": "contract"}
    if project_id:
        data["project_id"] = project_id
    res = client.post("/api/v1/documents", headers=headers, data=data, files={"file": (name, io.BytesIO(content), content_type)})
    assert res.status_code == 201, res.text
    return res.json()


def search(client, headers, q, **params):
    res = client.get("/api/v1/documents/search", headers=headers, params={"q": q, **params})
    assert res.status_code == 200, res.text
    return res.json()


# ---- Extraction and chunking (no HTTP) -------------------------------------------


def test_extract_each_format():
    pdf = extract("application/pdf", make_pdf(["Retention money is five percent", "Liquidated damages apply"]))
    assert pdf.status == "indexed" and pdf.page_count == 2
    assert [p for p, _ in pdf.pages] == [1, 2] and "Liquidated damages" in pdf.pages[1][1]
    assert "Concrete grade M25" in extract(DOCX, make_docx(["Scope", "Concrete grade M25"])).pages[0][1]
    assert "Cement | 500 bags" in extract(XLSX, make_xlsx([["Cement", "500 bags"]])).pages[0][1]
    assert "Café" in extract("text/csv", "item,note\nx,Café\n".encode("cp1252")).pages[0][1]


def test_extract_reports_what_it_cannot_read():
    assert extract("image/png", b"\x89PNG\r\n\x1a\n").status == "unsupported"
    assert extract("application/msword", b"\xd0\xcf\x11\xe0").status == "unsupported"
    assert extract("application/pdf", make_pdf([""])).status == "no_text"  # e.g. a scan
    assert extract(DOCX, b"PK\x03\x04 broken").status == "failed"


def test_chunking_keeps_pages_and_overlaps():
    sentence = "The contractor shall maintain the works. "
    long_text = sentence * 80  # ~3200 chars
    passages = chunk([(3, long_text), (4, "Short page.")])
    assert len(passages) > 3
    assert all(len(text) <= CHUNK_TARGET for _, text in passages)
    assert {p for p, _ in passages} == {3, 4} and passages[-1] == (4, "Short page.")
    # Consecutive passages share some text, so a phrase across a boundary isn't lost.
    first, second = passages[0][1], passages[1][1]
    assert second[:30] in first
    # Nothing dropped: every sentence-start position is covered.
    assert "".join(t for p, t in passages if p == 3).count("contractor") >= 80


# ---- Upload, search, delete -----------------------------------------------------------


def test_upload_indexes_and_search_finds_passage_with_page(client, auth_a):
    doc = upload(client, auth_a, make_pdf(["General conditions", "Retention money is five percent of each bill"]),
                 "application/pdf", "contract.pdf", "Main contract")
    assert (doc["text_status"], doc["page_count"]) == ("indexed", 2)

    [hit] = search(client, auth_a, "retention money")
    assert (hit["document_id"], hit["title"], hit["page"]) == (doc["id"], "Main contract", 2)
    assert "five percent" in hit["snippet"]


def test_all_words_must_match_and_case_is_ignored(client, auth_a):
    upload(client, auth_a, make_docx(["Concrete grade M25 for slabs"]), DOCX, "spec.docx", "Spec")
    assert len(search(client, auth_a, "CONCRETE slabs")) == 1
    assert search(client, auth_a, "concrete steel") == []


def test_exact_phrase_ranks_first(client, auth_a):
    upload(client, auth_a, make_docx(["damages may be liquidated later"]), DOCX, "a.docx", "Scattered")
    upload(client, auth_a, make_docx(["liquidated damages of 0.1% per day"]), DOCX, "b.docx", "Phrase")
    assert [h["title"] for h in search(client, auth_a, "liquidated damages")] == ["Phrase", "Scattered"]


def test_project_filter(client, auth_a):
    tower = client.post("/api/v1/projects", headers=auth_a, json={"name": "Tower", "code": "TWR", "budget": "1"}).json()
    upload(client, auth_a, make_docx(["waterproofing membrane"]), DOCX, "t.docx", "Tower spec", tower["id"])
    upload(client, auth_a, make_docx(["waterproofing membrane"]), DOCX, "o.docx", "Office spec")
    assert len(search(client, auth_a, "waterproofing")) == 2
    assert [h["title"] for h in search(client, auth_a, "waterproofing", project_id=tower["id"])] == ["Tower spec"]


def test_unsupported_and_textless_uploads_still_succeed(client, auth_a):
    img = upload(client, auth_a, b"\x89PNG\r\n\x1a\n" + b"\x00" * 32, "image/png", "site.png", "Photo")
    assert img["text_status"] == "unsupported"
    scan = upload(client, auth_a, make_pdf([""]), "application/pdf", "scan.pdf", "Scanned drawing")
    assert scan["text_status"] == "no_text"


def test_wildcards_are_literal(client, auth_a):
    upload(client, auth_a, make_docx(["column_c1 and columnXc1"]), DOCX, "w.docx", "W")
    [hit] = search(client, auth_a, "column_c1")
    assert hit["title"] == "W"
    upload(client, auth_a, make_docx(["only columnXc1 here"]), DOCX, "x.docx", "X")
    # "_" must not act as a single-character wildcard and match columnXc1 on its own.
    assert [h["title"] for h in search(client, auth_a, "column_c1")] == ["W"]


def test_delete_removes_passages(client, auth_a):
    doc = upload(client, auth_a, make_docx(["unique phrase zebracrossing"]), DOCX, "z.docx", "Z")
    assert len(search(client, auth_a, "zebracrossing")) == 1
    assert client.delete(f"/api/v1/documents/{doc['id']}", headers=auth_a).status_code == 204
    assert search(client, auth_a, "zebracrossing") == []


def test_reindex(client, auth_a, viewer_a):
    doc = upload(client, auth_a, make_docx(["piling depth 18 metres"]), DOCX, "p.docx", "Piling")
    assert client.post(f"/api/v1/documents/{doc['id']}/reindex", headers=viewer_a).status_code == 403
    res = client.post(f"/api/v1/documents/{doc['id']}/reindex", headers=auth_a)
    assert res.status_code == 200 and res.json()["text_status"] == "indexed"
    assert len(search(client, auth_a, "piling depth")) == 1  # re-indexing doesn't duplicate passages


def test_search_is_tenant_isolated(client, auth_a, auth_b):
    upload(client, auth_a, make_docx(["confidential tender price"]), DOCX, "c.docx", "Secret")
    assert search(client, auth_b, "confidential tender") == []
    assert client.get("/api/v1/documents/search", headers=auth_b, params={"q": "x"}).status_code == 422


def test_assistant_tool_searches_documents(client, auth_a, auth_b):
    from app.ai.tools import ToolContext, run_tool
    from app.db.session import SessionLocal
    from app.models.user import User

    upload(client, auth_a, make_pdf(["Defects liability period is twelve months"]), "application/pdf", "c.pdf", "Contract")
    for headers, expected in ((auth_a, 1), (auth_b, 0)):
        user_id = uuid.UUID(client.get("/api/v1/auth/me", headers=headers).json()["id"])
        with SessionLocal() as db:
            user = db.get(User, user_id)
            text, is_error = run_tool(ToolContext(db=db, company_id=user.company_id, user=user), "search_documents",
                                      {"query": "defects liability"})
        assert not is_error
        result = json.loads(text)
        assert len(result["items"]) == expected
        if expected:
            assert result["items"][0]["title"] == "Contract" and result["items"][0]["page"] == 1
