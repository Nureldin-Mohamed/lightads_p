from PIL import Image, ImageFont, ImageDraw
import colorsys
import gi
import cairo
gi.require_version('Pango', '1.0')
gi.require_version('PangoCairo', '1.0')
from gi.repository import Pango, PangoCairo, GLib

from collections import Counter


def to_pil(surface: cairo.ImageSurface) -> Image:
    format = surface.get_format()
    size = (surface.get_width(), surface.get_height())
    stride = surface.get_stride()

    with surface.get_data() as memory:
        if format == cairo.Format.RGB24:
            return Image.frombuffer(
                "RGB", size, memory.tobytes(),
                'raw', "BGRX", stride)
        elif format == cairo.Format.ARGB32:
            return Image.frombuffer(
                "RGBA", size, memory.tobytes(),
                'raw', "BGRa", stride)
        else:
            raise NotImplementedError(repr(format))


def crop_to_visible(img):
    if img.mode != 'RGBA':
        img = img.convert('RGBA')  
    bbox = img.getbbox() 
    if bbox:
        cropped_img = img.crop(bbox)
        return cropped_img
    else:
        return img
    

# take pil image, return rgb color
def get_dominant_color(img):
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    
    pixels = [
        (r, g, b) 
        for r, g, b, a in img.getdata() 
        if a > 0 
    ]
    
    if not pixels:
        raise ValueError("No visible pixels found in the image.")

    # Count the frequency of each color
    pixel_counts = Counter(pixels)
    
    # Get the most common color
    dominant_color = pixel_counts.most_common(1)[0][0]
    
    return dominant_color

def get_complementary_color(rgb_color):
    r, g, b = rgb_color
    h, s, v = colorsys.rgb_to_hsv(r/255.0, g/255.0, b/255.0)
    h = (h + 0.5) % 1.0
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return (int(r*255), int(g*255), int(b*255))

def fit_text(box_width, box_height, text, font_family="Sans", font_color=(255, 255, 255)):
    text = text.rstrip()
    
    # Create an image surface to draw on
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, box_width, box_height)
    context = cairo.Context(surface)

    # Create a PangoCairo context
    pangocairo_context = PangoCairo.create_context(context)
    
    # Create a Pango layout, which will hold the text
    layout = Pango.Layout.new(pangocairo_context)
    layout.set_text(text, -1)
    
    # Set the alignment to center the text
    layout.set_alignment(Pango.Alignment.CENTER)
    
    # Set the text to wrap within the specified width
    layout.set_width(box_width * Pango.SCALE)  # Pango uses 1/1024ths of a point

    # Initialize font size and scaling factor
    font_size = 1
    font_description = Pango.FontDescription(font_family)
    layout.set_font_description(font_description)
    
    while True:
        # Update the font size
        font_description.set_size(font_size * Pango.SCALE)
        layout.set_font_description(font_description)
        
        # Get the text size
        text_width, text_height = layout.get_pixel_size()
        
        # Check if the text fits within the box
        if text_width <= box_width and text_height <= box_height:
            font_size += 1  # Increase the font size and try again
        else:
            break  # If the text exceeds the box, stop the loop
    
    # Adjust font size back to last fitting size
    font_description.set_size((font_size - 1) * Pango.SCALE)
    layout.set_font_description(font_description)
    
    # Calculate position to center the text
    text_width, text_height = layout.get_pixel_size()
    context.move_to((box_width - text_width) / 2, (box_height - text_height) / 2)
    
    # Render the text onto the surface
    PangoCairo.update_layout(context, layout)
    PangoCairo.show_layout(context, layout)
    
    # Write the output to a PNG file
    return to_pil(surface)


def fit_image(img, width, height):
    ret_img = Image.new("RGBA", (width, height))
    orig_width, orig_height = img.size
    ratio = min(float(width) / orig_width, float(height) / orig_height) * .85
    print(ratio)
    new_size = int(orig_width * ratio), int(orig_height * ratio)
    print(new_size)
    img = img.resize(new_size)
    offset = (width - new_size[0]) // 2, (height - new_size[1]) // 2
    print(offset)
    ret_img.paste(img, offset)
    return ret_img


# colors should be passed as rgb tuples
def generate_ad_visual(ad_text, product_image, width, height, bg_color, text_color):
    ret_img = Image.new("RGB", (width, height), color=bg_color)
    if width > height:
        img_height = height
        img_width = int(width * .4)
        img_offset = 0, 0
        txt_height = height
        txt_width = width - img_width
        txt_offset = img_width, 0
    else:
        img_height = int(height * .4)
        img_width = width
        img_offset = 0, height - img_height
        txt_height = height - img_height
        txt_width = width
        txt_offset = 0, 0

    img_segment = fit_image(crop_to_visible(product_image), img_width, img_height)
    text_segment = fit_text(txt_width, txt_height, ad_text, font_color=text_color)
    ret_img.paste(img_segment, img_offset, img_segment)
    ret_img.paste(text_segment, txt_offset, text_segment)
    
    return ret_img
