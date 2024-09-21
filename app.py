from flask import Flask
from openai import OpenAI
from dotenv import load_dotenv
import requests
import json
import os
import re

load_dotenv()

RELEVANT_ACC_INFO_KEYS = { "account_id", "smart_contract", "simple_account", "classification" }

# OpenAI client
oai_client = OpenAI(
    organization=os.getenv("OAI_ORG"),
    project=os.getenv("OAI_PROJECT"),
)

def get_event_history(wallet_addr):
    response = requests.get(f'https://pikespeak.ai/api/event-historic/account/{wallet_addr}?type=&limit=50&offset=0&filters=&nearMinAmount=0')
    return response.json()

def get_account_info(account_id):
    response = requests.get(f'https://pikespeak.ai/api/infos/{account_id}')
    return response.json()


app = Flask(__name__)


@app.route("/ping")
def ping():
    return "<p>Pong!</p>"

@app.route("/account/<wallet_addr>")
def explain_account_activity(wallet_addr):

    # Get event history from pikespeak
    history = get_event_history(wallet_addr)
    history_str = json.dumps(history)

    completion = oai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "extract a list of all wallet addresses appearing in this blockchain transaction history data. Addresses must be comma-separated and in one line"},
            {
                "role": "user", "content": f"{history_str}"}
        ]
    )

    addresses = completion.choices[0].message.content.split(",")

    print(addresses)

    # Get some data about the addresses from PikesPeak
    addr_to_info = {}
    for addr in addresses:
        addr_to_info[addr] = get_account_info(addr)
        addr_to_info[addr] = {k: v for k, v in addr_to_info[addr].items() if k in RELEVANT_ACC_INFO_KEYS }

    completion = oai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Eli5 and summarize what a NEAR blockchain wallet address is doing based on its event history, do not mention technical details. Be concise, and only include details relevant to the main intention or startegy of the user. Response must be in HTML format"},
            {
                "role": "user",
                "content": f"Helpful information:\nEvent history data: {addr_to_info}\nAddress info: {addr_to_info}"
            }
        ]
    )

    return { "gpt_res": completion.choices[0].message.content}

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)