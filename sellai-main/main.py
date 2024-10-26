from flask import Flask, request, send_file, render_template
import redis
from dbcontrol import Product, User
from templates.basicxmltemplate.basicxmltemplate import BasicXMLTemplate
from templates.basichtmltemplate.basichtmltemplate import BasicHTMLTemplate
from openai import OpenAI, OpenAIError
from PIL import Image
from visualnode import vnode_tree_from_file, VNode
from legacy.products import get_embedding
from dataclasses import dataclass
from aibox import OpenAIBox
import os
from dotenv import load_dotenv

app = Flask(__name__)
redis_client = redis.Redis(host="localhost", port=6379, decode_responses=True)


# # this one returns page
# @app.route('/switchuser', methods=['GET'])
# def switch_user():
#   return render_template("switchuser.html")

# # this one returns page
# @app.route('/blog', methods=['GET'])
# def blog():
#   return render_template("blog.html")


if __name__ == "__main__":
    load_dotenv()
    
    aibox = OpenAIBox(openai_key=os.getenv("OPENAI_KEY"))
    
    product_json = {
        "name": "Yorkshire Tea",
        "description": """Yorkshire Tea is a black tea blend produced by Taylors of Harrogate. It is the most popular traditional black tea brand sold in the UK. It is exported to over 40 countries. It is the best-selling brand of tea in the UK and is one of the top three best-selling brands of tea in the world.""",
        "image_link": "img/tea_ed.png",
    }
    user_json = {
        "keywords": ["tea", "TV shows", "royal family", "cacti"],
    }
    product = Product.from_json(product_json)
    user = User.from_json(user_json)
    product.refresh(aibox)
    user.refresh(aibox)
    
    slogan = aibox.ad_text(product.name,
                           product.description,
                           user.keywords,
                           "Generate a short slogan for the product ad. Slogan should reference both product and user preferences where appropriate. Slogan should be catchy and memorable. Slogan should be less that 10 words in length. Output just slogan and nothing else. Do NOT wrap the slogan into quotation marks.")
    # template = BasicXMLTemplate(product,
    #                      (800, 200),
    #                      slogan,
    #                      (255, 0, 0, 255),
    #                      "some_key")
    template = BasicHTMLTemplate(product,
                                 (800, 144),
                                 slogan,
                                 (255, 0, 0, 255))
    img = template.compose()
    img.save("img/res.png")