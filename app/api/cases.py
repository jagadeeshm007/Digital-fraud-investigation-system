"""Investigation workspace endpoints (Level 2). PermissionDenied reaches the global handler (403)."""
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import cases as svc
from app.audit import write_audit
from app.db import get_session
from app.models import Recommendation
from app.permissions import check_permission, resolve_role, resolve_user

router = APIRouter(tags=["investigation"])


class _Who:
    def __init__(self, x_role: str | None = Header(default=None, alias="X-Role"),
                 x_user: str | None = Header(default=None, alias="X-User")):
        self.role = resolve_role(x_role)
        self.user = resolve_user(x_user, self.role)


class SplitRequest(BaseModel):
    alert_id: str
    reason: str


class NoteRequest(BaseModel):
    body: str


class RiskRequest(BaseModel):
    risk_level: str
    reason: str


class RecommendationDecision(BaseModel):
    approve: bool
    reason: str


class OpenCaseRequest(BaseModel):
    reason: str


def _http(e: svc.CaseError) -> HTTPException:
    return HTTPException(e.status, detail=e.detail)


@router.post("/cases/{case_id}/split")
async def split_case(case_id: str, body: SplitRequest, who: _Who = Depends(),
                     session: AsyncSession = Depends(get_session)):
    try:
        new = await svc.split_alert(session, case_id, body.alert_id, body.reason, who.role, who.user, "api")
    except svc.CaseError as e:
        raise _http(e)
    return {"new_case": svc.case_dict(new), "original_case_id": case_id}


@router.post("/cases/{case_id}/notes")
async def add_note(case_id: str, body: NoteRequest, who: _Who = Depends(),
                   session: AsyncSession = Depends(get_session)):
    try:
        note = await svc.add_note(session, case_id, body.body, who.role, who.user, "api")
    except svc.CaseError as e:
        raise _http(e)
    return svc.note_dict(note)


@router.patch("/cases/{case_id}/risk")
async def override_risk(case_id: str, body: RiskRequest, who: _Who = Depends(),
                        session: AsyncSession = Depends(get_session)):
    try:
        case = await svc.override_risk(session, case_id, body.risk_level, body.reason, who.role, who.user, "api")
    except svc.CaseError as e:
        raise _http(e)
    return svc.case_dict(case)


@router.get("/cases/{case_id}/report")
async def case_report(case_id: str, who: _Who = Depends(), session: AsyncSession = Depends(get_session)):
    check_permission(who.role, "view_cases")
    try:
        case = await svc.get_case_or_404(session, case_id)
    except svc.CaseError as e:
        raise _http(e)
    report = await svc.build_report(session, case)
    await write_audit(session, who.role, "api", "download_case_report", case_id, "ok", who.user)
    await session.commit()
    return JSONResponse(report, headers={
        "Content-Disposition": f'attachment; filename="case-{case_id[:8]}-report.json"'})


@router.get("/recommendations")
async def list_recommendations(status: str | None = Query(default="pending"), who: _Who = Depends(),
                               session: AsyncSession = Depends(get_session)):
    check_permission(who.role, "view_cases")
    q = select(Recommendation).order_by(Recommendation.created_at.desc())
    if status:
        q = q.where(Recommendation.status == status)
    rows = (await session.execute(q.limit(200))).scalars().all()
    return {"items": [svc.recommendation_dict(r) for r in rows]}


@router.post("/recommendations/{recommendation_id}/decision")
async def decide_recommendation(recommendation_id: str, body: RecommendationDecision, who: _Who = Depends(),
                                session: AsyncSession = Depends(get_session)):
    try:
        rec = await svc.decide_recommendation(session, recommendation_id, body.approve, body.reason,
                                              who.role, who.user, "api")
    except svc.CaseError as e:
        raise _http(e)
    return svc.recommendation_dict(rec)


@router.post("/alerts/{alert_id}/case")
async def open_case(alert_id: str, body: OpenCaseRequest, who: _Who = Depends(),
                    session: AsyncSession = Depends(get_session)):
    try:
        case = await svc.open_case_from_alert(session, alert_id, body.reason, who.role, who.user, "api")
    except svc.CaseError as e:
        raise _http(e)
    return svc.case_dict(case)
