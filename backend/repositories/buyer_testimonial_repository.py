from repositories.base_repository import BaseRepository


class BuyerTestimonialRepository(BaseRepository):

    def create(self, testimonial_data: dict):

        query = """
        CREATE (b:BuyerTestimonial)
        SET b += $data
        RETURN b
        """

        with self.driver.session() as session:
            result = session.run(
                query,
                data=testimonial_data
            )

            return result.single()