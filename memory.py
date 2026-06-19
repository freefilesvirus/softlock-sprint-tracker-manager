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

def set_discord_id_sheet_user(discord_id:int,sheet_user:str)->None:
	"""
	saves a persistent association between a discord id and sheet user name
	"""
	# make sure users dict exists
	if not "users" in data:
		data["users"]={}

	data["users"][str(discord_id)]=sheet_user
	save_data()

def get_discord_id(sheet_user:str)->int:
	"""
	returns the discord id associated with the sheet user name
	"""
	# make sure users dict exists
	if not "users" in data:
		return None
	
	for discord,sheet in data["users"].items():
		if sheet==sheet_user:
			return discord

def get_sheet_user(discord_id:int)->str:
	"""
	returns the sheet user name associated with the discord id
	"""
	# make sure users dict exists
	if not "users" in data:
		return None
	
	for discord in data["users"]:
		if discord==str(discord_id):
			return data["users"][discord]