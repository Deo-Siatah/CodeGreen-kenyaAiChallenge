from repositories.base_repository import BaseRepository


class VerificationRepository(BaseRepository):

    def create_session(self, data: dict):

        query = """
        CREATE (v:VerificationSession)
        SET v += $data
        RETURN v
        """

        with self.driver.session() as session:
            result = session.run(
                query,
                data=data
            )

            return result.single()