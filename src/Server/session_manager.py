import uuid

from src.LLM.history import ConversationHistory
from src.RAG.orchestrator import RAGOrchestrator
from src.RAG.resources import Resources

from src.RAG.handlers.registry import _autodiscover



class SessionManager:
    def __init__(self):
        self.sessions = {}
        _autodiscover()  # Ensure handlers are registered before any sessions are created
        print("SessionManager initialized, ready to manage sessions.")

    def create_session(self, resources: Resources):
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = Session(session_id, resources)
        return session_id

    def get_session(self, session_id: str):
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")
        return self.sessions[session_id]

    def delete_session(self, session_id: str):
        del self.sessions[session_id]

    def close(self):
        for session in self.sessions.values():
            session.close()
        self.sessions.clear()

class Session:
    def __init__(self, session_id: str, resources: Resources):
        self.session_id = session_id
        self.history = ConversationHistory()
        self.resources = resources
        self.orchestrator = RAGOrchestrator(self.resources)
        self.orchestrator.initialize()

    def prompt(self, prompt: str):
        history = self.history.get_history()
        response = self.orchestrator.prompt(prompt, history)
        self.history.add_message("user", prompt)
        self.history.add_message("assistant", response)
        return response

    def close(self):
        self.orchestrator.close()