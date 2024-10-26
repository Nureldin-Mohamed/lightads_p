from flask import Flask, request, send_file, render_template
import redis
import jsonschema
from openai import OpenAI, OpenAIError
from PIL import Image
from io import BytesIO

from legacy.products import find_similar
from legacy.segmentation import generate_ad_visual, get_dominant_color, get_complementary_color
from legacy.adtext import generate_ad_text


app = Flask(__name__)
redis_client = redis.Redis(host="localhost", port=6379, decode_responses=True)
openai_client = OpenAI()


user_details_schema = {
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "embedding": {
      "type": "array",
      "items": {
        "type": "number"
      },
      "minItems": 1536,
      "maxItems": 1536
    },
    "keywords": {
        "type": "array",
        "items": {
            "type": "string",
        },
        "minItems": 1
    },
  },
  "required": ["embedding", "keywords"],
}

@app.route('/get_banner', methods=['GET'])
def get_banner():
    raw_input = request.json
    width = int(request.args.get("width"))
    height = int(request.args.get("height"))
    try:
        jsonschema.validate(raw_input, user_details_schema)
    except jsonschema.ValidationError:
        Flask.abort(400, description="Bad JSON input")
    
    try:
        product_description, product_image_link = find_similar(raw_input["embedding"], 1, redis_client, "embedding")
    except RuntimeError:
        Flask.abort(500, description="Failed to retrieve any products from database")
    
    # for now, we'll use locally stored images, which might be not good, but works for now
    product_img = Image.open(product_image_link, 'r')
    main_color = get_dominant_color(product_img)
    contrast_color = get_complementary_color(main_color)
    
    image_caption = generate_ad_text(product_description, raw_input["keywords"], openai_client)
    
    # print(image_caption, product_img, width, height, main_color, contrast_color)
    ad_visual = generate_ad_visual(image_caption, product_img, width, height, main_color, contrast_color)
    img_io = BytesIO()
    ad_visual.save(img_io, 'JPEG', quality=80)
    img_io.seek(0)
    return send_file(img_io, mimetype="image/jpeg")
  
@app.route('/test-ad', methods=['GET'])
def get_main() -> str:
  return render_template(
    template_name_or_list="template1.html", 
    width=728, 
    height=90, 
    product_name="Yorkshire Tea",
    product_link="https://www.amazon.com/dp/B007NIC6FE?amp=&crid=1OW7ACEKT5MDE&sprefix=yorks",
    product_image_link="https://m.media-amazon.com/images/I/81GpUDHOMYL._SX679_.jpg",
    supplemental_image_link="https://media.istockphoto.com/id/1395191574/photo/black-led-tv-television-screen-blank-isolated.jpg?s=612x612&w=0&k=20&c=ps14JZJh0ebkINcbQyHFsR1J5EC7ozkj_WO7Fh_9IOI=",
  )
    
if __name__ == '__main__':
    app.run(debug=True)