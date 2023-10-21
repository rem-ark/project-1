import math
import queue
import time
from os import getenv, path
from io import BytesIO

import roblox

import interactions
import requests
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv

# Loading project specific variables
load_dotenv()

# Objects
bot = interactions.Client(token=getenv("DISCORD_TOKEN"),
                          activity=interactions.Activity(
                              name="to /help",
                              type=interactions.ActivityType.LISTENING
                          ),
                          status=interactions.Status.ONLINE,
                          intents=interactions.Intents.DEFAULT |
                                  interactions.Intents.GUILD_MEMBERS |
                                  interactions.Intents.GUILD_MESSAGES |
                                  interactions.Intents.MESSAGE_CONTENT, send_command_tracebacks=False)

roblox.User.Internal.SetCookie(getenv("ROBLOX_COOKIE"))

# Variables
owner_ids = [int(value) for value in getenv("OWNER_IDS").split(",")]
allowed_guilds = [int(value) for value in getenv("ALLOWED_GUILDS").split(",")]

roblox_group_id = int(getenv("ROBLOX_GROUP_ID"))
roblox_group_name = "None"
roblox_group_description = "None"
roblox_group_emblem_url = "None"
interval = 15

bot_closing = False
purchase_status = False

timeout_table = {
    # SampleCase:
    "User id (str) here": "buy command last used time (time object) here"
}

purchase_queue = queue.Queue()
group_balance = 0

robux_price = 0

recipient_id = 0
discount = 0

thanksroom_id = 0
guideroom_id = 0
buy_category_id = 0

purchase_role_id = 0
boost_role_id = 0

minimum_purchasable = 0
maximum_purchasable = 0


# Functions
def tax(amount: int):
    return math.floor((amount * 20) / 19) + 1


def create_final_image(background_image_path, icon_url, username, requested_robux, total_balance, output_image_path):
    # Open the background image
    background_image = Image.open(background_image_path)

    # Download the icon image
    response = requests.get(icon_url)
    # Create an image object from the downloaded data
    icon_image = Image.open(BytesIO(response.content))

    # Resize the icon image
    new_size = (48, 48)  # Specify the new size in pixels
    icon_image = icon_image.resize(new_size)

    # Create a new blank image with the dimensions of the background image
    new_image = Image.new("RGBA", background_image.size)

    # Paste the background image onto the new image
    new_image.paste(background_image, (0, 0))

    # Paste the icon image onto the new image at the desired position
    position = (5, 11)  # Specify the position where you want to place the image
    new_image.paste(icon_image, position, icon_image)

    # Set up the text settings
    text_color = (255, 255, 255)
    font_size = 15
    font = ImageFont.truetype(path.join("resources", "arial.ttf"), font_size)
    draw = ImageDraw.Draw(new_image)

    # Draw the text on the image
    draw.text((60, 23), f"{username}", text_color, font=font)
    draw.text((802, 28), f"{requested_robux}", text_color, font=font)
    draw.text((868, 69), f"{requested_robux}", text_color, font=font)
    draw.text((832, 90), f"{total_balance}", text_color, font=font)

    # Save the final image
    new_image.save(output_image_path)

    # Returning the final image path
    return output_image_path


async def after_payout(initial_channel_id: int, discord_id: int = None, username: str = None, robux: int = None,
                       photo_url: str = None, error: bool = False, error_message: str = None):
    channel = await bot.fetch_channel(channel_id=initial_channel_id)

    if error:
        if not error_message:
            await channel.send(
                "Error, for group payout you need be in group for 14 days. A moderator will contact you soon")
            await channel.edit(name="14-days-not-completed")
        else:
            await channel.send(error_message)
            await channel.edit(name=error_message)
        return

    global thanksroom_id
    global guideroom_id
    global group_balance

    # Sending the image embed in GUIDEROOM channel
    guide_channel = await bot.fetch_channel(channel_id=guideroom_id)
    final_file_path = create_final_image(background_image_path=path.join("resources", "background.png"),
                                         icon_url=photo_url,
                                         username=username,
                                         requested_robux=robux,
                                         total_balance=group_balance,
                                         output_image_path=path.join("resources", "final_image.png"))

    await guide_channel.send(content=f"Purchase successful <@!{discord_id}>",
                             file=final_file_path)
    await guide_channel.send(file=path.join("resources", "banner.gif"))

    # Sending final message in the purchase channel
    thanks_channel = await bot.fetch_channel(channel_id=thanksroom_id)
    await channel.send(
        f"<@!{discord_id}> your Payout was completed, send you words of graditude in {thanks_channel.mention}")

    time.sleep(10)
    await channel.delete("Successful payout")


# Creating and starting background thread for purchase processing
@interactions.Task.create(interactions.IntervalTrigger(seconds=interval))
async def purchase_loop():
    global roblox_group_id
    global purchase_status
    global group_balance

    if purchase_queue.empty():
        return

    # Collecting information from the queue
    username, userid, requested_robux, photo_url, discord_id, initial_channel_id = purchase_queue.get()

    # Doing payouts
    success, message = roblox.User.Groups.Internal.Payout(roblox_group_id, userid, requested_robux)

    if not success:
        error_code = int(message['errors'][0]['code'])
        if error_code == 34:
            await after_payout(initial_channel_id=initial_channel_id, error=True)
        else:
            await after_payout(initial_channel_id=initial_channel_id, error=True,
                               error_message=message['errors'][0]['message'])
        group_balance += requested_robux
    else:
        await after_payout(initial_channel_id, discord_id, username, requested_robux, photo_url)

    # Declaring the task is done
    purchase_queue.task_done()


# Bot Error
@interactions.listen()
async def on_command_error(ctx: interactions.errors):
    print(ctx)


# Bot Events
@interactions.listen()
async def on_startup():
    global roblox_group_id
    global roblox_group_name
    global roblox_group_description
    global group_balance
    global roblox_group_emblem_url
    global purchase_status

    purchase_loop.start()
    print("Purchase Loop: Started ")

    print(f"Account name: {roblox.User.Internal.Username}")

    roblox_group_name = roblox.Group.External.GetName(roblox_group_id)
    roblox_group_description = roblox.Group.External.GetDescription(roblox_group_id)
    group_balance = roblox.User.Groups.Internal.GetFunds(roblox_group_id)
    roblox_group_emblem_url = roblox.Group.External.GetEmblem(roblox_group_id)

    print(f"Group name: {roblox_group_name}")
    print(f"Group description: {roblox_group_description}")
    print(f"Group balance: {group_balance}")
    print(f"Group emblem url: {roblox_group_emblem_url}")

    print(f"Bot name: {bot.app.name}")

    # Enabling the purchase commands
    purchase_status = True


# Slash Commands
@interactions.slash_command(
    name="ping",
    description="Sends the bot latency",
    scopes=allowed_guilds
)
async def ping(ctx: interactions.SlashContext):
    if bot_closing:
        await ctx.send("The bot is closing right now, so the commands are disabled.\nSorry for inconvenience")
        return

    await ctx.send(f"Pong {round(bot.latency, 2)}ms !!")


@interactions.slash_command(
    name="shutdown",
    description="Shuts the bot down",
    scopes=allowed_guilds
)
async def shutdown(ctx: interactions.SlashContext):
    global bot_closing
    if bot_closing:
        await ctx.send("The bot is closing right now, so the commands are disabled.\nSorry for inconvenience")
        return

    if ctx.author.id in owner_ids:
        global purchase_queue
        bot_closing = True
        await ctx.send(
            f"Shutting down the bot after payment is completed.\nUnprocessed payments: `{purchase_queue.qsize()}`",
            ephemeral=True)
        purchase_queue.join()
        await ctx.send("All the payment are processed, bot shutdown completed", ephemeral=True)
        await bot.stop()


@interactions.slash_command(
    name="setprice",
    description="Set how much 1 Robux worth in credit",
    options=[
        interactions.SlashCommandOption(
            type=interactions.OptionType.INTEGER,
            name="amount",
            description="The amount to set",
            required=True
        )
    ],
    scopes=allowed_guilds
)
async def setprice(ctx: interactions.SlashContext, amount: int):
    if bot_closing:
        await ctx.send("The bot is closing right now, so the commands are disabled.\nSorry for inconvenience")
        return

    if ctx.author.id not in owner_ids:
        await ctx.send("It seems that you dont have permission to access this command", ephemeral=True)
        return

    global robux_price
    robux_price = amount
    await ctx.send(f"The price for 1 robux has been set to {robux_price}")


@interactions.slash_command(
    name="setrecipient",
    description="Set the user that will receive the credit",
    options=[
        interactions.SlashCommandOption(
            type=interactions.OptionType.USER,
            name="user",
            description="The user who will receive the credit",
            required=True
        )
    ],
    scopes=allowed_guilds
)
async def setrecipient(ctx: interactions.SlashContext, user: interactions.User):
    if bot_closing:
        await ctx.send("The bot is closing right now, so the commands are disabled.\nSorry for inconvenience")
        return

    if ctx.author.id not in owner_ids:
        await ctx.send("It seems that you dont have permission to access this command", ephemeral=True)
        return

    global recipient_id
    recipient_id = user.id
    await ctx.send(f"The recipient has been set to {user.mention}")


@interactions.slash_command(
    name="setstatus",
    description="Set the purchase status",
    options=[
        interactions.SlashCommandOption(
            type=interactions.OptionType.BOOLEAN,
            name="status",
            description="The status",
            required=True
        )
    ],
    scopes=allowed_guilds
)
async def setstatus(ctx: interactions.SlashContext, status: bool):
    if bot_closing:
        await ctx.send("The bot is closing right now, so the commands are disabled.\nSorry for inconvenience")
        return

    if ctx.author.id not in owner_ids:
        await ctx.send("It seems that you dont have permission to access this command", ephemeral=True)
        return

    global purchase_status
    purchase_status = status
    await ctx.send(f"The status has been set to {status}")


@interactions.slash_command(
    name="setdiscount",
    description="Sets the discount",
    options=[
        interactions.SlashCommandOption(
            type=interactions.OptionType.INTEGER,
            name="amount",
            description="The discount amount"
        )
    ],
    scopes=allowed_guilds
)
async def setdiscount(ctx: interactions.SlashContext, amount: int):
    if bot_closing:
        await ctx.send("The bot is closing right now, so the commands are disabled.\nSorry for inconvenience")
        return

    if ctx.author.id not in owner_ids:
        await ctx.send("It seems that you dont have permission to access this command", ephemeral=True)
        return

    global discount
    discount = amount
    await ctx.send(f"The discount was set to {discount}")


@interactions.slash_command(
    name="setthanksroom",
    description="Sets the thanks room",
    options=[
        interactions.SlashCommandOption(
            type=interactions.OptionType.CHANNEL,
            name="channel",
            description="The thanks room channel"
        )
    ],
    scopes=allowed_guilds
)
async def setthanksroom(ctx: interactions.SlashContext, channel):
    if bot_closing:
        await ctx.send("The bot is closing right now, so the commands are disabled.\nSorry for inconvenience")
        return

    if ctx.author.id not in owner_ids:
        await ctx.send("It seems that you dont have permission to access this command", ephemeral=True)
        return

    global thanksroom_id
    thanksroom_id = channel.id
    await ctx.send(f"The thanks room was set to {channel.mention}")


@interactions.slash_command(
    name="setguideroom",
    description="Sets the guide room",
    options=[
        interactions.SlashCommandOption(
            type=interactions.OptionType.CHANNEL,
            name="channel",
            description="The guide room channel"
        )
    ],
    scopes=allowed_guilds
)
async def setguideroom(ctx: interactions.SlashContext, channel):
    if bot_closing:
        await ctx.send("The bot is closing right now, so the commands are disabled.\nSorry for inconvenience")
        return

    if ctx.author.id not in owner_ids:
        await ctx.send("It seems that you dont have permission to access this command", ephemeral=True)
        return

    global guideroom_id
    guideroom_id = channel.id
    await ctx.send(f"The guide room was set to {channel.mention}")


@interactions.slash_command(
    name="setbuycategory",
    description="Set buy category",
    options=[
        interactions.SlashCommandOption(
            type=interactions.OptionType.STRING,
            name="category_id",
            description="The buy command category id"
        )
    ],
    scopes=allowed_guilds
)
async def setbuycategory(ctx: interactions.SlashContext, category_id: str):
    if bot_closing:
        await ctx.send("The bot is closing right now, so the commands are disabled.\nSorry for inconvenience")
        return

    if ctx.author.id not in owner_ids:
        await ctx.send("It seems that you dont have permission to access this command", ephemeral=True)
        return

    global buy_category_id
    try:
        buy_category_id = int(category_id)
    except ValueError:
        await ctx.send("Category id needs to be a number")
        return
    await ctx.send(f"The buy category was set to {category_id}")


@interactions.slash_command(
    name="setrole",
    description="Sets the role after buying",
    options=[
        interactions.SlashCommandOption(
            type=interactions.OptionType.ROLE,
            name="role",
            description="The role to set"
        )
    ],
    scopes=allowed_guilds
)
async def setrole(ctx: interactions.SlashContext, role: interactions.Role):
    if bot_closing:
        await ctx.send("The bot is closing right now, so the commands are disabled.\nSorry for inconvenience")
        return

    if ctx.author.id not in owner_ids:
        await ctx.send("It seems that you dont have permission to access this command", ephemeral=True)
        return

    global purchase_role_id
    purchase_role_id = role.id
    await ctx.send(f"The purchase role was set to {role.mention}")


@interactions.slash_command(
    name="setboostrole",
    description="Sets the boost role after buying",
    options=[
        interactions.SlashCommandOption(
            type=interactions.OptionType.ROLE,
            name="role",
            description="The role to set"
        )
    ],
    scopes=allowed_guilds
)
async def setboostrole(ctx: interactions.SlashContext, role: interactions.Role):
    if bot_closing:
        await ctx.send("The bot is closing right now, so the commands are disabled.\nSorry for inconvenience")
        return

    if ctx.author.id not in owner_ids:
        await ctx.send("It seems that you dont have permission to access this command", ephemeral=True)
        return

    global boost_role_id
    boost_role_id = role.id
    await ctx.send(f"The boost role was set to {role.mention}")


@interactions.slash_command(
    name="setmin",
    description="Sets the minimum robux one can buy",
    options=[
        interactions.SlashCommandOption(
            type=interactions.OptionType.INTEGER,
            name="amount",
            description="The minimum amount"
        )
    ],
    scopes=allowed_guilds
)
async def setmin(ctx: interactions.SlashContext, amount: int):
    if bot_closing:
        await ctx.send("The bot is closing right now, so the commands are disabled.\nSorry for inconvenience")
        return

    if ctx.author.id not in owner_ids:
        await ctx.send("It seems that you dont have permission to access this command", ephemeral=True)
        return

    global minimum_purchasable
    minimum_purchasable = amount
    await ctx.send(f"The minimum purchasable robux was set to {minimum_purchasable}")


@interactions.slash_command(
    name="setmax",
    description="Sets the maximum robux one can buy",
    options=[
        interactions.SlashCommandOption(
            type=interactions.OptionType.INTEGER,
            name="amount",
            description="The maximum amount"
        )
    ],
    scopes=allowed_guilds
)
async def setmax(ctx: interactions.SlashContext, amount: int):
    if bot_closing:
        await ctx.send("The bot is closing right now, so the commands are disabled.\nSorry for inconvenience")
        return

    if ctx.author.id not in owner_ids:
        await ctx.send("It seems that you dont have permission to access this command", ephemeral=True)
        return

    global maximum_purchasable
    maximum_purchasable = amount
    await ctx.send(f"The maximum purchasable robux was set to {maximum_purchasable}")


@interactions.slash_command(
    name="price",
    description="See the price of robux in credit",
    options=[
        interactions.SlashCommandOption(
            type=interactions.OptionType.INTEGER,
            name="amount",
            description="The amount of robux",
            required=False
        )
    ],
    scopes=allowed_guilds
)
async def price(ctx: interactions.SlashContext, amount: int = 1):
    if bot_closing:
        await ctx.send("The bot is closing right now, so the commands are disabled.\nSorry for inconvenience")
        return

    global robux_price
    global discount
    global boost_role_id

    try:
        has_role: bool = ctx.user in ctx.guild.get_role(boost_role_id).members

        if has_role:
            initial_price = robux_price - discount
        else:
            initial_price = robux_price

        displayed_price = initial_price

        initial_price *= amount
        final_price = tax(initial_price)

        await ctx.send(embed=interactions.Embed(
            title="Price Chart",
            description=f"**Quantity** `({amount})`\n"
                        f"**Value** `(1 robux = {displayed_price})`",
            fields=[
                interactions.EmbedField(
                    name="Total Price: ",
                    value=f"`{initial_price}`",
                    inline=False
                ),
                interactions.EmbedField(
                    name="Total Price with tax: ",
                    value=f"`{final_price}`",
                    inline=False
                )
            ],
            color=0xc154c1
        ), ephemeral=True)

    except AttributeError or ZeroDivisionError:
        await ctx.send("The credentials has not been set, ask a Moderator to set it.")


@interactions.slash_command(
    name="credit",
    description="See the amount of robux you can buy with credit",
    options=[
        interactions.SlashCommandOption(
            type=interactions.OptionType.INTEGER,
            name="amount",
            description="The amount of credit",
            required=False
        )
    ],
    scopes=allowed_guilds
)
async def credit(ctx: interactions.SlashContext, amount: int = 1):
    if bot_closing:
        await ctx.send("The bot is closing right now, so the commands are disabled.\nSorry for inconvenience")
        return

    global robux_price
    global discount
    global boost_role_id

    try:
        has_role: bool = ctx.user in ctx.guild.get_role(boost_role_id).members

        amount = math.floor(amount - amount * (5 / 100))

        if has_role:
            initial_price = robux_price - discount
        else:
            initial_price = robux_price

        total = amount / initial_price
        print(total)

        if '.' in str(total) and len(str(total).split('.')[1]) == 1 and int(str(total).split('.')[1]) != 0:
            total = int(total) - 1
        else:
            total = int(total)

        await ctx.send(embed=interactions.Embed(
            title="Credit Chart",
            fields=[
                interactions.EmbedField(
                    name="Total Robux: ",
                    value=f"`{total}`",
                    inline=False
                )
            ],
            color=0xc154c1
        ), ephemeral=True)

    except AttributeError or ZeroDivisionError:
        await ctx.send("The credentials has not been set, ask a Moderator to set it.")


@interactions.slash_command(
    name="stock",
    description="See the amount of robux available",
    scopes=allowed_guilds
)
async def stock(ctx: interactions.SlashContext):
    if bot_closing:
        await ctx.send("The bot is closing right now, so the commands are disabled.\nSorry for inconvenience")
        return

    global group_balance

    try:
        if group_balance == 0:
            global roblox_group_id
            group_balance = roblox.User.Groups.Internal.GetFunds(roblox_group_id)
    except Exception:
        await ctx.send("Invalid credentials")
        return

    await ctx.send(embed=interactions.Embed(
        title="Group Balance",
        description=f"Robux: {group_balance}"),
        ephemeral=True)


@interactions.slash_command(
    name="give",
    description="Gives Robux to user",
    scopes=allowed_guilds
)
async def give(ctx: interactions.SlashContext):
    if bot_closing:
        await ctx.send("The bot is closing right now, so the commands are disabled.\nSorry for inconvenience")
        return

    global owner_ids
    global purchase_status

    if ctx.author.id not in owner_ids:
        await ctx.send("It seems that you dont have permission to access this command", ephemeral=True)
        return

    if not purchase_status:
        await ctx.send("`/give` command is disabled right now.\nSorry for inconvenience")
        return

    global group_balance
    global roblox_group_id
    global minimum_purchasable
    global maximum_purchasable

    prompt: interactions.Modal = interactions.Modal(
        interactions.InputText(
            style=interactions.TextStyles.SHORT,
            label="Enter the username of the recipient",
            custom_id="username",
            min_length=3,
            max_length=20
        ),
        interactions.InputText(
            style=interactions.TextStyles.SHORT,
            label="Enter the amount of robux you want to send ",
            custom_id="amount",
        ),
        custom_id=f"give_modal{ctx.author_id}",
        title="Enter details",
    )

    buttons: interactions.ActionRow = interactions.ActionRow(
        interactions.Button(
            custom_id=f"yes_button{ctx.author_id}",
            style=interactions.ButtonStyle.GREEN,
            label="Yes"
        ),
        interactions.Button(
            custom_id=f"no_button{ctx.author_id}",
            style=interactions.ButtonStyle.RED,
            label="No"
        ))

    await ctx.send_modal(prompt)

    give_context: interactions.ModalContext = await ctx.bot.wait_for_modal(prompt)

    try:
        requested_username = give_context.responses['username']
        requested_amount = int(give_context.responses['amount'])
    except ValueError:
        await give_context.send(
            f"The amount should be a **number** like (eg - 1, 2, 3) and not **{give_context.responses['amount']}**\n"
            "Please use `/give` again to restart process.")
        return

    loading_message = await give_context.send("Processing Information ....")

    # Getting userid and profile pic url
    try:
        roblox_user_id = roblox.User.External.GetID([requested_username])
        photo_url = roblox.User.External.GetHeadshot(UserID=roblox_user_id, Height=100, Width=100, circular=True)
    except Exception:
        await ctx.send("The username is invalid\n"
                       "Please use `/give` again to restart process.")
        return

    # Checking if the user is in the group
    try:
        groups = roblox.User.Groups.External.GetGroups(roblox_user_id)
        in_group = False

        for group_data in groups:
            group_id = int(group_data['group']['id'])
            if group_id == roblox_group_id:
                in_group = True
                break

        if not in_group:
            await ctx.send("The User is not in the group\n"
                           "Please use `/give` again to restart process.")
            return

    except Exception:
        await ctx.send("Unable to fetch user's group\n"
                       "Please use `/give` again to restart process.")
        return

    # Building Embed with user info
    note = None

    if requested_amount > group_balance:
        requested_amount = group_balance
        note = "The amount you requested is more than available in group, so the robux amount was set to the maximum available"

    group_balance -= requested_amount

    if note:
        await ctx.send(embed=interactions.Embed(
            title="Note",
            description=note,
            color=0xff0000
        ))

    message = await ctx.send(embeds=[
        interactions.Embed(
            title=requested_username,
            description=f"**Id**: {roblox_user_id}\n"
                        f"**Amount**: {requested_amount}\n\n"
                        "**You have 20 second to confirm the information**",
            thumbnail=interactions.EmbedAttachment(url=photo_url),
            color=0xffffff
        )
    ], components=buttons)

    await loading_message.delete()

    try:
        checked_component = await bot.wait_for_component(components=buttons,
                                                         check=lambda button: button.ctx.author_id == ctx.author_id,
                                                         timeout=20)

    except TimeoutError:
        group_balance += requested_amount

        for component in buttons.components:
            component.disabled = True

        await message.edit(components=buttons)

        await ctx.send("The Purchase was cancelled because you were unable to complete the confirmation in time.\n"
                       "Please use `/give` again to restart process.")

        return

    for component in buttons.components:
        component.disabled = True

    await message.edit(components=buttons)

    if checked_component.ctx.custom_id == f"yes_button{ctx.author_id}":
        global purchase_queue
        await checked_component.ctx.send("Your purchase was successful, you will receive your robux shortly")

        purchase_queue.put(
            [requested_username, roblox_user_id, requested_amount, photo_url, ctx.author_id, ctx.channel_id])
        await ctx.send(f"Position in Queue: {purchase_queue.qsize()}\n"
                       f"Estimated Time: {purchase_queue.qsize() * interval} secs")
    else:
        group_balance += requested_amount
        await checked_component.ctx.send("Your purchase was cancelled")


@interactions.slash_command(
    name="buy",
    description="Buy robux using credits",
    scopes=allowed_guilds
)
async def buy(ctx: interactions.SlashContext):
    if bot_closing:
        await ctx.send("The bot is closing right now, so the commands are disabled.\nSorry for inconvenience")
        return

    global purchase_status
    global buy_category_id
    global timeout_table

    if not purchase_status:
        await ctx.send("`/buy` command is disabled right now.\nSorry for inconvenience")
        return

    if not ctx.channel.parent_id == buy_category_id:
        await ctx.send("`/buy` command can only be used inside tickets")
        return

    # Checking timeout and removing timeout if timeout over
    if f"{ctx.author_id}" in timeout_table.keys():
        if time.time() - timeout_table[f"{ctx.author_id}"] >= 300:
            del timeout_table[f"{ctx.author_id}"]
        else:
            await ctx.send(f"You are timed out try again at <t:{int(timeout_table[f'{ctx.author_id}'] + 300)}:t>")
            return

    global group_balance
    global roblox_group_id
    global minimum_purchasable
    global maximum_purchasable

    prompt: interactions.Modal = interactions.Modal(
        interactions.InputText(
            style=interactions.TextStyles.SHORT,
            label="Enter the username of the recipient",
            custom_id="username",
            min_length=3,
            max_length=20
        ),
        interactions.InputText(
            style=interactions.TextStyles.SHORT,
            label="Enter the amount of robux you want to send ",
            custom_id="amount",
        ),
        custom_id=f"give_modal{ctx.author_id}",
        title="Enter details",
    )

    buttons: interactions.ActionRow = interactions.ActionRow(
        interactions.Button(
            custom_id=f"yes_button{ctx.author_id}",
            style=interactions.ButtonStyle.GREEN,
            label="Yes"
        ),
        interactions.Button(
            custom_id=f"no_button{ctx.author_id}",
            style=interactions.ButtonStyle.RED,
            label="No"
        ))

    await ctx.send_modal(prompt)

    give_context: interactions.ModalContext = await ctx.bot.wait_for_modal(prompt)

    try:
        requested_username = give_context.responses['username']
        requested_amount = int(give_context.responses['amount'])
    except ValueError:
        await give_context.send(
            f"The amount should be a **number** like (eg - 1, 2, 3) and not **{give_context.responses['amount']}**\n"
            "Please use `/buy` again to restart process.")
        return

    loading_message = await give_context.send("Processing Information ....")

    # Checking if the amount of robux exceeds the range of min and maximum
    if requested_amount < minimum_purchasable:
        await ctx.send(f"The amount you requested is less than minimum amount (minimum robux = {minimum_purchasable}\n)"
                       "Please use `/buy` again to restart process.")
        return

    if requested_amount > maximum_purchasable:
        await ctx.send(f"The amount you requested is more than maximum amount (maximum robux = {maximum_purchasable}\n)"
                       "Please use `/buy` again to restart process.")
        return

    # Getting userid and profile pic url
    try:
        roblox_user_id = roblox.User.External.GetID([requested_username])
        photo_url = roblox.User.External.GetHeadshot(UserID=roblox_user_id, Height=100, Width=100, circular=True)
    except Exception:
        await ctx.send("The username is invalid\n"
                       "Please use `/buy` again to restart process.")
        return

    # Adding timeout
    timeout_table[f"{ctx.author_id}"] = time.time()

    # Checking if the user is in the group
    try:
        groups = roblox.User.Groups.External.GetGroups(roblox_user_id)
        in_group = False

        for group_data in groups:
            group_id = int(group_data['group']['id'])
            if group_id == roblox_group_id:
                in_group = True
                break

        if not in_group:
            await ctx.send("The User is not in the group\n"
                           "Please use `/group` to get group link and the use `/buy` to restart the process.")
            return

    except Exception:
        await ctx.send("Unable to fetch user's group\n"
                       "Please use `/buy` again to restart process.")
        return

    # Checking for booster role set
    global boost_role_id

    try:
        has_role: bool = ctx.user in ctx.guild.get_role(boost_role_id).members
    except Exception:
        await ctx.send("Booster role not set ask a moderator to set it")
        return

    # Building Embed with user info
    note = None

    if requested_amount > group_balance:
        requested_amount = group_balance
        note = "The amount you requested is more than available in group, so the robux amount was set to the maximum available"

    group_balance -= requested_amount

    if note:
        await ctx.send(embed=interactions.Embed(
            title="Note",
            description=note,
            color=0xff0000
        ))

    message = await ctx.send(embeds=[
        interactions.Embed(
            title=requested_username,
            description=f"**Id**: {roblox_user_id}\n"
                        f"**Amount**: {requested_amount}\n\n"
                        "**You have 20 second to confirm the information**",
            thumbnail=interactions.EmbedAttachment(url=photo_url),
            color=0xffffff
        )
    ], components=buttons)

    await loading_message.delete()

    try:
        checked_component = await bot.wait_for_component(components=buttons,
                                                         check=lambda button: button.ctx.author_id == ctx.author_id,
                                                         timeout=20)

    except TimeoutError:
        group_balance += requested_amount

        for component in buttons.components:
            component.disabled = True

        await message.edit(components=buttons)

        await ctx.send("The Purchase was cancelled because you were unable to complete the confirmation in time.\n"
                       "Please use `/buy` again to restart process.")

        return

    for component in buttons.components:
        component.disabled = True

    await message.edit(components=buttons)

    if checked_component.ctx.custom_id != f"yes_button{ctx.author_id}":
        group_balance += requested_amount
        await checked_component.ctx.send("Your purchase was cancelled")
        return

    global robux_price
    global discount

    if has_role:
        initial_price = robux_price - discount
    else:
        initial_price = robux_price

    final_price = tax(initial_price * requested_amount)

    await checked_component.ctx.send(f"Convert {final_price} to <@!{recipient_id}>\n"
                                     f"You only have two minute.\n\n"
                                     f"Use command")
    await ctx.channel.send(f"c {recipient_id} {final_price}")

    try:
        await bot.wait_for(event="on_message_create", timeout=120, checks=lambda mess:
        mess.message.channel == ctx.channel and
        mess.message.content == f"**:moneybag: | {ctx.user.username}, has transferred `${(initial_price * requested_amount)}` to <@!{recipient_id}> **")
    except TimeoutError:
        group_balance += requested_amount

        await ctx.send("The Purchase was cancelled because you were unable to complete the confirmation in time.\n"
                       "Please use `/buy` again to restart process.")

        return

    try:
        global purchase_role_id
        global purchase_queue
        global interval

        role = ctx.guild.get_role(purchase_role_id)
        await ctx.member.add_role(role=role, reason=f"Purchased Robux at {time.time()}")

        await ctx.send("Your purchase was successful, you will receive your robux shortly")
        purchase_queue.put(
            [requested_username, roblox_user_id, requested_amount, photo_url, ctx.author_id, ctx.channel_id])
        await ctx.send(f"Position in Queue: {purchase_queue.qsize()}\n"
                       f"Estimated Time: {purchase_queue.qsize() * interval} secs")

    except Exception:
        group_balance += requested_amount

        await ctx.send("Some unknown error occurred\n"
                       "Please use `/buy` again to restart process.")


@interactions.slash_command(
    name="group",
    description="Get info about the group",
    scopes=allowed_guilds
)
async def group(ctx: interactions.SlashContext):
    if bot_closing:
        await ctx.send("The bot is closing right now, so the commands are disabled.\nSorry for inconvenience")
        return

    global roblox_group_name
    global roblox_group_description
    global roblox_group_emblem_url
    global roblox_group_id

    await ctx.send(embed=interactions.Embed(
        title=f"{roblox_group_name}",
        description=f"**Description:** {roblox_group_description}",
        thumbnail=interactions.EmbedAttachment(url=roblox_group_emblem_url)
    ), components=[interactions.Button(
        label="Group link",
        style=interactions.ButtonStyle.LINK,
        url=f"https://www.roblox.com/groups/{roblox_group_id}/{roblox_group_name.replace(' ','-')}#!/about"
    )])


@interactions.slash_command(
    name="help",
    description="Sends the list of commands and their usage",
    scopes=allowed_guilds
)
async def help(ctx: interactions.SlashContext):
    if bot_closing:
        await ctx.send("The bot is closing right now, so the commands are disabled.\nSorry for inconvenience")
        return

    embed = interactions.Embed(title="Help Command", color=0x2e8b57)
    public_commands = ['buy', 'stock', 'price', 'credit', 'ping', 'help', 'group']

    for command in bot.application_commands:
        if ctx.user.id in owner_ids:
            embed.add_field(name=f"**Command:** `/{command.resolved_name}`",
                            value=f"**Description:** {command.description}\n\n\n", inline=False)
        else:
            if command.resolved_name in public_commands:
                embed.add_field(name=f"**Command:** `/{command.resolved_name}`",
                                value=f"**Description:** {command.description}\n\n\n", inline=False)

    await ctx.send(embed=embed, ephemeral=True)


bot.start()
