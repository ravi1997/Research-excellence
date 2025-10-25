from __future__ import annotations

import json
from datetime import date
from typing import Dict, Iterable, Optional, Sequence

from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models.Cycle import Cycle, CyclePhase, CycleWindow
from app.security_utils import audit_log
from app.utils.logging_utils import get_logger, log_context

from .base import (
    _sanitize_payload,
    _serialize_value,
    create_instance,
    delete_instance,
    get_instance,
    list_instances,
    update_instance,
)

logger = get_logger("cycle_utils")


def _audit(event: str, actor_id: Optional[str], payload: Dict[str, object]) -> None:
    try:
        audit_log(
            event,
            user_id=str(actor_id) if actor_id is not None else None,
            detail=json.dumps(payload, default=_serialize_value),
        )
    except Exception:
        logger.exception("Failed to record audit event", extra={"event": event})


def create_cycle(
    commit: bool = True,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
    **attributes,
) -> Cycle:
    ctx = {"function": "create_cycle", **(context or {})}
    sanitized = _sanitize_payload(attributes)
    with log_context(module="cycle_utils", action="create_cycle", actor_id=actor_id):
        logger.info("create_cycle invoked commit=%s attributes=%s", commit, sanitized)
    cycle = create_instance(
        Cycle,
        commit=commit,
        actor_id=actor_id,
        event_name="cycle.create",
        context=ctx,
        **attributes,
    )
    logger.info("create_cycle completed id=%s", _serialize_value(getattr(cycle, "id", None)))
    return cycle


def get_cycle_by_id(
    cycle_id,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> Optional[Cycle]:
    ctx = {"function": "get_cycle_by_id", **(context or {})}
    with log_context(module="cycle_utils", action="get_cycle_by_id", actor_id=actor_id):
        logger.info("get_cycle_by_id requested id=%s", _serialize_value(cycle_id))
    cycle = get_instance(
        Cycle,
        cycle_id,
        actor_id=actor_id,
        event_name="cycle.get",
        context=ctx,
    )
    logger.info(
        "get_cycle_by_id resolved id=%s found=%s",
        _serialize_value(cycle_id),
        cycle is not None,
    )
    return cycle


def list_cycles(
    *,
    include_windows: bool = False,
    filters: Optional[Sequence] = None,
    order_by=None,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> Sequence[Cycle]:
    options = [joinedload(Cycle.windows)] if include_windows else None
    ctx = {
        "function": "list_cycles",
        "include_windows": include_windows,
        **(context or {}),
    }
    results = list_instances(
        Cycle,
        filters=filters,
        order_by=order_by,
        query_options=options,
        actor_id=actor_id,
        event_name="cycle.list",
        context=ctx,
    )
    with log_context(module="cycle_utils", action="list_cycles", actor_id=actor_id):
        logger.info(
            "list_cycles completed include_windows=%s count=%s",
            include_windows,
            len(results),
        )
    return results


def update_cycle(
    cycle: Cycle,
    commit: bool = True,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
    **attributes,
) -> Cycle:
    ctx = {
        "function": "update_cycle",
        "cycle_id": _serialize_value(getattr(cycle, "id", None)),
        **(context or {}),
    }
    sanitized = _sanitize_payload(attributes)
    with log_context(module="cycle_utils", action="update_cycle", actor_id=actor_id):
        logger.info("update_cycle target_id=%s attributes=%s", ctx.get("cycle_id"), sanitized)
    updated = update_instance(
        cycle,
        commit=commit,
        actor_id=actor_id,
        event_name="cycle.update",
        context=ctx,
        **attributes,
    )
    logger.info("update_cycle complete target_id=%s", ctx.get("cycle_id"))
    return updated


def delete_cycle(
    cycle_or_id,
    commit: bool = True,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> None:
    ctx = {"function": "delete_cycle", **(context or {})}
    with log_context(module="cycle_utils", action="delete_cycle", actor_id=actor_id):
        logger.info("delete_cycle requested target=%s", _serialize_value(cycle_or_id))
    delete_instance(
        Cycle,
        cycle_or_id,
        commit=commit,
        actor_id=actor_id,
        event_name="cycle.delete",
        context=ctx,
    )
    logger.info("delete_cycle completed target=%s", _serialize_value(cycle_or_id))


def create_window(
    *,
    cycle_id,
    phase: CyclePhase,
    start_date,
    end_date,
    commit: bool = True,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> CycleWindow:
    ctx = {
        "function": "create_window",
        "cycle_id": _serialize_value(cycle_id),
        "phase": phase.name if isinstance(phase, CyclePhase) else _serialize_value(phase),
        **(context or {}),
    }
    with log_context(module="cycle_utils", action="create_window", actor_id=actor_id):
        logger.info(
            "create_window cycle_id=%s phase=%s start=%s end=%s",
            _serialize_value(cycle_id),
            phase,
            start_date,
            end_date,
        )
    window = create_instance(
        CycleWindow,
        commit=commit,
        actor_id=actor_id,
        event_name="cycle.window.create",
        context=ctx,
        cycle_id=cycle_id,
        phase=phase,
        start_date=start_date,
        end_date=end_date,
    )
    logger.info("create_window completed id=%s", _serialize_value(getattr(window, "id", None)))
    return window


def list_windows(
    *,
    cycle_id=None,
    phase: Optional[CyclePhase] = None,
    reference_date: Optional[date] = None,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> Sequence[CycleWindow]:
    filters = []
    if cycle_id is not None:
        filters.append(CycleWindow.cycle_id == cycle_id)
    if phase is not None:
        filters.append(CycleWindow.phase == phase)
    if reference_date is not None:
        filters.extend(
            (
                CycleWindow.start_date <= reference_date,
                CycleWindow.end_date >= reference_date,
            )
        )
    results = list_instances(
        CycleWindow,
        filters=filters,
        order_by=(CycleWindow.start_date.asc(),),
        actor_id=actor_id,
        event_name="cycle.window.list",
        context={"function": "list_windows", **(context or {})},
    )
    with log_context(module="cycle_utils", action="list_windows", actor_id=actor_id):
        logger.info(
            "list_windows completed cycle_id=%s phase=%s reference_date=%s count=%s",
            _serialize_value(cycle_id),
            phase,
            reference_date,
            len(results),
        )
    return results


def getActiveCycleForSubmission(
    reference_date: Optional[date] = None,
    *,
    eager_load_windows: bool = True,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> Optional[Cycle]:
    """
    Return the first cycle that has an active submission window for the given
    reference date.  By default the submission windows are eagerly loaded to
    avoid lazy-load penalties when the caller inspects the active periods.
    """

    if reference_date is None:
        reference_date = date.today()

    query = (
        db.session.query(Cycle)
        .join(CycleWindow, CycleWindow.cycle_id == Cycle.id)
        .filter(
            CycleWindow.phase == CyclePhase.SUBMISSION,
            CycleWindow.start_date <= reference_date,
            CycleWindow.end_date >= reference_date,
        )
        .order_by(CycleWindow.start_date.asc(), Cycle.name.asc())
    )

    if eager_load_windows:
        query = query.options(joinedload(Cycle.submission_windows))

    with log_context(module="cycle_utils", action="getActiveCycleForSubmission", actor_id=actor_id):
        logger.info(
            "getActiveCycleForSubmission reference_date=%s eager=%s",
            reference_date,
            eager_load_windows,
        )
        cycle = query.first()
        found_id = _serialize_value(getattr(cycle, "id", None)) if cycle else None
        logger.info("getActiveCycleForSubmission result_id=%s", found_id)
        _audit(
            "cycle.active_submission.lookup",
            actor_id,
            {
                "operation": "getActiveCycleForSubmission",
                "reference_date": _serialize_value(reference_date),
                "found_cycle_id": found_id,
                "eager_load_windows": eager_load_windows,
            },
        )
        return cycle


def list_active_cycles_by_phase(
    phase: CyclePhase,
    reference_date: Optional[date] = None,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> Sequence[Cycle]:
    if reference_date is None:
        reference_date = date.today()

    query = (
        db.session.query(Cycle)
        .join(CycleWindow, CycleWindow.cycle_id == Cycle.id)
        .filter(
            CycleWindow.phase == phase,
            CycleWindow.start_date <= reference_date,
            CycleWindow.end_date >= reference_date,
        )
        .order_by(CycleWindow.start_date.asc())
    )

    with log_context(module="cycle_utils", action="list_active_cycles_by_phase", actor_id=actor_id):
        logger.info(
            "list_active_cycles_by_phase phase=%s reference_date=%s",
            phase,
            reference_date,
        )
        results = query.all()
        logger.info("list_active_cycles_by_phase count=%s", len(results))
        _audit(
            "cycle.active_by_phase",
            actor_id,
            {
                "operation": "list_active_cycles_by_phase",
                "phase": phase.name if isinstance(phase, CyclePhase) else _serialize_value(phase),
                "reference_date": _serialize_value(reference_date),
                "count": len(results),
            },
        )
        return results
