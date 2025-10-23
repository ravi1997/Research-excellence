from __future__ import annotations

from datetime import date
from typing import Iterable, Optional, Sequence

from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models.Cycle import Cycle, CyclePhase, CycleWindow

from .base import (
    create_instance,
    delete_instance,
    get_instance,
    list_instances,
    update_instance,
)


def create_cycle(commit: bool = True, **attributes) -> Cycle:
    return create_instance(Cycle, commit=commit, **attributes)


def get_cycle_by_id(cycle_id) -> Optional[Cycle]:
    return get_instance(Cycle, cycle_id)


def list_cycles(
    *,
    include_windows: bool = False,
    filters: Optional[Sequence] = None,
    order_by=None,
) -> Sequence[Cycle]:
    query = db.session.query(Cycle)
    if include_windows:
        query = query.options(joinedload(Cycle.windows))

    if filters:
        for clause in filters:
            query = query.filter(clause)

    if order_by is not None:
        if isinstance(order_by, (list, tuple)):
            query = query.order_by(*order_by)
        else:
            query = query.order_by(order_by)

    return query.all()


def update_cycle(cycle: Cycle, commit: bool = True, **attributes) -> Cycle:
    return update_instance(cycle, commit=commit, **attributes)


def delete_cycle(cycle_or_id, commit: bool = True) -> None:
    delete_instance(Cycle, cycle_or_id, commit=commit)


def create_window(
    *,
    cycle_id,
    phase: CyclePhase,
    start_date,
    end_date,
    commit: bool = True,
) -> CycleWindow:
    return create_instance(
        CycleWindow,
        commit=commit,
        cycle_id=cycle_id,
        phase=phase,
        start_date=start_date,
        end_date=end_date,
    )


def list_windows(
    *,
    cycle_id=None,
    phase: Optional[CyclePhase] = None,
    reference_date: Optional[date] = None,
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
    return list_instances(
        CycleWindow,
        filters=filters,
        order_by=(CycleWindow.start_date.asc(),),
    )


def getActiveCycleForSubmission(
    reference_date: Optional[date] = None,
    *,
    eager_load_windows: bool = True,
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

    return query.first()


def list_active_cycles_by_phase(
    phase: CyclePhase,
    reference_date: Optional[date] = None,
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
    return query.all()
