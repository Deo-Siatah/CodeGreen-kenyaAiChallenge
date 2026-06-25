import uuid
from repositories.base_repository import BaseRepository


class TrustSourceRepository(BaseRepository):

    def create_trust_source(self, trust_source_data: dict):
        trust_source_data["id"] = str(uuid.uuid4())
        query = """
        CREATE (t:TrustSource)
        SET t += $data
        RETURN t
        """

        with self.driver.session() as session:
            result = session.run(
                query,
                data=trust_source_data
            )

            return result.single()

    def get_by_id(self, trust_source_id: str):

        query = """
        MATCH (t:TrustSource {id:$id})
        RETURN t
        """

        with self.driver.session() as session:
            result = session.run(
                query,
                id=trust_source_id
            )

            return result.single()