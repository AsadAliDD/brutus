from user_profile import profile
from dotenv import load_dotenv
import os 
import openai



def load_api_key():
    load_dotenv()
    api_key = os.getenv('open_api_key')
    openai.api_key = api_key

def generate_password_stems(prompt, max_tokens=1500):
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=max_tokens,
        n=1,
        stop=None,
        temperature=0.7,
    )
    return response['choices'][0]['message']['content']

# Define the prompt based on the information about Dwight
prompt = """
Generate a list of 1000 custom password stems based on the following information about Dwight:
1. Loves beets and owns a beet farm.
2. Fascinated by martial arts.
3. Huge fan of "Battlestar Galactica."
4. Date of birth: January 20, 1970.
5. Pets: Mose Schrute (cousin), several cats.
6. Favorite color: Brown.
7. Likely passwords: "BeetFarm1970", "GalacticaFan", "SenseiSchrute".
"""

# Generate the password stems
password_stems = generate_password_stems(prompt)
print (password_stems)
