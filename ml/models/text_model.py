"""Text feature adapter for the shared local CLIP encoder."""
class TextModel:
    def __init__(self, encoder):
        self.encoder = encoder

    def encode(self, text):
        return self.encoder.encode_text(text)
