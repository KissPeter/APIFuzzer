from kitty.model import GraphModel


class APIFuzzerModel(GraphModel):

    def __init__(self, name='GraphModel', content_type=None):
        super().__init__(name)
        self.content_type = content_type
