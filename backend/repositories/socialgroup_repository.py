from repositories.base_repository import BaseRepository


class SocialGroupRepository(BaseRepository):

    def create_social_group(self, group_data: dict):

        query = """
        CREATE (g:SocialGroup)
        SET g += $data
        RETURN g
        """

        with self.driver.session() as session:
            result = session.run(
                query,
                data=group_data
            )

            return result.single()