from dbcontrol import Product
from template_executor import TemplateExecutor
from PIL import Image
import requests
from jinja2 import Environment, FileSystemLoader, select_autoescape
import os
from visualnode import vnode_tree_from_file, vnode_tree_from_string



class BasicXMLTemplate(TemplateExecutor):
    """
    XML-powered template for the product ad.
    This class implements the basic template I designed in Canva. Yes, one with the icons))
    Font color of the main banner section will be either black or white, depending on the main color provided.
    In case corresponding icon is not found, it will be absent from the image.
    """
    def __init__(self, product: Product, 
                 dimensions: tuple[int, int], 
                 slogan: str,
                 main_color: tuple[int, int, int, int], 
                 svgapi_key: str) -> None:
        """
        :param dimensions: The dimensions of requested image (width, height)
        :param slogan: The slogan for the product
        :param main_color: The main color of the template. See Canva for how it looks like
        :param svgapi_key: The key for the SVG API.
        """
        template_path = os.path.dirname(os.path.abspath(__file__)) + "/basicxmltemplate.xml.j2"
        super().__init__(template_path, product)
        self.dimensions = dimensions
        self.slogan = slogan
        self.main_color = main_color
        self.svgapi_key = svgapi_key
        self.env = Environment(
            loader=FileSystemLoader("/"),
            autoescape=select_autoescape()
        )
        
    def compose(self) -> Image:
        """
        Composes the template and returns the composed image.
        """
        # width and height
        width = self.dimensions[0]
        height = self.dimensions[1]
        
        # main table direction        
        if self.dimensions[0] > self.dimensions[1]:
            main_table_direction = "h"
        else:
            main_table_direction = "v"
        
        # main color
        main_color = self.main_color
        
        # slogan
        # NOTE: implement the slogan generator
        slogan = self.slogan
        
        # svg icon path
        # NOTE: implement the icon fetching
        svg_icon_path = "img/tv.png"
        
        # product_img_path
        product_img_path = self.product.image_link
        
        # product_name
        product_name = self.product.name
        
        # fonts        
        # NOTE: implement the font selection
        slogan_font_path = "fonts/Roca Regular.ttf"
        product_name_font_path = "fonts/Times New Roman.ttf"
                    
        template = self.env.get_template(os.path.abspath(self.template_path))
        xml_template_rendered = template.render(
            width=width,
            height=height,
            main_table_direction=main_table_direction,
            main_color=main_color,
            slogan=slogan,
            svg_icon_path=svg_icon_path,
            product_img_path=product_img_path,
            product_name=product_name,
            slogan_font_path=slogan_font_path,
            product_name_font_path=product_name_font_path
        )
        
        print(xml_template_rendered)
        root_node = vnode_tree_from_string(xml_template_rendered)
        return root_node.compose()
        