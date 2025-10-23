from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Type, TypeVar, Union

from sqlalchemy.orm import Query

from app.extensions import db

ModelType = TypeVar("ModelType", bound=db.Model)


def create_instance(
    model_cls: Type[ModelType],
    commit: bool = True,
    flush: bool = False,
    **attributes: Any,
) -> ModelType:
    """
    Generic helper to create and optionally persist a new model instance.
    """

    instance = model_cls(**attributes)
    db.session.add(instance)

    if flush:
        db.session.flush()

    if commit:
        db.session.commit()

    return instance


def get_instance(model_cls: Type[ModelType], instance_id: Any) -> Optional[ModelType]:
    """
    Fetch a single model instance by primary key.
    """

    if instance_id is None:
        return None

    return db.session.get(model_cls, instance_id)


def list_instances(
    model_cls: Type[ModelType],
    *,
    filters: Optional[Sequence[Any]] = None,
    order_by: Optional[Union[Any, Sequence[Any]]] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> List[ModelType]:
    """
    List model instances subject to optional filters, ordering, and paging.
    """

    query: Query = db.session.query(model_cls)

    if filters:
        for clause in filters:
            query = query.filter(clause)

    if order_by is not None:
        if isinstance(order_by, (list, tuple)):
            query = query.order_by(*order_by)
        else:
            query = query.order_by(order_by)

    if offset is not None:
        query = query.offset(offset)

    if limit is not None:
        query = query.limit(limit)

    return list(query)


def update_instance(
    instance: ModelType,
    commit: bool = True,
    flush: bool = False,
    **attributes: Any,
) -> ModelType:
    """
    Update attributes on an instance.  Attributes with value ``None`` are
    respected – callers should pre-filter if they need to skip ``None`` values.
    """

    for key, value in attributes.items():
        setattr(instance, key, value)

    if flush:
        db.session.flush()

    if commit:
        db.session.commit()

    return instance


def delete_instance(
    model_cls: Type[ModelType],
    instance_or_id: Union[ModelType, Any],
    commit: bool = True,
    flush: bool = False,
) -> None:
    """
    Delete a model instance by object or identifier.
    """

    if isinstance(instance_or_id, model_cls):
        instance = instance_or_id
    else:
        instance = get_instance(model_cls, instance_or_id)

    if instance is None:
        return

    db.session.delete(instance)

    if flush:
        db.session.flush()

    if commit:
        db.session.commit()
