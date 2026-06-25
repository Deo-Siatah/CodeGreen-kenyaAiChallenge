from repositories.base_repository import BaseRepository


class SettlementRepository(BaseRepository):

    def create(self, settlement_data: dict):

        query = """
        CREATE (s:InKindSettlementProof)
        SET s += $data
        RETURN s
        """

        with self.driver.session() as session:
            result = session.run(
                query,
                data=settlement_data
            )

            return result.single()