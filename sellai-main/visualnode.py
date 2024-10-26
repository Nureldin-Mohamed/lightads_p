from PIL import Image, ImageDraw, ImageFont, ImageFilter
from typing import List
import xml.etree.ElementTree as ET
import io
from ast import literal_eval
 

class VNode:
    def __init__(self, width: int, height: int, children: 'List[VNode]', bg_color: tuple[int, int, int, int], offsets = []):
        self.width = width
        self.height = height
        self.children = children
        self.bg_color = bg_color
        self.offsets = offsets
        
            
    def compose(self) -> Image:
        ret_img = Image.new("RGBA", (self.width, self.height), self.bg_color)
        return ret_img
    

class Root(VNode):
    def __init__(self, 
                 width: int, 
                 height: int, 
                 children: List[VNode], 
                 bg_color: tuple[int, int, int, int]
    ):
        if len(children) != 1:
            raise ValueError("Number of children in root element must be equal to one")
        super().__init__(width, height, children, bg_color, [])
    
    def compose(self) -> Image:
        ret_img = Image.new("RGBA", (self.width, self.height), self.bg_color)
        self.children[0].width = self.width
        self.children[0].height = self.height
        c_img = self.children[0].compose()
        ret_img.paste(c_img, (0, 0), c_img)
        return ret_img


class FitText(VNode):
    def __init__(self, 
               width: int, 
               height: int, 
               text: str, 
               max_font_size: int,
               line_spacing: int,
               font_path: str,
               bg_color: tuple[int, int, int, int], 
               font_color: tuple[int, int, int, int],
               children: List[VNode] = []
    ):
        super().__init__(width, height, [], bg_color)
        self.text = text
        self.max_font_size = max_font_size
        self.font_path = font_path
        self.font_color = font_color
        self.line_spacing = line_spacing
        self.children = children
        
    def compose(self):
        ret_img = Image.new("RGBA", (self.width, self.height), self.bg_color)
        text_img = Image.new("RGBA", (self.width, self.height), (0,0,0,0)) # this one is needed to get bbox of text afterwards
        draw = ImageDraw.Draw(text_img)
        font_size = self.max_font_size
        while font_size > 0:
            lines = []
            line = ""
            font = ImageFont.FreeTypeFont(self.font_path, font_size)
            
            metrics = list(font.getmetrics())
            formal_line_height = (metrics[0] - metrics[1]) * self.line_spacing
            
            words = self.text.split()
            i = 0
            while i < len(words):
                word = words[i]
                wordbb = font.getbbox(word)
                if wordbb[2] - wordbb[0] >= self.width:
                    break
                
                nextline = word if (line == "") else line + " " + word
                nlbbox = font.getbbox(nextline, anchor="lt")
                if nlbbox[2] - nlbbox[0] > self.width:
                    lines += [line]
                    line = ""
                    continue
                else:
                    line = nextline
                    
                if i == len(words) - 1:
                    lines += [line]
                
                i += 1
                
            if wordbb[2] - wordbb[0] >= self.width:
                font_size -= 1
                continue
                
            last_line_bbox = font.getbbox(lines[len(lines) - 1], anchor="lt")
            if formal_line_height * (len(lines) - 1) + last_line_bbox[3] - last_line_bbox[1] > self.height:
                    font_size -= 1
                    continue
            else:
                break
        
        for i in range(len(lines)):
            line = lines[i]
            draw.text((0, i * formal_line_height), line, self.font_color, font, anchor="lt")
        
        # this part centers the text horizontally and vertically
        textbbox = text_img.getbbox()
        text_width = textbbox[2] - textbbox[0]
        text_height = textbbox[3] - textbbox[1]
        ret_img.paste(text_img, ((self.width - text_width) // 2, (self.height - text_height) // 2), text_img)
        
        return ret_img
            
            
class FTable(VNode):
    def __init__(self, 
                 width, 
                 height, 
                 children: List[VNode], 
                 bg_color: tuple[int, int, int, int], 
                 direction: str, offsets: List[int], 
                 use_percent: bool = False
    ):
        if len(children) < 1:
            raise ValueError("Number of children in FTable node should be nonzero")
        super().__init__(width, height, children, bg_color)
        if len(offsets) != len(children):
            return ValueError("Length of offsets array should be equal to length of children array")
        
        self.offsets = offsets
        self.direction = direction
        self.children = children
        self.use_percent = use_percent
            
        # print(self.offsets)

        
    def compose(self): 
        ret_img = Image.new("RGBA", (self.width, self.height), self.bg_color)
        
        if self.use_percent:
            side = self.width if self.direction == "h" else self.height
            for i in range(len(self.offsets)):
                self.offsets[i] = int(self.offsets[i] * side / 100)
            self.use_percent = False
        
        # print(self.offsets)
        
        for i in range(len(self.children)):
            if i < len(self.children) - 1:
                metric = self.offsets[i + 1] - self.offsets[i]
            else:
                if self.direction == "h":
                    metric = self.width - self.offsets[len(self.children) - 1]
                else:
                    metric = self.height - self.offsets[len(self.children) - 1]
                    
                
            if self.direction == "h":
                self.children[i].width = metric
                self.children[i].height = self.height
            else:
                self.children[i].height = metric
                self.children[i].width = self.width
            # print(self.children[i].width)
                
        for i in range(len(self.children)):
            child_img = self.children[i].compose()
            offset = self.offsets[i]
            if self.direction == "h":
                ret_img.paste(child_img, (offset, 0), child_img)
            else:
                ret_img.paste(child_img, (0, offset), child_img)   
        return ret_img
                    

class Padding(VNode):
    def __init__(self, 
                 width: int, 
                 height: int, 
                 bg_color: tuple[int, int, int, int], 
                 padding: tuple[int, int, int, int],
                 use_percent: bool = False,
                 children: List[VNode] = []
    ):
        super().__init__(width, height, children, bg_color, [])
        self.padding_left = padding[0]
        self.padding_right = padding[1]
        self.padding_top = padding[2]
        self.padding_bottom = padding[3]
        self.use_percent = use_percent
        
    def compose(self):
        ret_img = Image.new("RGBA", (self.width, self.height), self.bg_color)
        ppadding_left = self.padding_left
        ppadding_right = self.padding_right
        ppadding_top = self.padding_top
        ppadding_bottom = self.padding_bottom
        if self.use_percent:
            ppadding_left = int(ppadding_left * self.width / 100)
            ppadding_right = int(ppadding_right * self.width / 100)
            ppadding_top = int(ppadding_top * self.height / 100)
            ppadding_bottom = int(ppadding_bottom * self.height / 100)
            self.use_percent = False
        
        c_width = self.width - ppadding_left - ppadding_right
        c_height = self.height - ppadding_top - ppadding_bottom
        self.children[0].width = c_width
        self.children[0].height = c_height
        c_img = self.children[0].compose()
        ret_img.paste(c_img, (ppadding_left, ppadding_top), c_img)
        return ret_img


class Shadow(VNode):
    def __init__(self,
        width: int,
        height: int,
        bg_color: tuple[int, int, int, int],
        shadow_color: tuple[int, int, int, int],
        shadow_intensity: int,
        shadow_offset: tuple[int, int],
        children: List[VNode] = []
    ):
        super().__init__(width, height, children, bg_color, [])
        self.shadow_intensity = shadow_intensity
        self.shadow_offset = shadow_offset
        self.shadow_color = shadow_color
        
    def compose(self):
        ret_img = Image.new("RGBA", (self.width, self.height), self.bg_color)
        self.children[0].width = self.width
        self.children[0].height = self.height
        c_img = self.children[0].compose()
        ret_img.paste(self.shadow_color, self.shadow_offset, c_img)
        for i in range(self.shadow_intensity):
            ret_img = ret_img.filter(ImageFilter.BLUR)
        ret_img.paste(c_img, (0, 0), c_img)
        return ret_img        

class Picture(VNode):
    def __init__(self,
        width: int,
        height: int,
        bg_color: tuple[int, int, int, int],
        img_source: io.BytesIO | str,
        mode: str,
        children: List[VNode] = []
    ):
        super().__init__(width, height, [], bg_color, [])
        self.img_source = img_source
        self.mode = mode
    
    def compose(self):
        ret_img = Image.new("RGBA", (self.width, self.height), self.bg_color)
        picture = Image.open(self.img_source)
        picture = picture.convert("RGBA")
        pic_width, pic_height = picture.size
        
        if self.mode == "fit":
            ratio = min(self.width / pic_width, self.height / pic_height)
        if self.mode == "fill":
            ratio = max(self.width / pic_width, self.height / pic_height)
            
        pic_width = round(pic_width * ratio)
        pic_height = round(pic_height * ratio)
        # print(pic_width, pic_height)
        picture = picture.resize((pic_width, pic_height))
        pic_offset = (self.width - pic_width) // 2, (self.height - pic_height) // 2
        ret_img.paste(picture, pic_offset, picture)
        return ret_img
                         
vnode_types = {
    "VNode": VNode, 
    "Root": Root,
    "FitText": FitText,
    "FTable": FTable, 
    "Padding": Padding, 
    "Picture": Picture, 
    "Shadow": Shadow,
}


def __visit_vertex(xml_element: ET.Element) -> VNode:
    tag = xml_element.tag
    args = xml_element.attrib
    valued_args = args
    for arg in valued_args:
        # print(valued_args[arg])
        try:
            valued_args[arg] = literal_eval(valued_args[arg])
        except (ValueError, SyntaxError):
            valued_args[arg] = args[arg]
    # print(tag, valued_args)
    children = []
    for child in xml_element:
        children += [__visit_vertex(child)]
    valued_args["children"] = children
    print(tag, valued_args)
    vnode = vnode_types[tag](**valued_args)
    return vnode


def vnode_tree_from_file(file_path) -> VNode:
    "Parses a file and returns the root node of the element tree"
    tree = ET.parse(file_path)
    tree_root = tree.getroot()
    vnode_root = __visit_vertex(tree_root)
    return vnode_root

def vnode_tree_from_string(string) -> VNode:
    "Parses a string and returns the root node of the element tree"
    tree = ET.ElementTree(ET.fromstring(string))
    tree_root = tree.getroot()
    vnode_root = __visit_vertex(tree_root)
    return vnode_root