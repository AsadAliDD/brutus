from dotenv import load_dotenv
import os 
from openai import OpenAI


load_dotenv()
api_key = os.getenv('open_api_key')
client = OpenAI(api_key=api_key)

# Change this to to 
profile='''Key points about Dwight:
Loves beets and owns a beet farm.
Fascinated by martial arts.
Huge fan of "Battlestar Galactica."
Date of birth: January 20, 1970.
Pets: Mose Schrute (cousin), several cats.
Favorite color: Brown.
Likely passwords: "BeetFarm1970", "GalacticaFan", "SenseiSchrute".'''

    

def generate_password_stems(prompt, max_tokens=1500):
    response = client.chat.completions.create(model="gpt-4",
    messages=[
        {"role": "system", "content": "You are a password profiler. Based on the information provided by the user, generate pasword stems. Return only the stems without any numbering"},
        {"role": "user", "content": prompt}
    ],
    max_tokens=max_tokens,
    n=1,
    stop=None,
    temperature=0.1)
    return response.choices[0].message.content



def save_stems(password_stems):
    # Save the password stems to a file
    with open('./PasswordLists/password_stems.txt', 'w') as file:
        file.write(password_stems)

def main():
    prompt=f'Generate a list of 5 custom password stems based on the following information:\n{profile}'
    password_stems = generate_password_stems(prompt)
    print (password_stems)
    save_stems(password_stems)


if __name__ == "__main__":
    main()
