from __future__ import annotations

import json
import logging
import os
import zipfile
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from flask import Flask, current_app


_CORE_LOG_RECORD_FIELDS = {
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
}

_log_context: ContextVar[Dict[str, Any]] = ContextVar("log_context", default={})


def _resolve_app() -> Optional[Flask]:
    try:
        return current_app._get_current_object()  # type: ignore[attr-defined]
    except RuntimeError:
        return None


def _resolve_app_logger() -> Optional[logging.Logger]:
    app = _resolve_app()
    if app:
        return app.logger
    return None


def get_log_context() -> Dict[str, Any]:
    """Return a shallow copy of the active contextual logging fields."""

    return dict(_log_context.get())


def set_log_context(context: Dict[str, Any]) -> None:
    """Replace the active contextual logging fields."""

    _log_context.set(dict(context or {}))


def update_log_context(**fields: Any) -> None:
    """Merge additional fields into the active contextual logging fields."""

    current = dict(_log_context.get())
    for key, value in fields.items():
        if value is None:
            current.pop(key, None)
        else:
            current[key] = value
    _log_context.set(current)


def clear_log_context(*keys: str) -> None:
    """Clear specific contextual keys, or all if none provided."""

    if not keys:
        _log_context.set({})
        return
    current = dict(_log_context.get())
    for key in keys:
        current.pop(key, None)
    _log_context.set(current)


@contextmanager
def log_context(**fields: Any):
    """Context manager that temporarily adds contextual logging fields."""

    current = dict(_log_context.get())
    updated = current.copy()
    updated.update({k: v for k, v in fields.items() if v is not None})
    token = _log_context.set(updated)
    try:
        yield
    finally:
        _log_context.reset(token)


class ContextAwareFormatter(logging.Formatter):
    """Formatter that can emit JSON or text logs enriched with contextual fields."""

    def __init__(
        self,
        fmt: Optional[str] = None,
        datefmt: Optional[str] = None,
        *,
        json_format: bool = False,
        static_fields: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(fmt=fmt or "[%(asctime)s] %(levelname)s %(name)s - %(message)s", datefmt=datefmt)
        self.json_format = json_format
        self.static_fields = dict(static_fields or {})

    def format(self, record: logging.LogRecord) -> str:
        if self.json_format:
            return self._format_json(record)

        base = super().format(record)
        context = _log_context.get()
        if context:
            ctx = " ".join(f"{key}={value}" for key, value in sorted(context.items()))
            base = f"{base} | {ctx}"
        return base

    def _format_json(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        payload.update(self.static_fields)

        for key, value in record.__dict__.items():
            if key in _CORE_LOG_RECORD_FIELDS or key.startswith("_") or key in payload:
                continue
            payload[key] = value

        context = _log_context.get()
        if context:
            payload.setdefault("context", {}).update(context)

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack"] = self.formatStack(record.stack_info)

        return json.dumps(payload, default=str, separators=(",", ":"))


@dataclass(frozen=True)
class LogCategory:
    """Supported logical logging categories."""

    name: str
    filename: str


DEFAULT_CATEGORIES: Dict[str, LogCategory] = {
    "registration": LogCategory("registration", "registration.log"),
    "auth": LogCategory("auth", "auth.log"),
    "otp": LogCategory("otp", "otp.log"),
    "mail": LogCategory("mail", "mail.log"),
    "submission": LogCategory("submission", "submission.log"),
    "route": LogCategory("route", "route.log"),
    "app": LogCategory("app", "application.log"),
    "error": LogCategory("error", "errors.log"),
    "exception": LogCategory("exception", "exceptions.log"),
    "activity": LogCategory("activity", "activity.log"),
}


class LoggerManager:
    """
    Manages per-category loggers with timed rotation, contextual support,
    optional console output, and archival utilities.
    """

    def __init__(
        self,
        *,
        base_dir: Optional[str] = None,
        rotation_when: str = "midnight",
        rotation_interval: int = 1,
        backup_count: Optional[int] = None,
        archive_dir: Optional[str] = None,
        auto_archive_after_days: Optional[int] = None,
        archive_check_interval_hours: int = 6,
        categories: Optional[Dict[str, LogCategory]] = None,
        enable_category_files: bool = True,
        mirror_app_handlers: bool = True,
        auto_archive_enabled: bool = True,
        default_level: int = logging.INFO,
        category_levels: Optional[Dict[str, int]] = None,
        enable_console: bool = True,
        console_level: Optional[int] = None,
        console_json: bool = False,
        json_format: bool = False,
        text_format: Optional[str] = None,
        date_format: Optional[str] = None,
        file_handler_level: Optional[int] = None,
        static_fields: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._base_dir = base_dir
        self._rotation_when = rotation_when
        self._rotation_interval = rotation_interval
        self._backup_count = backup_count if backup_count is not None else 7
        self._archive_dir = archive_dir
        self._auto_archive_after_days = auto_archive_after_days
        self._archive_check_interval = timedelta(hours=archive_check_interval_hours)
        self._categories = (categories or DEFAULT_CATEGORIES).copy()
        self._enable_category_files = enable_category_files
        self._mirror_app_handlers = mirror_app_handlers
        self._auto_archive_enabled = auto_archive_enabled
        self._default_level = default_level
        self._category_levels = {k.lower(): v for k, v in (category_levels or {}).items()}
        self._enable_console = enable_console
        self._console_level = console_level if console_level is not None else default_level
        self._console_json = console_json
        self._json_format = json_format
        self._text_format = text_format
        self._date_format = date_format
        self._file_handler_level = file_handler_level
        self._static_fields = dict(static_fields or {})
        self._loggers: Dict[str, logging.Logger] = {}
        self._last_archive_check: Optional[datetime] = None
        self._console_handler: Optional[logging.Handler] = None

    @property
    def base_dir(self) -> Path:
        if self._base_dir:
            return Path(self._base_dir)
        app = _resolve_app()
        if app:
            cfg_dir = app.config.get("LOGGING_BASE_DIR")
            if cfg_dir:
                return Path(cfg_dir)
        return Path(os.getenv("LOGGING_BASE_DIR", "/tmp/research_excellence_logs"))

    @property
    def archive_dir(self) -> Path:
        if self._archive_dir:
            return Path(self._archive_dir)
        return self.base_dir / "archive"

    def register_category(self, name: str, filename: Optional[str] = None) -> LogCategory:
        """Register a new logging category (idempotent)."""

        key = name.strip().lower()
        spec = LogCategory(key, filename or f"{key}.log")
        existing = self._categories.get(key)
        if existing and existing.filename != spec.filename:
            self._detach_logger(key)
        self._categories[key] = spec
        return spec

    def get_logger(self, category: str) -> logging.Logger:
        if not self._enable_category_files:
            return _resolve_app_logger() or logging.getLogger("app")

        category_key = category.lower()
        if category_key in self._loggers:
            return self._loggers[category_key]

        spec = self._categories.get(category_key)
        if spec is None:
            spec = self.register_category(category)

        logger_name = f"app.{spec.name}"
        logger = logging.getLogger(logger_name)
        logger.propagate = False
        level = self._category_levels.get(category_key, self._default_level)
        logger.setLevel(level)

        log_dir = self.base_dir
        log_dir.mkdir(parents=True, exist_ok=True)
        file_path = log_dir / spec.filename

        handler = TimedRotatingFileHandler(
            file_path,
            when=self._rotation_when,
            interval=self._rotation_interval,
            backupCount=self._backup_count,
            encoding="utf-8",
            utc=True,
        )
        handler_level = self._file_handler_level or level
        handler.setLevel(handler_level)
        handler.setFormatter(self._build_formatter(json_format=self._json_format))
        logger.addHandler(handler)

        if self._enable_console:
            console_handler = self._ensure_console_handler()
            if console_handler not in logger.handlers:
                logger.addHandler(console_handler)

        app_logger = _resolve_app_logger()
        if self._mirror_app_handlers and app_logger and app_logger.handlers:
            for app_handler in app_logger.handlers:
                if app_handler not in logger.handlers:
                    logger.addHandler(app_handler)

        self._loggers[category_key] = logger
        self._maybe_auto_archive()
        return logger

    def _build_formatter(self, *, json_format: bool) -> ContextAwareFormatter:
        return ContextAwareFormatter(
            fmt=self._text_format,
            datefmt=self._date_format,
            json_format=json_format,
            static_fields=self._static_fields,
        )

    def _ensure_console_handler(self) -> logging.Handler:
        if self._console_handler is None:
            handler = logging.StreamHandler()
            handler.setLevel(self._console_level)
            handler.setFormatter(self._build_formatter(json_format=self._console_json))
            self._console_handler = handler
        return self._console_handler

    def _maybe_auto_archive(self) -> None:
        if not self._auto_archive_enabled or self._auto_archive_after_days is None:
            return

        now = datetime.now(timezone.utc)
        if (
            self._last_archive_check is not None
            and now - self._last_archive_check < self._archive_check_interval
        ):
            return

        self.archive_logs(older_than_days=self._auto_archive_after_days)
        self._last_archive_check = now

    def _iter_log_files(self, categories: Optional[Iterable[str]] = None) -> Sequence[Path]:
        log_dir = self.base_dir
        if not log_dir.exists():
            return []

        if categories is None:
            return list(sorted(log_dir.glob("*.log*")))

        matched: List[Path] = []
        for category in categories:
            spec = self._categories.get(category.lower())
            if spec is None:
                continue
            base = log_dir / spec.filename
            matched.extend(sorted(base.parent.glob(f"{base.name}*")))
        return matched

    def clear_log(self, category: str) -> List[Path]:
        self._detach_logger(category.lower())

        deleted: List[Path] = []
        for path in self._iter_log_files([category]):
            try:
                path.unlink()
                deleted.append(path)
            except FileNotFoundError:
                continue
        return deleted

    def clear_all_logs(self) -> List[Path]:
        for key in list(self._loggers.keys()):
            self._detach_logger(key)

        deleted: List[Path] = []
        for path in self._iter_log_files():
            try:
                path.unlink()
                deleted.append(path)
            except FileNotFoundError:
                continue
        return deleted

    def archive_logs(
        self,
        *,
        older_than_days: int,
        destination_dir: Optional[str] = None,
    ) -> List[Path]:
        if older_than_days < 0:
            raise ValueError("older_than_days must be non-negative")

        dest_dir = Path(destination_dir) if destination_dir else self.archive_dir
        dest_dir.mkdir(parents=True, exist_ok=True)

        cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
        archives: List[Path] = []

        for log_path in self._iter_log_files():
            try:
                mtime = datetime.fromtimestamp(log_path.stat().st_mtime, tz=timezone.utc)
            except FileNotFoundError:
                continue

            if mtime > cutoff:
                continue

            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
            archive_name = dest_dir / f"{log_path.stem}_{timestamp}.zip"

            with zipfile.ZipFile(
                archive_name,
                mode="w",
                compression=zipfile.ZIP_DEFLATED,
            ) as zf:
                zf.write(log_path, arcname=log_path.name)

            try:
                log_path.unlink()
            except FileNotFoundError:
                pass

            archives.append(archive_name)

        return archives

    def shutdown(self) -> None:
        for key in list(self._loggers.keys()):
            self._detach_logger(key)
        if self._console_handler:
            try:
                self._console_handler.close()
            except Exception:
                pass
            self._console_handler = None

    def _detach_logger(self, category_key: str) -> None:
        logger = self._loggers.pop(category_key, None)
        if not logger:
            return
        for handler in list(logger.handlers):
            try:
                handler.close()
            except Exception:
                pass
            logger.removeHandler(handler)


def _to_int(value: Optional[Any], *, default: Optional[int] = None) -> Optional[int]:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_bool(value: Optional[Any], *, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return bool(value)


def _to_level(value: Optional[Any], *, default: int = logging.INFO) -> int:
    if value is None or value == "":
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        numeric = getattr(logging, value.strip().upper(), None)
        if isinstance(numeric, int):
            return numeric
    return default


def _parse_categories(config_categories: Optional[Iterable[Dict[str, Any]]]) -> Dict[str, LogCategory]:
    categories = DEFAULT_CATEGORIES.copy()
    if not config_categories:
        return categories
    for entry in config_categories:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name", "")).strip().lower()
        filename = str(entry.get("filename", "")).strip()
        if not name or not filename:
            continue
        categories[name] = LogCategory(name, filename)
    return categories


def _apply_category_flags(
    categories: Dict[str, LogCategory],
    *,
    disable: Optional[Iterable[str]] = None,
    enable: Optional[Iterable[str]] = None,
) -> Dict[str, LogCategory]:
    updated = categories.copy()
    if disable:
        for key in disable:
            updated.pop(str(key).strip().lower(), None)
    if enable:
        for key in enable:
            normalized = str(key).strip().lower()
            if normalized not in updated:
                updated[normalized] = LogCategory(normalized, f"{normalized}.log")
    return updated


_manager: Optional[LoggerManager] = None


def init_logger(app: Flask) -> LoggerManager:
    """
    Configure the shared logger manager using the provided Flask application.
    """

    global _manager

    categories = _parse_categories(app.config.get("LOGGING_EXTRA_CATEGORIES"))
    categories = _apply_category_flags(
        categories,
        disable=app.config.get("LOGGING_DISABLE_CATEGORIES"),
        enable=app.config.get("LOGGING_ENABLE_CATEGORIES"),
    )

    category_levels_cfg = app.config.get("LOGGING_CATEGORY_LEVELS") or {}
    category_levels = {
        str(name).strip().lower(): _to_level(level, default=_to_level(None))
        for name, level in category_levels_cfg.items()
    }

    static_fields = app.config.get("LOGGING_STATIC_FIELDS") or {}

    manager = LoggerManager(
        base_dir=app.config.get("LOGGING_BASE_DIR"),
        rotation_when=app.config.get("LOGGING_ROTATION_WHEN", "midnight"),
        rotation_interval=_to_int(app.config.get("LOGGING_ROTATION_INTERVAL"), default=1) or 1,
        backup_count=_to_int(app.config.get("LOGGING_ROTATION_BACKUP_COUNT")),
        archive_dir=app.config.get("LOGGING_ARCHIVE_DIR"),
        auto_archive_after_days=_to_int(app.config.get("LOGGING_AUTO_ARCHIVE_DAYS")),
        archive_check_interval_hours=_to_int(app.config.get("LOGGING_ARCHIVE_CHECK_HOURS"), default=6) or 6,
        categories=categories,
        enable_category_files=_to_bool(app.config.get("LOGGING_ENABLE_CATEGORY_FILES", True), default=True),
        mirror_app_handlers=_to_bool(app.config.get("LOGGING_MIRROR_APP_HANDLERS", True), default=True),
        auto_archive_enabled=_to_bool(app.config.get("LOGGING_ENABLE_AUTO_ARCHIVE", True), default=True),
        default_level=_to_level(app.config.get("LOGGING_DEFAULT_LEVEL"), default=logging.INFO),
        category_levels=category_levels,
        enable_console=_to_bool(app.config.get("LOGGING_CONSOLE_ENABLED", True), default=True),
        console_level=_to_level(app.config.get("LOGGING_CONSOLE_LEVEL"), default=logging.INFO),
        console_json=_to_bool(app.config.get("LOGGING_CONSOLE_JSON", False), default=False),
        json_format=_to_bool(app.config.get("LOGGING_JSON_FORMAT", False), default=False),
        text_format=app.config.get("LOGGING_TEXT_FORMAT"),
        date_format=app.config.get("LOGGING_DATE_FORMAT"),
        file_handler_level=_to_level(app.config.get("LOGGING_FILE_LEVEL")),
        static_fields=static_fields,
    )

    shutdown_logger()
    _manager = manager
    return _manager


def logger_manager() -> LoggerManager:
    global _manager
    if _manager is None:
        _manager = LoggerManager(
            rotation_when=os.getenv("LOGGING_ROTATION_WHEN", "midnight"),
            rotation_interval=_to_int(os.getenv("LOGGING_ROTATION_INTERVAL"), default=1) or 1,
            backup_count=_to_int(os.getenv("LOGGING_ROTATION_BACKUP_COUNT")),
            archive_dir=os.getenv("LOGGING_ARCHIVE_DIR"),
            auto_archive_after_days=_to_int(os.getenv("LOGGING_AUTO_ARCHIVE_DAYS")),
            archive_check_interval_hours=_to_int(os.getenv("LOGGING_ARCHIVE_CHECK_HOURS"), default=6) or 6,
            enable_category_files=_to_bool(os.getenv("LOGGING_ENABLE_CATEGORY_FILES", "true"), default=True),
            mirror_app_handlers=_to_bool(os.getenv("LOGGING_MIRROR_APP_HANDLERS", "true"), default=True),
            auto_archive_enabled=_to_bool(os.getenv("LOGGING_ENABLE_AUTO_ARCHIVE", "true"), default=True),
            default_level=_to_level(os.getenv("LOGGING_DEFAULT_LEVEL"), default=logging.INFO),
            enable_console=_to_bool(os.getenv("LOGGING_CONSOLE_ENABLED", "true"), default=True),
            console_level=_to_level(os.getenv("LOGGING_CONSOLE_LEVEL"), default=logging.INFO),
            console_json=_to_bool(os.getenv("LOGGING_CONSOLE_JSON"), default=False),
            json_format=_to_bool(os.getenv("LOGGING_JSON_FORMAT"), default=False),
            text_format=os.getenv("LOGGING_TEXT_FORMAT"),
            date_format=os.getenv("LOGGING_DATE_FORMAT"),
            file_handler_level=_to_level(os.getenv("LOGGING_FILE_LEVEL")),
        )
    return _manager


def shutdown_logger() -> None:
    global _manager
    if _manager is None:
        return
    _manager.shutdown()
    _manager = None


def get_logger(category: str) -> logging.Logger:
    return logger_manager().get_logger(category)


def clear_log(category: str) -> List[Path]:
    return logger_manager().clear_log(category)


def clear_all_logs() -> List[Path]:
    return logger_manager().clear_all_logs()


def archive_logs(
    older_than_days: int,
    *,
    destination_dir: Optional[str] = None,
) -> List[Path]:
    return logger_manager().archive_logs(
        older_than_days=older_than_days,
        destination_dir=destination_dir,
    )


def register_category(name: str, filename: Optional[str] = None) -> LogCategory:
    return logger_manager().register_category(name, filename=filename)
