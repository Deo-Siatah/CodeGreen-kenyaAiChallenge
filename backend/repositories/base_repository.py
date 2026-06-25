from core.database import db


class BaseRepository:

    @property
    def driver(self):
        return db.driver