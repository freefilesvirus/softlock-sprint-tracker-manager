import discord
from discord.ext import commands
from datetime import datetime
import rapidfuzz
import memory
import tasks

# region const variables
DEFAULT_COLOR=discord.Color.from_rgb(255,234,124)

NUMBER_EMOJIS:list[str]=["1️⃣","2️⃣","3️⃣","4️⃣","5️⃣"]

# accuracy percent to immediately accept above
ACCEPTABLE_TASK_SIMILARITY=95

MEMORY_USER_CATEGORY="users"
MEMORY_LEAD_CATEGORY="leads"
# endregion

bot=commands.Bot()

# region memory functions
def set_discord_user_sheet_user(ctx,discord_user:discord.user,sheet_user:str)->None:
	"""
	saves a persistent association between a discord id and sheet user name
	"""
	memory.set_category_key_value(ctx.guild.id,MEMORY_USER_CATEGORY,str(discord_user.id),sheet_user)

def get_discord_id(ctx,sheet_user:str)->int:
	"""
	returns the discord id associated with the sheet user name
	"""
	return memory.get_category_key(ctx.guild.id,MEMORY_USER_CATEGORY,sheet_user)

def get_sheet_user(ctx,discord_user:discord.user)->str:
	"""
	returns the sheet user name associated with the discord id
	"""
	return memory.get_category_value(ctx.guild.id,MEMORY_USER_CATEGORY,str(discord_user.id))

def get_user_is_lead(ctx,discord_user:discord.user)->bool:
	lead_category:list=memory.get_category(ctx.guild.id,MEMORY_LEAD_CATEGORY)

	# false if lead category isnt valid
	if lead_category is None:
		return False
	
	# return if discord id is in category
	return str(discord_user.id) in lead_category

def set_user_is_lead(ctx,discord_user:discord.user,is_lead:bool)->None:
	# return if no change
	if get_user_is_lead(ctx,discord_user)==is_lead:
		return

	lead_category:list=memory.get_category(ctx.guild.id,MEMORY_LEAD_CATEGORY)
	if lead_category is None:
		# make it somethin
		lead_category=[]

	discord_user_str:str=str(discord_user.id)
	if is_lead:
		# add to list
		lead_category.append(discord_user_str)
	else:
		# remove from list
		lead_category.remove(discord_user_str)

	memory.set_category(ctx.guild.id,MEMORY_LEAD_CATEGORY,lead_category)
# endregion

# region misc util functions
def get_user_has_authority(ctx,user:discord.user)->bool:
	"""
	returns if the user is a server admin or lead
	"""
	return user.guild_permissions.administrator or get_user_is_lead(ctx,user)

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

def user_embed(ctx,discord_user:discord.user,action:str="")->discord.Embed:
	"""
	creates an embed colored after the user with a description of what they did

	:param action: a description of what the user did, shown after their name<br>
	e.g. "created a task" or "registered as user"
	"""
	embed:discord.Embed=discord.Embed(
		color=get_element_discord_color(get_sheet_user(ctx,discord_user))
	)
	# set user
	embed.set_author(name=discord_user.display_name,icon_url=discord_user.display_avatar)

	# set description if action not empty
	if action!="":
		embed.description=f"{discord_user.mention} {action}"

	return embed

async def get_task_from_description(ctx,description:str)->tasks.SprintTask:
	"""
	from the task description, finds a task from the sheet with a similar description or gives the user an interactive
	prompt between a few
	"""
	sheet_tasks:list[tasks.SprintTask]=tasks.get_sheet_tasks()

	description=description

	# collect descriptions
	descriptions:list[str]=[]
	for task in sheet_tasks:
		descriptions.append(task.description)

	matches=rapidfuzz.process.extract(description,descriptions,processor=rapidfuzz.utils.default_process)
	for match in matches:
		if match[1]>=ACCEPTABLE_TASK_SIMILARITY:
			# good enough, find which task the description is for again
			for task in sheet_tasks:
				if task.description==match[0]:
					return task

	# its gonna be a second
	await ctx.defer()
	
	# offer similar tasks
	embed=user_embed(ctx,ctx.author)
	embed.add_field(name="",value="Invalid task! Did you mean one of the following?",inline=False)
	emojis:list[str]=[]
	for i,match in enumerate(matches):
		emoji:str=NUMBER_EMOJIS[i]
		embed.add_field(name="",value=f"> {emoji} {match[0]}",inline=False)

		# add to list
		emojis.append(emoji)
	message=await ctx.send(embed=embed,silent=True)

	# add reactions
	for emoji in emojis:
		await message.add_reaction(emoji)

	# check if user has already added reaction
	def reaction_check(reaction,user)->bool:
		return user==ctx.author and reaction.emoji in emojis

	# gotta go through this rigamarole to get correct reactions
	winning_reaction:discord.reaction=None
	message=await message.channel.fetch_message(message.id)
	for reaction in message.reactions:
		for user in await reaction.users().flatten():
			if reaction_check(reaction,user):
				winning_reaction=reaction
				break
		
		if not winning_reaction is None:
			break

	# check if user hasnt reacted yet
	if winning_reaction is None:
		try:
			winning_reaction,user=await bot.wait_for("reaction_add",check=reaction_check,timeout=10)
		except discord.asyncio.TimeoutError as error:
			# timeout
			await message.delete()
			return None

	# DESTROY!!! temp message
	await message.delete()

	# find and return associated task
	winning_description=matches[emojis.index(winning_reaction.emoji)][0]
	for task in sheet_tasks:
		if task.description==winning_description:
			return task
	
	# some weird fail
	return None
# endregion

# region fail functions
async def fail(ctx,message:str)->None:
	"""
	creates an ephemeral message indicating the command failed
	"""
	await ctx.respond(
		embed=discord.Embed(color=DEFAULT_COLOR,description=f"Operation failed! {message}"),
		ephemeral=True
	)

async def fail_notask(ctx)->None:
	await fail(ctx,"Couldn't find the task")

async def fail_notregistered(ctx,user:discord.user)->None:
	await fail(ctx,f"{user.mention} isn't registered as any user")

async def fail_noauth(ctx)->None:
	await fail(ctx,"You don't have permission to use that command")
# endregion

# region bot commands
@bot.slash_command(
	name="changediscipline",
	description="Changes the discipline of a task"
)
async def command_changediscipline(ctx,
	task_description:discord.Option(str,description="The description to find the task"),
	discipline:discord.Option(str,choices=tasks.domains["disciplines"],description="The discipline to set for the task")
):
	# check for authority
	if not get_user_has_authority(ctx,ctx.author):
		await fail_noauth(ctx)
		return

	# check that task is valid
	task:tasks.SprintTask=await get_task_from_description(ctx,task_description)
	if task is None:
		await fail_notask(ctx)
		return
	
	# check for a change
	if task.discipline==discipline:
		await fail(ctx,f"The discipline of that task is already \"{discipline}\"")
		return

	# make embed
	embed:discord.Embed=user_embed(ctx,ctx.author,f"changed the discipline of a task to \"{discipline}\"")
	embed.add_field(name="",value="> "+task.description,inline=False)
	embed.color=get_element_discord_color(discipline)
	await ctx.respond(embed=embed)

	# update task
	task.discipline=discipline
	task.invalidate()

@bot.slash_command(
	name="changepriority",
	description="Changes the priority of a task"
)
async def command_changepriority(ctx,
	task_description:discord.Option(str,description="The description to find the task"),
	priority:discord.Option(str,choices=tasks.domains["priorities"],description="The priority to set for the task")
):
	# check for authority
	if not get_user_has_authority(ctx,ctx.author):
		await fail_noauth(ctx)
		return

	# check that task is valid
	task:tasks.SprintTask=await get_task_from_description(ctx,task_description)
	if task is None:
		await fail_notask(ctx)
		return
	
	# check for a change
	if task.priority==priority:
		await fail(ctx,f"The priority of that task is already \"{priority}\"")
		return

	# make embed
	embed:discord.Embed=user_embed(ctx,ctx.author,f"changed the priority of a task to \"{priority}\"")
	embed.add_field(name="",value="> "+task.description,inline=False)
	embed.color=get_element_discord_color(priority)
	await ctx.respond(embed=embed)

	# update task
	task.priority=priority
	task.invalidate()

@bot.slash_command(
	name="assignuser",
	description="Assigns a user to a task"
)
async def command_assignuser(ctx,
	task_description:discord.Option(str,description="The description to find the task"),
	user:discord.Option(discord.User,description="The user to assign to the task")
):
	# check that user is registered
	sheet_user=get_sheet_user(ctx,user)
	if sheet_user is None:
		await fail_notregistered(ctx,user)
		return

	# check that task is valid
	task:tasks.SprintTask=await get_task_from_description(ctx,task_description)
	if task is None:
		await fail_notask(ctx)
		return
	
	# check that user isnt already assigned
	if sheet_user in task.assigned_users:
		await fail(ctx,f"{sheet_user} is already assigned to that task")
		return

	# make embed
	embed:discord.Embed=user_embed(ctx,ctx.author,
		f"assigned {user.mention if user!=ctx.author else 'themself'} (as {sheet_user}) to a task")
	embed.color=get_element_discord_color(sheet_user)
	embed.add_field(name="",value="> "+task.description,inline=False)
	await ctx.respond(embed=embed)
	
	# update task
	task.assigned_users.insert(0,sheet_user)
	while len(task.assigned_users)>tasks.SHEET_ASSIGNED_USERS_COUNT:
		task.assigned_users.pop()
	task.invalidate()

@bot.slash_command(
	name="setstatus",
	description="Sets the status of a task"
)
async def command_setstatus(ctx,
	task_description:discord.Option(str,description="The description to find the task"),
	status:discord.Option(str,choices=tasks.domains["statuses"],description="The status to set for the task")
):
	# check that task is valid
	task:tasks.SprintTask=await get_task_from_description(ctx,task_description)
	if task is None:
		await fail_notask(ctx)
		return
	
	# check for a change
	if task.status==status:
		await fail(ctx,f"The status of that task is already \"{status}\"")
		return

	# make embed
	embed:discord.Embed=user_embed(ctx,ctx.author,f"set the status of a task to \"{status}\"")
	embed.add_field(name="",value="> "+task.description,inline=False)
	embed.color=get_element_discord_color(status)
	await ctx.respond(embed=embed)

	# update task
	task.status=status

	if status==tasks.COMPLETE_STATUS:
		# set date complete to today
		task.date_completed=datetime.now().strftime("%m/%d/%Y")

	task.invalidate()

@bot.slash_command(
	name="setblockers",
	description="Sets the blockers of a task"
)
async def command_setblockers(ctx,
	task_description:discord.Option(str,description="The description to find the task"),
	blockers:discord.Option(str,required=False,description="The blockers to set for the task")
):
	# check that task is valid
	task:tasks.SprintTask=await get_task_from_description(ctx,task_description)
	if task is None:
		await fail_notask(ctx)
		return

	# make embed
	message:str
	if blockers is None:
		blockers=""
		message="cleared the blockers of a task"
	else:
		message=f"set the blockers of a task to \"{blockers}\""
	
	embed:discord.Embed=user_embed(ctx,ctx.author,message)
	embed.add_field(name="",value="> "+task.description,inline=False)
	await ctx.respond(embed=embed)

	# update task
	task.blockers=blockers
	task.invalidate()

@bot.slash_command(
	name="setcomments",
	description="Sets the comments of a task"
)
async def command_setcomments(ctx,
	task_description:discord.Option(str,description="The description to find the task"),
	comments:discord.Option(str,required=False,description="The comments to set for the task")
):
	# check that task is valid
	task:tasks.SprintTask=await get_task_from_description(ctx,task_description)
	if task is None:
		await fail_notask(ctx)
		return

	# make embed
	message:str
	if comments is None:
		comments=""
		message="cleared the comments of a task"
	else:
		message=f"set the comments of a task to \"{comments}\""
	
	embed:discord.Embed=user_embed(ctx,ctx.author,message)
	embed.add_field(name="",value="> "+task.description,inline=False)
	await ctx.respond(embed=embed)

	# update task
	task.comments=comments
	task.invalidate()

@bot.slash_command(
	name="register",
	description="Associates your account with a sheet user"
)
async def command_register(ctx,
	sheet_user:discord.Option(str,choices=tasks.domains["users"],description="The name to assign to your discord account")
):
	# check for a change
	if get_sheet_user(ctx,ctx.author)==sheet_user:
		await fail(ctx,f"You're already registered as \"{sheet_user}\"")
		return

	set_discord_user_sheet_user(ctx,ctx.author,sheet_user)

	# make embed
	embed=user_embed(ctx,ctx.author,f"registered themself as \"{sheet_user}\"")
	await ctx.respond(embed=embed)

@bot.slash_command(
	name="createtask",
	description="Creates a task"
)
async def command_createtask(ctx,
	task_description:discord.Option(str,description="The description of the task"),
	discipline:discord.Option(str,choices=tasks.domains["disciplines"],description="The discipline of the task"),
	priority:discord.Option(str,choices=tasks.domains["priorities"],description="The priority of the task"),
	status:discord.Option(str,choices=tasks.domains["statuses"],default=tasks.DEFAULT_STATUS,description="The status of the task"),
):
	# check for authority
	if not get_user_has_authority(ctx,ctx.author):
		await fail_noauth(ctx)
		return

	task=tasks.SprintTask()
	task.description=task_description
	task.discipline=discipline
	task.priority=priority
	task.status=status

	# make embed
	embed=user_embed(ctx,ctx.author,f"created a task")
	embed.add_field(name="",value=f"> {task_description}",inline=False)
	embed.color=get_element_discord_color(discipline)
	await ctx.respond(embed=embed)

	task.invalidate()
	
@bot.slash_command(
	name="whois",
	description="Gets who a user is registered as"
)
async def command_assignuser(ctx,user:discord.Option(discord.User,description="The user to check")):
	embed:discord.Embed=discord.Embed(color=DEFAULT_COLOR)

	sheet_user:str=get_sheet_user(ctx,user)
	if sheet_user is None:
		embed.description=f"{user.mention} isn't registered as any user"
	else:
		embed.description=f"{user.mention} is{" a lead and" if get_user_is_lead(ctx,user) else ""} registered as \"{sheet_user}\""
		embed.color=get_element_discord_color(sheet_user)

	await ctx.respond(embed=embed,ephemeral=True)
	
@bot.slash_command(
	name="getusertasks",
	description="Gets all tasks assigned to a specific user"
)
async def command_getusertasks(ctx,user:discord.Option(discord.User,description="The user to check",required=False)):
	# set user to author if unspecified
	if user is None:
		user=ctx.author
	
	# check that theyre registered
	sheet_user:str=get_sheet_user(ctx,user)
	if sheet_user is None:
		await fail_notregistered(ctx,user)
		return

	embed=discord.Embed()
	embed.color=get_element_discord_color(sheet_user)
	embed.description=f"{user.mention} (as {sheet_user}) is assigned to the following tasks"
	
	# get tasks
	sheet_tasks:list[tasks.SprintTask]=tasks.get_sheet_tasks()
	for task in sheet_tasks:
		if sheet_user in task.assigned_users:
			embed.add_field(name="",value="> "+task.description,inline=False)

	await ctx.respond(embed=embed,ephemeral=True)

@bot.slash_command(
	name="organizesheet",
	description="Organizes all the tasks on the sheet"
)
async def command_organizesheet(ctx):
	# check for authority
	if not get_user_has_authority(ctx,ctx.author):
		await fail_noauth(ctx)
		return

	# make embed
	embed=user_embed(ctx,ctx.author,f"organized the sheet")
	await ctx.respond(embed=embed)

	tasks.organize_sheet()

@bot.slash_command(
	name="closesprint",
	description="Finishes the current sprint sheet and creates a new one"
)
async def command_closesprint(ctx,archive_title:discord.Option(str,description="The title for the current sprints archive")):
	# check for authority
	if not get_user_has_authority(ctx,ctx.author):
		await fail_noauth(ctx)
		return

	# make embed
	embed=user_embed(ctx,ctx.author,f"closed the current sprint sheet and archived it as \"{archive_title}\"")
	await ctx.respond(embed=embed)

	tasks.close_sprint(archive_title)

@bot.slash_command(
	name="makelead",
	description="Gives a user lead permissions"
)
async def command_makelead(ctx,user:discord.Option(discord.User,description="The user to make a lead")):
	# check for authority
	if not get_user_has_authority(ctx,ctx.author):
		await fail_noauth(ctx)
		return

	# check that they arent already a lead
	if get_user_is_lead(ctx,user):
		await fail(ctx,f"{user.mention} is already a lead")
		return
	
	# make embed
	embed=user_embed(ctx,user,f"made {user.mention} a lead")
	await ctx.respond(embed=embed)

	set_user_is_lead(ctx,user,True)

@bot.slash_command(
	name="revokelead",
	description="Removes lead permissions from a user"
)
async def command_revokelead(ctx,user:discord.Option(discord.User,description="The user to revoke lead permissions")):
	# check for authority
	if not get_user_has_authority(ctx,ctx.author):
		await fail_noauth(ctx)
		return

	# check that they are a lead
	if not get_user_is_lead(ctx,user):
		await fail(ctx,f"{user.mention} isn't a lead")
		return
	
	# make embed
	embed=user_embed(ctx,user,f"revoked lead permissions from {user.mention}")
	await ctx.respond(embed=embed)

	set_user_is_lead(ctx,user,False)
# endregion

@bot.event
async def on_ready():
	print("bot is ready!")

with open("discordtoken.txt","r") as file:
	bot.run(file.read())
