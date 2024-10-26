from abc import ABC, abstractmethod
import numpy as np
from openai import OpenAI

class AIBox(ABC):
    def __init__(self) -> None:
        pass
    
    @abstractmethod
    def embedding_from_text(self, text: str) -> np.ndarray:
        pass 
    
    @abstractmethod
    def embedding_from_file(self, file_path: str) -> np.ndarray:
        pass
    
    @abstractmethod
    def ad_text(self, product_name: str, 
                product_description: str,
                user_keywords: list[str],
                instructions: str) -> str:
        "Custom instructions need to be suppied for generating text"
        pass
    
    @abstractmethod
    def keywords(self, text: str, num_keywords: int) -> list[str]:
        """
        This method generates keywords from a given text
        text.   
        NOTE: model might not return exactly num_keywords     
        """
        pass
    
class OpenAIBox(AIBox):
    def __init__(self, openai_key: str) -> None:
        self.openai_client = OpenAI(api_key=openai_key)
        super().__init__()
        
    def embedding_from_text(self, text: str, model="text-embedding-3-small") -> np.ndarray:
        response = self.openai_client.embeddings.create(
            input=text,
            model=model,
        )
        
        embedding = response.data[0].embedding
        return np.array(embedding)
    
    def embedding_from_file(self, file_path: str, model="text-embedding-3-small") -> np.ndarray:
        with open(file_path, 'r') as file:
            text = file.read()
        return self.embedding_from_text(text, model)
    
    def ad_text(self, 
                product_name: str,
                product_description: str,
                user_keywords: list[str],
                instructions: str,
                model = "gpt-4o-mini") -> str:
        prompt = f"""Product name: {product_name}\n
                    Product description: {product_description}\n
                    User keywords: {user_keywords}\n
                    """
        response = self.openai_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": instructions},
                {"role": "user", "content": prompt}
            ]
        )
        if response.choices[0].finish_reason != "stop":
            raise Exception("OpenAI did not finish generating the text")
        return response.choices[0].message.content
    
    def keywords(self, text: str, num_keywords: int, model="gpt-4o-mini") -> list[str]:
        """
        :param model: OpenAI completions model to use
        """
        response = self.openai_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": f"Generate exactly {num_keywords} for given text. Separate keywords by commas. Do not output anything else."},
                {"role": "user", "content": text}
            ],
        )
        if response.choices[0].finish_reason != "stop":
            raise Exception("OpenAI did not finish generating the text")
        
        return response.choices[0].message.content.split(",")
