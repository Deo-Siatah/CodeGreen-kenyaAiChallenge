from repositories.base_repository import BaseRepository


class VerificationRepository(BaseRepository):
    """
    DEPRECATED: Use VerificationSessionRepository instead.
    Keeping only for backward compatibility with legacy methods.
    """

    def get_session_trust_sources(self, farmer_id: str):
        """Get trust sources for a farmer"""
        query = """
        MATCH (f:Farmer {id:$farmer_id})
            -[:VERIFIED_BY]->
            (t:TrustSource)
        RETURN t
        """

        with self.driver.session() as session:
            result = session.run(query, farmer_id=farmer_id)
            return [dict(record["t"]) for record in result]

    def get_session_participants(self, session_id: str):
        """Get participants in a session"""
        query = """
        MATCH (v:VerificationSession {id:$id})
            -[:SENT_TO]->
            (t)
        RETURN t
        """

        with self.driver.session() as session:
            result = session.run(query, id=session_id)
            return [dict(record["t"]) for record in result]

    def attach_question(self, session_id: str, question_id: str):
        """Attach question to session"""
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
            record = result.single()
            return dict(record["q"]) if record else {}