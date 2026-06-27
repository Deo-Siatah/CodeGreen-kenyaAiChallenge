from repositories.base_repository import BaseRepository


class ResponseRepository(BaseRepository):

    def create_response(
        self,
        data: dict
    ):

        query = """
        CREATE (r:VerificationResponse)
        SET r += $data
        RETURN r
        """

        with self.driver.session() as session:

            result = session.run(
                query,
                data=data
            )

            return result.single()
        
    

    def attach_to_question(
    self,
    response_id: str,
    question_id: str
    ):

        query = """
        MATCH (r:VerificationResponse {id:$response_id})
        MATCH (q:Question {id:$question_id})

        MERGE (r)-[:FOR]->(q)

        RETURN r
        """

        with self.driver.session() as session:

            return session.run(
                query,
                response_id=response_id,
                question_id=question_id
            ).single()
        
    def attach_to_trust_source(
    self,
    response_id: str,
    trust_source_id: str
    ):

        query = """
        MATCH (r:VerificationResponse {id:$response_id})
        MATCH (t:TrustSource {id:$trust_source_id})

        MERGE (t)-[:SUBMITTED]->(r)

        RETURN r
        """

        with self.driver.session() as session:

            return session.run(
                query,
                response_id=response_id,
                trust_source_id=trust_source_id
            ).single()