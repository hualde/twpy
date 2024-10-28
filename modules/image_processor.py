import base64
from io import BytesIO
from PIL import Image, ImageOps, ImageFilter, ImageEnhance

class ImageProcessor:
    @staticmethod
    def apply_effects(image):
        original = Image.open(image).convert('RGB')
        greyscale = ImageOps.grayscale(original)
        blur = original.filter(ImageFilter.GaussianBlur(radius=5))
        contrast = ImageEnhance.Contrast(original).enhance(1.5)

        return {
            'original': original,
            'greyscale': greyscale,
            'blur': blur,
            'contrast': contrast
        }

    @staticmethod
    def image_to_base64(image):
        buffered = BytesIO()
        if image.mode == 'RGBA':
            image = image.convert('RGB')
        image.save(buffered, format="JPEG")
        return base64.b64encode(buffered.getvalue()).decode('utf-8')