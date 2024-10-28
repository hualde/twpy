from instagrapi import Client
from PIL import Image
import tempfile
import os

class InstagramHandler:
    def __init__(self):
        self.client = Client()
        self.is_logged_in = False

    def login(self):
        if not self.is_logged_in:
            self.client.login(os.environ.get('INSTAGRAM_USERNAME'), os.environ.get('INSTAGRAM_PASSWORD'))
            self.is_logged_in = True

    def post_image(self, caption_text, image):
        try:
            self.login()
            
            # Convert PIL Image to file
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                image.save(temp_file, format='JPEG')
                temp_file_name = temp_file.name

            # Upload the image
            media = self.client.photo_upload(temp_file_name, caption=caption_text)
            
            os.unlink(temp_file_name)  # Delete the temporary file
            return "Publicación en Instagram realizada con éxito."
        except Exception as e:
            return f"Error al publicar en Instagram: {str(e)}"