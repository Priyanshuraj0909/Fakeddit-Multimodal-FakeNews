"""Image feature adapter for the shared local CLIP encoder."""
class ImageModel:
    def __init__(self, encoder):
        self.encoder = encoder

    def encode(self, image):
        return self.encoder.encode_image(image)
