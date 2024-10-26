from dbcontrol import Product, User
from PIL import Image
from abc import ABC, abstractmethod

class TemplateExecutor(ABC):
    """
    This class takes an XML/HTML template and renders it with the given data.
    """
    
    def __init__(self, template_path, product: Product) -> None:
        self.template_path = template_path
        self.product = product
        
    @abstractmethod
    def compose(self) -> Image:
        """
        Composes the template and returns the composed image.
        """
        return None