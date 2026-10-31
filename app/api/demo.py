"""
GET /api/demo/{source_type}  — serves synthetic seed CSV files for frontend testing.

?masked=true  (default): PII columns replaced with HMAC tokens.
?masked=false           : plaintext (demo/dev only; all data is synthetic).
"""
import csv
import io
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.masking import mask

router = APIRouter(tags=["demo"])

_DEMO_DIR = Path(__file__).parent.parent / "demo_data"

_PII_COLUMNS: dict[str, list[str]] = {
    "customers_accounts": ["name", "phone", "email", "address", "identity_number"],
    "transactions":       ["beneficiary_name"],
    "login_events":       ["ip_address"],
    "loan_applications":  ["phone", "address"],
    "insurance_claims":   ["description"],
}

_VALID_SOURCES = set(_PII_COLUMNS.keys())


@router.get("/demo/{source_type}")
async def get_demo_data(
    source_type: str,
    masked: bool = Query(True, description="Mask PII columns"),
):
    if source_type not in _VALID_SOURCES:
        raise HTTPException(
            404,
            detail=f"Unknown source_type '{source_type}'. "
                   f"Valid: {sorted(_VALID_SOURCES)}",
        )

    csv_path = _DEMO_DIR / f"{source_type}.csv"
    if not csv_path.exists():
        raise HTTPException(500, detail=f"Demo file missing for '{source_type}'")

    raw = csv_path.read_text(encoding="utf-8")

    if not masked:
        return StreamingResponse(
            io.StringIO(raw),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{source_type}.csv"'},
        )

    pii_cols = set(_PII_COLUMNS.get(source_type, []))
    reader = csv.DictReader(io.StringIO(raw))
    assert reader.fieldnames is not None
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=reader.fieldnames, lineterminator="\n")
    writer.writeheader()
    for row in reader:
        for col in pii_cols:
            if col in row and row[col]:
                row[col] = mask(row[col], col)
        writer.writerow(row)

    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{source_type}_masked.csv"'},
    )
