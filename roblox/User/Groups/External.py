import requests

def GetGroups(UserID: int) -> dict:
    """
    Returns the list of groups a user is in
    [Name],[ID]
    """
    response = requests.get(f"https://groups.roblox.com/v2/users/{UserID}/groups/roles")

    return response.json()['data']
