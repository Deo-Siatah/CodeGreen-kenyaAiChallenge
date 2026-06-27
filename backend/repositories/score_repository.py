from repositories.base_repository import BaseRepository


class ScoreRepository(BaseRepository):

    def create_score_profile(
        self,
        data: dict
    ):

        query = """
        CREATE (s:ScoreProfile)
        SET s += $data
        RETURN s
        """

        with self.driver.session() as session:

            result = session.run(
                query,
                data=data
            )

            return result.single()