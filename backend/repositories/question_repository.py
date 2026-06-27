from repositories.base_repository import BaseRepository


class QuestionRepository(BaseRepository):

    def create_question(
        self,
        data: dict
    ):

        query = """
        CREATE (q:Question)
        SET q += $data
        RETURN q
        """

        with self.driver.session() as session:

            result = session.run(
                query,
                data=data
            )

            return result.single()

    def get_question(
        self,
        question_id: str
    ):

        query = """
        MATCH (q:Question {id:$id})
        RETURN q
        """

        with self.driver.session() as session:

            result = session.run(
                query,
                id=question_id
            )

            return result.single()

    def get_session_questions(
        self,
        session_id: str
    ):

        query = """
        MATCH (v:VerificationSession {id:$id})
              -[:HAS_QUESTION]->
              (q:Question)

        RETURN q
        """

        with self.driver.session() as session:

            result = session.run(
                query,
                id=session_id
            )

            return [
                record["q"]
                for record in result
            ]
    def attach_question(
    self,
    session_id: str,
    question_id: str
    ):

        query = """
        MATCH (v:VerificationSession {id:$session_id})
        MATCH (q:Question {id:$question_id})

        MERGE (v)-[:HAS_QUESTION]->(q)

        RETURN q
        """

        with self.driver.session() as session:

            result = session.run(
                query,
                session_id=session_id,
                question_id=question_id
            )

            return result.single()