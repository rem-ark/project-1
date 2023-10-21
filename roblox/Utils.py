import requests,os
import roblox.User.Internal

TestCookie = ""


#URL List

MobileAPI = "https://www.roblox.com/mobileapi/"
FriendsAPI = "https://friends.roblox.com/v1/users/"
APIURL = "https://api.roblox.com/"
UserAPI = "https://api.roblox.com/users/"
UserAPIV1 = "https://users.roblox.com/v1/users/"
GroupAPIV1 = "https://groups.roblox.com/v1/groups/"
GroupAPIV2 = "https://groups.roblox.com/v2/"
EconomyURL = "https://economy.roblox.com/v1/"
EconomyURLV2 = "https://economy.roblox.com/v2/"
InventoryURL = "https://inventory.roblox.com/v2/assets/"
Inventory1URL = "https://inventory.roblox.com/v1/users/"
SettingsURL = "https://www.roblox.com/my/settings/json"
PrivateMessageAPIV1 = "https://privatemessages.roblox.com/v1/"
GamesAPI = "https://games.roblox.com/v1/"
DevelopAPIV2 = "https://develop.roblox.com/v2/"
GameAuthUrl = "https://auth.roblox.com/v1/authentication-ticket/"
ThumnnailAPIV1 = "https://thumbnails.roblox.com/v1/"



Version = "0.2.21"

def CheckCookie(Cookie: str = None) -> str:
    """
    If you want to check the current used cookie just run the function without any variable, if you wish to check a specific cookie then enter the cookie as a string
    """
    try:
        if(Cookie == None):
            session = roblox.User.Internal.CurrentCookie
        else:
            session = requests.session()
            CurrentCookie = {'.ROBLOSECURITY': Cookie}
            requests.utils.add_dict_to_cookiejar(session.cookies, CurrentCookie)
            Header = session.post('https://catalog.roblox.com/')
            session.headers['X-CSRF-TOKEN'] = Header.headers['X-CSRF-TOKEN']
        response = session.get(MobileAPI + 'userinfo')
        try:
            Temp = response.json()['UserID']
            #return response.json()
            return "Valid Cookie"
        except:
            return "Invalid Cookie"
    except:
        return "No Cookie Set"
