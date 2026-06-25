from repositories.base_repository import BaseRepository


class InstitutionRepository(BaseRepository):

    def create_institution(self, institution_data: dict):

        query = """
        CREATE (i:Institution)
        SET i += $data
        RETURN i
        """

        with self.driver.session() as session:
            result = session.run(
                query,
                data=institution_data
            )

            return result.single()