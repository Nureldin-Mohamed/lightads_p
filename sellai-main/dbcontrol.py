import json
import jsonschema
import redis
from redis import Redis
from redis.commands.search.field import TextField, VectorField
from redis.commands.search.indexDefinition import IndexDefinition, IndexType
from redis.commands.search import Search
from redis.commands.search.query import Query
from openai import OpenAI
import numpy as np
from PIL import Image
from typing import Dict, Optional, Tuple, Any
from dotenv import load_dotenv
import datetime
from aibox import AIBox

# FT.CREATE productIdx ON JSON PREFIX 1 product: SCHEMA $.description AS description TEXT $.image_link AS image_link TEXT $.embedding AS embedding VECTOR FLAT 6 TYPE FLOAT32 DIM 1536 DISTANCE_METRIC COSINE

# Schemas
input_product_schema = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "name": {
            "type": "string"
        },
        "description": {
            "type": "string"
        },
        "image_link": {
            "type": "string",
            "format": "uri"
        },
    },
    "required": ["name", "description", "image_link"],
}

storage_product_schema = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "name": {
            "type": "string"
        },
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
    "required": ["name", "description", "image_link", "embedding"],
}

user_schema = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "keywords": {
            "type": "array",
            "items": {
                "type": "string",
            }
        },
        "embedding": {
            "type": "array",
            "items": {
                "type": "number"
            },
            "minItems": 1536,
            "maxItems": 1536
        },
        # last_refreshed_db lets know when the user object was last refreshed
        "last_refreshed": {
            "type": "string",
            "format": "date-time",
        }
    },
    "required": ["keywords"],
}


def _create_redis_index(redis_client: Redis, index_name) -> None:
    """
    Throws exception if index already exists
    """
    try:
        # Check if the index already exists
        search_client = Search(client=redis_client, index_name=index_name)
        try:
            search_client.info()  # If this succeeds, the index exists
            raise RuntimeError(f"Index '{index_name}' already exists.")
        except redis.exceptions.ResponseError:
            pass  # If it raises an error, the index does not exist

        # Define the index schema
        
        schema = (
            TextField("$.name", as_name="name"),
            TextField("$.description", as_name="description"),
            TextField("$.image_link", as_name="image_link"),
            VectorField("$.embedding", as_name="embedding", 
                        algorithm="FLAT", 
                        attributes={"TYPE": "FLOAT32", "DIM": 1536, "DISTANCE_METRIC": "COSINE", "INITIAL_CAP": 1000})
        )

        # Create the index
        search_client.create_index(schema, definition=IndexDefinition(prefix=["product:"], index_type=IndexType.JSON))
        print(f"Index '{index_name}' created successfully.")
        
    except Exception as e:
        print(e)
        raise RuntimeError(f"Failed to create index '{index_name}': {e}")



class Product:
    def __init__(self, name: str, description: str, image_link: str, embedding: Optional[np.ndarray] = None) -> None:
        self.name = name
        self.description = description
        self.image_link = image_link
        self.embedding = embedding

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "image_link": self.image_link,
            "embedding": self.embedding.tolist() if self.embedding is not None else None
        }

    @classmethod
    def from_json(cls, json_data: Dict[str, Any]) -> "Product":
        jsonschema.validate(json_data, input_product_schema)
        
        return cls(
            name=json_data['name'],
            description=json_data['description'],
            image_link=json_data['image_link']
        )

    def refresh(self, aibox: AIBox) -> None:
        """Generates an embedding for the product"""
        text = self.description.replace("\n", " ")
        self.embedding = aibox.embedding_from_text(text)

    def save_image(self, key: str) -> None:
        """
        Takes image key as an input and saves image to image storage database
        NOTE: currently assumes that self.image_link is link to a file, key is also link to a file
        """
        location = key
        Image.open(self.image_link).save(location)
        self.image_link = location


class RedisProductStore:
    def __init__(self, redis_client: Redis) -> None:
        self.redis_client = redis_client
        try:
            _create_redis_index(self.redis_client, "productIdx")
        except RuntimeError:
            print("RedisProductStore: product index already exists, skipping creation")        

    def __get_next_product_key(self) -> str:
        """
        This function increases product counter in the database and returns a new product ID.
        This function goes against principles of good programming.
        """
        return "product:" + str(self.redis_client.incr("product_counter"))

    def save_product(self, product: Product, aibox: AIBox) -> None:
        """
        Saves product object to database 
        """
        # Generate embedding
        product.refresh(aibox)

        # Validate product
        storage_product_dict = product.to_dict()
        jsonschema.validate(storage_product_dict, storage_product_schema)

        # Save image and update link
        key = self.__get_next_product_key()
        product.save_image("db-img/" + key + ".png")

        # Save product to Redis
        self.redis_client.json().set(key, "$", storage_product_dict)

    def find_similar_from_embedding(self, embedding: np.ndarray, k: int, vector_field: str) -> Tuple[str, str]:
        query: Query = (
            Query(f"*=>[KNN {k} @{vector_field} $vec as score]")
            .return_fields("description", "image_link", "score")
            .sort_by("score")
            .paging(0, k)
            .dialect(2)
        )

        query_params: Dict[str, bytes] = {
            "vec": embedding.astype(np.float32).tobytes()
        }

        res = self.redis_client.ft("productIdx").search(query, query_params).docs
        if not res:
            raise RuntimeError("Failed to retrieve any matching documents from Redis index")
        return res[0].description, res[0].image_link
    

class User:
    def __init__(self, keywords, embedding: Optional[np.ndarray], last_refreshed = datetime.datetime.now()) -> None:
        self.keywords = keywords
        self.embedding = embedding
        self.last_refreshed = last_refreshed
        
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "keywords": self.keywords,
            "embedding": self.embedding.tolist() if self.embedding is not None else None,
            "last_refreshed": self.last_refreshed.isoformat()
        }
        
    @classmethod
    def from_json(cls, json_data: Dict[str, Any]) -> "User":
        jsonschema.validate(json_data, user_schema)
        return cls(
            keywords=json_data['keywords'],
            embedding=json_data['embedding'] if 'embedding' in json_data else None,
            last_refreshed=datetime.datetime.fromisoformat(json_data['last_refreshed']) if 'last_refreshed' in json_data else None
        )

    def refresh(self, aibox: AIBox) -> None:
        """Generator an embedding for the user, refreshes the last_refreshed field"""
        self.embedding = aibox.embedding_from_text(" ".join(self.keywords))
        self.last_refreshed = datetime.datetime.now()
        
    def push_keywords(self, keywords: list) -> None:
        """So far this function is simply a placeholder that does not work efficiently"""
        self.keywords.extend(keywords)
    
    
class RedisUserStore:
    def __init__(self, redis_client: Redis) -> None:
        self.redis_client = redis_client
            
    def __get_next_user_key(self) -> str:
        """
        This function increases user counter in the database and returns a new user ID.
        This function goes against principles of good programming.
        """
        return "user:" + str(self.redis_client.incr("user_counter"))
    
    def save_user(self, user: User, aibox: AIBox) -> None:
        """
        Saves user object to database 
        """
        # Generate embedding
        user.refresh(aibox)

        # Validate user
        storage_user_dict = user.to_dict()
        jsonschema.validate(storage_user_dict, user_schema)

        # Save user to Redis
        key = self.__get_next_user_key()
        self.redis_client.json().set(key, "$", storage_user_dict)
        

# if __name__ == "__main__":
#     load_dotenv()
#     openai_client = OpenAI()
#     redis_client = Redis(host="localhost", port=6379, decode_responses=True)

#     product_json: Dict[str, Any] = {
#         "description": """Taylors of Harrogate Yorkshire Red, 240 Teabags
#             Rich, full-bodied blend makes an ideal breakfast tea or afternoon delight.
#             Ingredients: Black tea.
#             For the perfect cup use one tea bag. Add freshly boiled water and infuse for 4-5 minutes. Serve pure or with milk.
#             240 tea bags.
#             Taylors of Harrogate is Carbon Neutral Certified, a member of the Ethical Tea Partnership, and Rainforest Alliance Certified.
#         """,
#         "image_link": "img/tea.png",
#     }

#     product = Product.from_json(product_json)
#     product.refresh(openai_client)  
    
    
#     user_json = {
#         "keywords": ["Black tea", "TV shows", "toilet paper", "bananas"],
#     }
    
#     user = User.from_json(user_json)
#     user.refresh(openai_client)
    
#     # dot product of user and product embeddings
#     print(np.dot(user.embedding, product.embedding))
    
#     product_store = RedisProductStore(redis_client)
#     product_store.save_product(product, openai_client)
    
#     user_store = RedisUserStore(redis_client)
#     user_store.save_user(user, openai_client)
#     # Example of finding similar products
#     # test_embedding: np.ndarray = np.random.rand(1536)
#     # print(store.find_similar(test_embedding, 1, "embedding"))
