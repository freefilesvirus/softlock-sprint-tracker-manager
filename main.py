import discord
from discord.ext import commands
import rapidfuzz
import sheet
import memory
import tasks

DEFAULT_COLOR=discord.Color.from_rgb(255,234,124)

# accuracy percent to immediately accept above
ACCEPTABLE_TASK_SIMILARITY=95

bot=commands.Bot()

async def get_user_from_id(discord_id:int)->discord.user:
	"""
	tries to get a discord user from their id
	"""
	user=bot.get_user(discord_id)
	if not user is None:
		return user
	
	# might still exist, just not cached
	return await bot.fetch_user(discord_id)

def get_element_discord_color(element:str)->discord.Color:
	"""
	returns the background color from the element cells in the domain sheets

	:param element: any element that is part of a domain<br>
	e.g. "Design" or "Waiting on Paperwork"
	"""
	color=tasks.get_element_color(element)
	if color is None:
		return DEFAULT_COLOR

	return discord.Color.from_rgb(
		int((color.red or 0)*255),
		int((color.green or 0)*255),
		int((color.blue or 0)*255)
	)

def user_embed(discord_user:discord.user,action:str)->discord.Embed:
	"""
	creates an embed colored after the user with a description of what they did

	:param action: a description of what the user did, shown after their name<br>
	e.g. "created a task" or "registered as user"
	"""
	embed:discord.Embed=discord.Embed(
		description=f"{discord_user.mention} {action}",
		color=get_element_discord_color(memory.get_sheet_user(discord_user.id))
	)
	# set user
	embed.set_author(name=discord_user.display_name,icon_url=discord_user.display_avatar)

	return embed

# TODO
#async def get_task_from_description(ctx:discord.context,description:str)->tasks.SprintTask:
#	for task in tasks.get_sheet_tasks():

# returns the task index of a close enough task, or has user choose
# async def get_task_index(ctx,task):
# 	tasks=sheet.get_all_tasks()

# 	# make lower for comparison
# 	task=task.lower()
# 	for index in range(len(tasks)):
# 		tasks[index]=tasks[index].lower()

# 	matches=rapidfuzz.process.extract(task,tasks)
# 	for match in matches:
# 		if match[1]>=ACCEPTABLE_TASK_SIMILARITY:
# 			# good enough, find its index
# 			index=0
# 			for t in tasks:
# 				if match[0]==t:
# 					return index

# 				index+=1
	
# 	# show the user similar
# 	embed=discord.Embed(
# 		description="Invalid task! Did you mean one of the following?",
# 		color=DEFAULT_COLOR
# 	)
# 	emojis=[]
# 	for match in matches:
# 		embed.add_field(name="",value="> "+match[0],inline=False)

# 	message=await ctx.respond(embed=embed,ephemeral=True)

# 	return -1

@bot.slash_command(
	name="register",
	description="Associates your account with a sheet user",
	guild_ids=[1515128303827292341]
)
async def command_register(ctx:discord.context,
	sheet_user:discord.Option(str,choices=tasks.domains["users"])
):
	memory.set_discord_id_sheet_user(ctx.author.id,sheet_user)

	# make embed
	embed=user_embed(ctx.author,f"registered themself as \"{sheet_user}\"")
	await ctx.respond(embed=embed)

@bot.event
async def on_ready():
	print("bot is ready!")

with open("discordtoken.txt","r") as file:
	bot.run(file.read())