import numpy as np
import requests
import json
import io
from PIL import Image

if __name__ == "__main__":
    test_embedding = np.random.rand(1536)
    keywords = ["television", "rhinoceros", "toilet paper"]
    user = {
        "embedding": test_embedding.tolist(),
        "keywords": keywords
    }
    response = requests.get("http://localhost:5000/get_banner", params={"width": 1000, "height": 300}, data=json.dumps(user), headers={"Content-type": "application/json"})
    # print(response.request.body)
    img = Image.open(io.BytesIO(response.content))
    img.save("img/res.png")