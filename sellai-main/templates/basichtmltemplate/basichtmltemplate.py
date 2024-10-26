from template_executor import TemplateExecutor
from jinja2 import Environment, FileSystemLoader, select_autoescape
from dbcontrol import Product
from PIL import Image
from weasyprint import HTML
from io import BytesIO
import os

class BasicHTMLTemplate(TemplateExecutor):
    """
    HTML-powered template for the product ad.
    """
    def __init__(self, product: Product, 
                 dimensions: tuple[int, int], 
                 slogan: str,
                 main_color: tuple[int, int, int, int], 
                 ):
        template_path = os.path.dirname(os.path.abspath(__file__)) + "/basichtmltemplate.html.j2"
        super().__init__(template_path, product)
        self.product = product
        self.dimensions = dimensions
        self.slogan = slogan
        self.main_color = main_color
        self.env = Environment(
            loader=FileSystemLoader("/"),
            autoescape=select_autoescape()
        )
        
    def compose(self) -> Image:
        html_path = ""
        buffer = BytesIO()
    
        # Check if the input is a local file or a string of HTML content
        if os.path.isfile(self.template_path):
            HTML(filename=self.template_path).write_png(buffer)
        else:
            HTML(string=self.template_path).write_png(buffer)

        # Move the buffer's cursor to the beginning
        buffer.seek(0)

        # Open the image with Pillow
        image = Image.open(buffer)

        return image
