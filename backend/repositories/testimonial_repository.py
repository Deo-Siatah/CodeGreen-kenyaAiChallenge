from repositories.base_repository import BaseRepository


class TestimonialRepository(BaseRepository):

    def create(self, testimonial_data: dict):

        query = """
        CREATE (t:Testimonial)
        SET t += $data
        RETURN t
        """

        with self.driver.session() as session:
            result = session.run(
                query,
                data=testimonial_data
            )

            return result.single()