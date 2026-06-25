from repositories.base_repository import BaseRepository


class MarketActorRepository(BaseRepository):

    def create(self, actor_data: dict):

        query = """
        CREATE (m:MarketActor)
        SET m += $data
        RETURN m
        """

        with self.driver.session() as session:
            result = session.run(
                query,
                data=actor_data
            )

            return result.single()