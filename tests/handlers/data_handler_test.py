from src.RAG.handlers.data_handler import DataHandler

def test_data_handler():
    handler = DataHandler()
    assert handler is not None
    # Test that the handler can process a simple query
    query = "What is the capital of France?"
    response = handler.handle_query(query)
    assert response is not None
    assert "Paris" in response