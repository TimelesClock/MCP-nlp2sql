class BaseLLMService:
    """Base class for LLM service implementations"""
    def __init__(self):
        self.last_raw_response = []

    async def process_chain(self, *args, **kwargs):
        raise NotImplementedError()
