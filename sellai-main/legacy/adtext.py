from openai import OpenAI
import os

# openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# product_description = """Taylors of Harrogate Yorkshire Red, 240 Teabags
# Rich, full-bodied blend makes an ideal breakfast tea or afternoon delight.
# Ingredients: Black tea.
# For the perfect cup use one tea bag. Add freshly boiled water and infuse for 4-5 minutes. Serve pure or with milk.
# 240 tea bags.
# Taylors of Harrogate is Carbon Neutral Certified, a member of the Ethical Tea Partnership, and Rainforest Alliance Certified.
# """

# client_preferences = ["television", "toilet paper"]


def generate_ad_text(product_description, client_preferences, openai_client):
  message = f"There is a product that has following description: {product_description}.\nThere is a client which is interested in following: {client_preferences}.\n Generate one caption for such client."
  response = openai_client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
      {"role": "system", "content": "You generate short, catchy, attractive captions for web banner ads. Actively incorporate client's preferences into ad in non-intrusive, yet organic way. Do not highlight aspects of the product unless it intersects with user's preferences or unless you can find a way to make it intersect verbally in organic way. Use wording that evokes imagery and context. Do not use emojis or non-text characters. Word count should not exceed 10."},
      {"role": "user", "content": message},
    ]
  )
  return response.choices[0].message.content


# print(generate_ad_text(product_description, client_preferences, openai_client))