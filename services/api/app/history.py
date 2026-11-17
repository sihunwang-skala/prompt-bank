from .db import new_id
from .models import HistoryEvent
from .security import redact


def log(db, user_id, kind, entity_type="", entity_id="", project_id=None, **data):
    """Append a structured, timestamped record. Secrets are redacted before storage."""
    clean = {k: (redact(v) if isinstance(v, str) else v) for k, v in data.items()}
    ev = HistoryEvent(user_id=user_id, project_id=project_id, kind=kind, entity_type=entity_type, entity_id=entity_id, data=clean)
    db.add(ev)
    db.commit()
    return ev
