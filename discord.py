# My code is shit.
# Not done yet.
import discord
import os
import json
import sys
from discord.ext import commands
import aiosqlite
from datetime import datetime
import twbus

# config
displayversion = "v0.1 Beta"
version = 0.1
config = {}
if os.path.exists("config.json"):
    config = json.loads(open("config.json", "r").read())
    if version > config["version"]:
        pass
else:
    open("config.json", "w").write(json.dumps({"version":version,"token":"YOUR_TOKEN_HERE","ownersid":[]}))
    sys.exit(1)

showversion = displayversion.split()[0] + " _" + displayversion.split()[1] + "_"

def echo(text, type="INFO", userid=None, ctx=None):
    username = ""
    if ctx:
        username = f"user={ctx.author.name}({ctx.author.id})"
    elif userid:
        user = bot.fetch_user(userid)
        username = f"user={user.name}({user.id})"
    print(f"[{type}]", text, username)

# def button
class StatusButton(discord.ui.Button):
    def __init__(self, label, status, emoji, task_name, user_id, parent_view):
        super().__init__(label=label, style=discord.ButtonStyle.primary, emoji=emoji)
        self.status = status
        self.task_name = task_name
        self.user_id = user_id
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        # update db
        async with aiosqlite.connect('tasks.db') as db:
            await db.execute("UPDATE task_list SET status = ? WHERE user_id = ? AND task_name = ?",
                         (self.status, self.user_id, self.task_name))
            await db.commit()
    
        # update the task message
        await self.parent_view.update_task_message(interaction)

        


        

# create view
class StatusButtonView(discord.ui.View):
    def __init__(self, task_name, user_id, parent_view):
        super().__init__(timeout=None)
        statuses = [
            ("已完成", "<a:yes:1292752044960251915>"),
            ("正在用", "<a:writing:1292752138065416246>"),
            ("尚未開始", "<a:no:1292752102527078440>"),
            ("沒帶", "💀")
        ]
        for label, emoji in statuses:
            self.add_item(StatusButton(label=label, status=label, emoji=emoji, task_name=task_name, user_id=user_id, parent_view=parent_view))

# create selections view
class TaskSelect(discord.ui.Select):
    def __init__(self, tasks, user_id, parent_view):
        self.user_id = user_id
        self.parent_view = parent_view
        options = [discord.SelectOption(label=task) for task in tasks]
        super().__init__(placeholder="選擇一個項目來更新狀態", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        task_name = self.values[0]

        # create buttons
        view = StatusButtonView(task_name, self.user_id, self.parent_view)
        await interaction.response.send_message(f'選擇 **{task_name}** 的狀態：', view=view, ephemeral=True)

# main view selections
class TaskView(discord.ui.View):
    def __init__(self, user_id, message):
        super().__init__(timeout=None)
        self.tasks = []
        self.user_id = user_id
        self.message = message

    async def load_tasks(self):
        tasks = []
        async with aiosqlite.connect('tasks.db') as db:
            async with db.execute("SELECT task_name, status, date FROM task_list WHERE user_id = ?", (self.user_id,)) as cursor:
                async for row in cursor:
                    task_name, status, date = row
                    tasks.append(task_name)
        self.tasks = tasks
        self.add_item(TaskSelect(self.tasks, self.user_id, self))

    async def update_task_message(self, interaction):
        task_list_message = await self.generate_task_message()
        await self.message.edit(content=task_list_message)

    async def generate_task_message(self):
        alldone = True
        last_date = ""
        task_list_message = ""
        async with aiosqlite.connect('tasks.db') as db:
            async with db.execute("SELECT task_name, status, date FROM task_list WHERE user_id = ?", (self.user_id,)) as cursor:
                async for row in cursor:
                    task_name, status, date = row
                    status_map = {
                        "已完成": "<a:yes:1292752044960251915>",
                        "正在用": "<a:writing:1292752138065416246>",
                        "尚未開始": "<a:no:1292752102527078440>",
                        "沒帶": "💀"
                    }
                    if status != "已完成":
                        alldone = False
                    if date != last_date:
                        task_list_message += date + "\n"
                        last_date = date
                    task_list_message += f"- {task_name} {status_map[status]}\n"
        return task_list_message


intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)
# remove help command and mine will work
bot.remove_command('help')

# init db
async def init_db():
    async with aiosqlite.connect('tasks.db') as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS task_list (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                user_id INTEGER,
                                task_name TEXT,
                                status TEXT DEFAULT "尚未開始",
                                date TEXT
                            )''')
        await db.commit()
        await db.execute('''CREATE TABLE IF NOT EXISTS noOldMsg (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                user_id INTEGER,
                                enabled BOOLEAN,
                                channel_id INTEGER,
                                message_id INTEGER
                            )''')
        await db.commit()
        await db.execute('''CREATE TABLE IF NOT EXISTS showAfterDel (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                user_id INTEGER,
                                enabled BOOLEAN
                            )''')
        await db.commit()




@bot.event
async def on_ready():
    echo(f'Logged in as {bot.user.name}')
    echo("Changing rich presence...")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="Lists"))
    echo("Init database")
    await init_db()
    echo("All ready!")

@bot.command(name="help")
async def help(ctx):
    echo("Ran command help", ctx=ctx)
    msg = await ctx.send("## ListBot Help\n  * !help - 顯示機器人用法\n  * !about - 關於此機器人\n  * !addlist [list] - 增加一個當天清單，用半形逗號(,)分項\n    * list範例： Task1,Task2,Task3\n  * !dellist [options] - 在清單內刪除一個或多個項目，使用 !dellist 來查看使用方式。\n  * !showlist - 顯示你的清單\n  * !nooldmsg [ true | false ] - 自動將舊訊息刪除。 _測試版_\n  * !showafterdel [ true | false ] - 在執行!dellist之後執行!showlist。 _測試版_")
    await nomsync(ctx.author.id, ctx.channel.id, msg.id)

@bot.command(name="about")
async def about(ctx):
    echo("Ran command about", ctx=ctx)
    msg = await ctx.send(f"## ListBot {showversion} by AvianJay\n### 幫助你管理待辦事項的好機器人:D\n  * 更新紀錄\n    * 增加showafterdel\n    * 優化以及修復了用法訊息")
    await nomsync(ctx.author.id, ctx.channel.id, msg.id)

@bot.command(name="getbusid")
async def getbusid(ctx, name=None):
    echo("Ran command getbusid", ctx=ctx)
    if name:
        data = bus.fetch_route_byname(name)
        if data == []:
            await ctx.send("找不到 ¯⁠\⁠\\_⁠(⁠ツ⁠)⁠\\_⁠/⁠¯")
    msg = await ctx.send(f"## BusBot {showversion} by AvianJay\n### 幫助你管理待辦事項的好機器人:D\n  * 更新紀錄\n    * 增加showafterdel\n    * 優化以及修復了用法訊息")

if __name__ == "__main__":
    echo(f"ListBot {version} by AvianJay")
    bot.run(token)
