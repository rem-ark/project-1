import roblox.Utils as Utils
import roblox.User.Internal as Internal
from typing import Union
import json

def GetFunds(GroupID: int) -> Union[int, dict]:
    try:
        response = Internal.CurrentCookie.get(f"{Utils.EconomyURL}/groups/{GroupID}/currency/")
        return response.json()['robux']
    except:
        return 0


def Payout(GroupID: int, targetUserID: int, RobuxAmount: int) -> tuple[bool, dict]:
    url = f'https://groups.roblox.com/v1/groups/{GroupID}/payouts'
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json'
    }
    data = {
        "PayoutType": 1,
        "Recipients": [
            {
                "recipientId": targetUserID,
                "recipientType": 0,
                "amount": RobuxAmount
            }
        ]
    }

    response = Internal.CurrentCookie.post(url, headers=headers, data=json.dumps(data))

    if response.status_code == 200:
        return True, response.json()
    else:
        return False, response.json()
