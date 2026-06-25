import uuid
from repositories.base_repository import BaseRepository


class FarmerRepository(BaseRepository):

    def create(self, farmer_data: dict):
        farmer_data["id"] = str(uuid.uuid4())
        query = """
        CREATE (f:Farmer)
        SET f += $data
        RETURN f
        """

        with self.driver.session() as session:
            result = session.run(
                query,
                data=farmer_data
            )

            return result.single()

    def get_by_id(self, farmer_id: str):

        query = """
        MATCH (f:Farmer {id:$id})
        RETURN f
        """

        with self.driver.session() as session:
            result = session.run(
                query,
                id=farmer_id
            )

            return result.single()

    def list_all(self):

        query = """
        MATCH (f:Farmer)
        RETURN f
        """

        with self.driver.session() as session:
            result = session.run(query)

            return [record["f"] for record in result]