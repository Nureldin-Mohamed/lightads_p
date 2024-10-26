from openai import OpenAI
import json
import jsonschema
import redis
from redis.commands.search.query import Query
import numpy as np
from PIL import Image
import os
from dotenv import load_dotenv

# FT.CREATE productIdx ON JSON PREFIX 1 product: SCHEMA $.description AS description TEXT $.image_link AS image_link TEXT $.embedding AS embedding VECTOR FLAT 6 TYPE FLOAT32 DIM 1536 DISTANCE_METRIC COSINE

inputUserSchema = {
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "preferences": {
      "type": "string"
    },
    "image_link": {
      "type": "string",
      "format": "uri"
    },
  },
  "required": ["description", "image_link"],
}

inputProductSchema = {
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "description": {
      "type": "string"
    },
    "image_link": {
      "type": "string",
      "format": "uri"
    },
  },
  "required": ["description", "image_link"],
}

storageProductSchema = {
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "description": {
      "type": "string"
    },
    "image_link": {
      "type": "string",
      "format": "uri"
    },
    "embedding": {
      "type": "array",
      "items": {
        "type": "number"
      },
      "minItems": 1536,
      "maxItems": 1536
    }
  },
  "required": ["description", "image_link", "embedding"],
}


def get_embedding(text, openai_client, model="text-embedding-3-small"):
   text = text.replace("\n", " ")
   return openai_client.embeddings.create(input = [text], model=model).data[0].embedding


def add_image_to_db(key, img):
  location = f"/mnt/c/Users/gosha/Documents/sellai/db-img/{key}.png"
  img.save(location)
  return location
  
  
# takes inputProductSchema as input
# for now, assumes that we deal with file images
def redis_add_json_product(product, redis_client):
    try:
        jsonschema.validate(product, inputProductSchema)
    except jsonschema.ValidationError:
        print("invalid object passed to redis_add_json_product")
        return -1
    
    key = "product:" + str(redis_client.incr("product_counter"))

    embedding = get_embedding(product['description'], openai_client)
    product['embedding'] = embedding
    

    try:
        jsonschema.validate(product, storageProductSchema)
    except jsonschema.ValidationError:
        print("invalid object returned by OpenAI embeddings")
        return -1
    
    
    new_link = add_image_to_db(key, Image.open(product['image_link']))
    product['image_link'] = new_link
    redis_client.json().set(key, "$", product)


# get float vector from openai api
def find_similar(embedding, k, redis_client, vector_field):
    query = (
        Query(f"*=>[KNN {k} @{vector_field} $vec as score]")
        .return_fields("description", "image_link", "score")
        .sort_by("score")
        .paging(0, k)
        .dialect(2)
    )

    query_params = {
        "vec": np.array(embedding, dtype=np.float32).tobytes()
    }
    
    res = redis_client.ft("productIdx").search(query, query_params).docs
    if not res:
      raise RuntimeError("Failed to retrieve any matching documents from Redis index")
    return res[0].description, res[0].image_link



if __name__ == "__main__":
  # openai_api_key = os.getenv("OPENAI_API_KEY")
  # print(openai_api_key)
  load_dotenv()
  openai_client = OpenAI()
  redis_client = redis.Redis(host="localhost", port=6379, decode_responses=True)
  
  product = {
      "description": """Taylors of Harrogate Yorkshire Red, 240 Teabags
        Rich, full-bodied blend makes an ideal breakfast tea or afternoon delight.
        Ingredients: Black tea.
        For the perfect cup use one tea bag. Add freshly boiled water and infuse for 4-5 minutes. Serve pure or with milk.
        240 tea bags.
        Taylors of Harrogate is Carbon Neutral Certified, a member of the Ethical Tea Partnership, and Rainforest Alliance Certified.
        """,
      "image_link": "img/tea.png",
  }
  print(redis_add_json_product(product, redis_client))

  # test_embedding = np.random.rand(1536)
  # print(find_similar(test_embedding, 1, redis_client, "embedding"))
