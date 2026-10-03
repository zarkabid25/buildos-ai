"""Extract text from documents uploaded before search existed (BUILD-076).

New uploads are indexed automatically; this catches up the rest. Safe to re-run:
only documents never indexed are processed unless --all is given.

    cd backend
    .venv\\Scripts\\python.exe scripts\\index_documents.py          # only not-yet-indexed
    .venv\\Scripts\\python.exe scripts\\index_documents.py --all    # rebuild everything
"""

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import models  # noqa: E402,F401
from app.db.session import SessionLocal  # noqa: E402
from app.models.document import Document  # noqa: E402
from app.services.document_service import index_document  # noqa: E402


def main() -> None:
    rebuild_all = "--all" in sys.argv
    outcomes: Counter[str] = Counter()
    with SessionLocal() as db:
        query = db.query(Document)
        if not rebuild_all:
            query = query.filter(Document.text_status.is_(None))
        for document in query.yield_per(50):
            index_document(db, document)
            db.commit()
            outcomes[document.text_status or "unknown"] += 1
    total = sum(outcomes.values())
    print(f"Processed {total} document(s): " + (", ".join(f"{n} {s}" for s, n in sorted(outcomes.items())) or "nothing to do"))


if __name__ == "__main__":
    main()
