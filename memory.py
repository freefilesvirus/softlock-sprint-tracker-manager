# data is stored like the following
#
# users:
# 	discord id: sheet user

import json
import os

DATA_FILE_NAME="data.json"

# ensure the file exists
if not os.path.exists(DATA_FILE_NAME):
	with open(DATA_FILE_NAME,"w") as file:
		file.write("{}")

# get data
data={}
with open(DATA_FILE_NAME,"r") as file:
	data=json.load(file)

def save_data()->None:
	with open(DATA_FILE_NAME,"w") as file:
		file.write(json.dumps(data,indent=4))

def get_category(guild_id:int,category:str)->any:
	"""
	gets a category in a guild
	prefer get_category_key unless youre doing something special
	"""
	# check if category exists
	guild_str=str(guild_id)
	if not guild_str in data or not category in data[guild_str]:
		return None

	return data[guild_str][category]

def set_category(guild_id:int,category:str,value:any)->None:
	"""
	sets a category in a guild
	prefer set_category_key_value unless the category isnt a dictionary
	"""
	# make sure dict tree exists
	guild_str=str(guild_id)
	if not guild_str in data:
		data[guild_str]={}
	
	data[guild_str][category]=value

	save_data()

def set_category_key_value(guild_id:int,category:str,key:str,value:str)->None:
	"""
	sets a keys value in a category in a guild
	"""
	# make sure dict tree exists
	guild_str=str(guild_id)
	if not guild_str in data:
		data[guild_str]={}
	if not category in data[guild_str]:
		data[guild_str][category]={}
	
	data[guild_str][category][key]=value

	save_data()

def get_category_key_value(guild_id:int,category:str,key:str)->str:
	"""
	gets a keys value in a category in a guild
	"""
	# check if dict tree exists
	guild_str=str(guild_id)
	if not guild_str in data or not category in data[guild_str] or not key in data[guild_str][category]:
		return None

	return data[guild_str][category][key]

def set_discord_id_sheet_user(guild_id:int,discord_id:int,sheet_user:str)->None:
	"""
	saves a persistent association between a discord id and sheet user name
	"""
	set_category_key_value(guild_id,"users",str(discord_id),sheet_user)

def get_discord_id(guild_id:int,sheet_user:str)->int:
	"""
	returns the discord id associated with the sheet user name
	"""
	for discord,sheet in get_category(guild_id,"users"):
		if sheet==sheet_user:
			return discord

def get_sheet_user(guild_id:int,discord_id:int)->str:
	"""
	returns the sheet user name associated with the discord id
	"""
	return get_category_key_value(guild_id,"users",str(discord_id))
