"""Django storage backend that keeps media files in the database.

Used on hosts with a read-only or temporary disk (Vercel, Render). Files are
served back through the ``media/`` route in ``config/urls.py``.
"""
import mimetypes

from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible
from django.utils.encoding import filepath_to_uri
from sqlalchemy import delete, select


@deconstructible
class DatabaseStorage(Storage):
    def _session(self):
        from api.sql_store import SessionLocal, ensure_tables

        ensure_tables()
        return SessionLocal()

    def _open(self, name, mode="rb"):
        from api.sql_store import MediaFileRecord

        with self._session() as session:
            content = session.scalar(select(MediaFileRecord.content).where(MediaFileRecord.name == name))
        if content is None:
            raise FileNotFoundError(name)
        file = ContentFile(content)
        file.name = name
        return file

    def _save(self, name, content):
        from api.sql_store import MediaFileRecord

        content.seek(0)
        mime_type = getattr(content, "content_type", None) or mimetypes.guess_type(name)[0] or "application/octet-stream"
        with self._session() as session:
            session.add(MediaFileRecord(name=name, mime_type=mime_type, content=content.read()))
            session.commit()
        return name

    def delete(self, name):
        from api.sql_store import MediaFileRecord

        with self._session() as session:
            session.execute(delete(MediaFileRecord).where(MediaFileRecord.name == name))
            session.commit()

    def exists(self, name):
        from api.sql_store import MediaFileRecord

        with self._session() as session:
            return session.scalar(select(MediaFileRecord.id).where(MediaFileRecord.name == name)) is not None

    def size(self, name):
        from api.sql_store import MediaFileRecord
        from sqlalchemy import func

        with self._session() as session:
            size = session.scalar(select(func.length(MediaFileRecord.content)).where(MediaFileRecord.name == name))
        if size is None:
            raise FileNotFoundError(name)
        return size

    def mime_type(self, name):
        from api.sql_store import MediaFileRecord

        with self._session() as session:
            return session.scalar(select(MediaFileRecord.mime_type).where(MediaFileRecord.name == name))

    def url(self, name):
        from django.conf import settings

        return settings.MEDIA_URL + filepath_to_uri(name)
