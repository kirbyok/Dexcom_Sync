import os
import sys
import logging
from pathlib import Path
import arrow


def _ensure_tconnectsync_on_path() -> Path:
    base = Path(__file__).parent / "tconnectsync-master"
    if not base.exists():
        raise FileNotFoundError("tconnectsync-master directory not found")
    path_str = str(base)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)
    return base


def _map_env_from_project() -> None:
    os.environ.setdefault("TCONNECT_EMAIL", os.getenv("TCONNECT_USERNAME", ""))
    os.environ.setdefault("TCONNECT_PASSWORD", os.getenv("TCONNECT_PASSWORD", ""))
    os.environ.setdefault("TCONNECT_REGION", os.getenv("TCONNECT_REGION", "US"))

    ns_url = os.getenv("NS_URL") or os.getenv("NIGHTSCOUT_URL", "")
    os.environ.setdefault("NS_URL", ns_url)
    ns_secret = os.getenv("NS_SECRET") or os.getenv("NIGHTSCOUT_API_TOKEN", "")
    os.environ.setdefault("NS_SECRET", ns_secret)

    os.environ.setdefault("TIMEZONE_NAME", os.getenv("TIMEZONE", "UTC"))
    os.environ.setdefault("CACHE_CREDENTIALS", "true")

    base = Path(os.getenv("LOG_DIR", "/app/logs"))
    cache_dir = Path(os.getenv("TCONNECT_CACHE_DIR", base / ".config" / "tconnectsync"))
    cache_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("CACHE_CREDENTIALS_PATH", str(cache_dir / ".creds_cache"))


def run_tconnectsync(hours: int, feature_flags: dict[str, bool], logger: logging.Logger) -> bool:
    """Run Tandem sync using vendored tconnectsync code."""
    try:
        _ensure_tconnectsync_on_path()
        _map_env_from_project()

        from tconnectsync import secret
        from tconnectsync import TConnectApi
        from tconnectsync.nightscout import NightscoutApi
        from tconnectsync.sync.tandemsource.choose_device import ChooseDevice
        from tconnectsync.sync.tandemsource.process import ProcessTimeRange
        from tconnectsync.features import DEFAULT_FEATURES

        time_end = arrow.utcnow()
        time_start = time_end.shift(hours=-hours)

        selected_features = [name for name, enabled in feature_flags.items() if enabled]
        if not selected_features:
            selected_features = list(DEFAULT_FEATURES)

        tconnect = TConnectApi(secret.TCONNECT_EMAIL, secret.TCONNECT_PASSWORD, secret.TCONNECT_REGION)
        nightscout = NightscoutApi(
            secret.NS_URL,
            secret.NS_SECRET,
            skip_verify=secret.NS_SKIP_TLS_VERIFY,
            ignore_conn_errors=secret.NS_IGNORE_CONN_ERRORS,
        )

        device = ChooseDevice(secret, tconnect).choose()
        added, last_event_id = ProcessTimeRange(
            tconnect,
            nightscout,
            device,
            pretend=False,
            secret=secret,
            features=selected_features,
        ).process(time_start, time_end)

        logger.info("tconnectsync processed %s events; last seq %s", added, last_event_id)
        return added > 0
    except Exception as exc:  # noqa: BLE001
        logger.error("tconnectsync run failed: %s", exc, exc_info=True)
        return False
