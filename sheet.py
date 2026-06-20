import time
import gspread
import gspread_formatting
from google.oauth2.service_account import Credentials

HIT_QUOTA_PRINT="hit google sheets read/write quota >:-/"
BACKOFF_TIME=5

# open sheet
gc=gspread.service_account(filename="sheetsapikey.json")
spreadsheet:gspread.spreadsheet
with open("sheetkey.txt","r") as file:
	spreadsheet=gc.open_by_key(file.read())

def rowcol_to_a1_range(from_row:int,from_col:int,to_row:int,to_col:int)->str:
	return f"{gspread.utils.rowcol_to_a1(from_row,from_col)}:{gspread.utils.rowcol_to_a1(to_row,to_col)}"

def get_worksheet(title:str)->gspread.Worksheet:
	return spreadsheet.worksheet(title)

# quota protection func
def get_user_entered_format(worksheet:gspread.worksheet,row:int,col:int):
	try:
		return gspread_formatting.get_user_entered_format(worksheet,gspread.utils.rowcol_to_a1(row,col))
	except gspread.exceptions.APIError as error:
		# check if hit quota
		if error.response.status_code==429:
			print(HIT_QUOTA_PRINT)

			# wait
			print("waiting %d seconds..."%BACKOFF_TIME)
			time.sleep(BACKOFF_TIME)

			# retry
			return get_user_entered_format(worksheet,row,col)
		else:
			raise error

# quota protection func
def batch_get_values(worksheet:gspread.worksheet,ranges):
	try:
		return worksheet.batch_get(ranges)
	except gspread.exceptions.APIError as error:
		# check if hit quota
		if error.response.status_code==429:
			print(HIT_QUOTA_PRINT)

			# wait
			print("waiting %d seconds..."%BACKOFF_TIME)
			time.sleep(BACKOFF_TIME)

			# retry
			return batch_get_values(worksheet,ranges)
		else:
			raise error

def batch_get_values_from_to(worksheet:gspread.Worksheet,from_row:int,from_col:int,to_row:int,to_col:int):
	return batch_get_values(worksheet,[rowcol_to_a1_range(from_row,from_col,to_row,to_col)])[0]

# quota protection func
def batch_update(worksheet:gspread.worksheet,data)->None:
	try:
		return worksheet.batch_update(data)
	except gspread.exceptions.APIError as error:
		# check if hit quota
		if error.response.status_code==429:
			print(HIT_QUOTA_PRINT)

			# wait
			print("waiting %d seconds..."%BACKOFF_TIME)
			time.sleep(BACKOFF_TIME)

			# retry
			batch_update(worksheet,data)
		else:
			raise error

def batch_update_from(worksheet:gspread.Worksheet,row:int,col:int,data:list)->None:
	"""
	figures out the range relative to row and col from how big the data list is<br>
	doesnt do anything to cells that would be under an empty string
	"""
	# okay heres my issue
	# updating a cells value to an empty string isnt the same as clearing it. >:-(
	# itll break formatting in a way that makes the dropdown disappear, which TANGENT
		# thats pretty weird because setting it to a non empty but arbitrary string value that isnt in the dropdown
		# doesnt get rid of the dropdown, it just gives the cell a mark that it violates the rule
		# what is this weird quasi clear state??? can we get scientists to look into it? maybe this could be a new
		# source of clean renewable energy, or fuel for nuclear weapons
	# the solution im using here is breaking it up into batch operations by rows, and only setting values that arent
	# empty strings
	# theres a better solution here where it looks vertically too to find the biggest squares, since the bottleneck is
	# sheets api limits and not compute on the server computer but i dont think it really matters here
	ranges:list[str]=[]
	valueses:list[list[str]]=[]

	for vertical_offset in range(len(data)):
		row_data=data[vertical_offset]
		this_row:int=row+vertical_offset

		horizontal_from:int=-1
		values:list[str]=[]
		for horizontal_offset,value in enumerate(row_data):
			# check to wrap up batch
			if value=="" and horizontal_from!=-1:
				# add range and values
				ranges.append(rowcol_to_a1_range(this_row,col+horizontal_from,this_row,col+horizontal_offset-1))
				valueses.append([values])
				values=[]

				horizontal_from=-1
			elif value!="":
				# check to start batch
				if horizontal_from==-1:
					horizontal_from=horizontal_offset
				
				# add value to this batch
				values.append(value)

		if horizontal_from!=-1:
			# add range and values
			ranges.append(rowcol_to_a1_range(this_row,col+horizontal_from,this_row,col+len(row_data)-1))
			valueses.append([values])
	
	# add everything
	batch_data:list=[]
	for i in range(len(ranges)):
		batch_data.append({
			"range":ranges[i],
			"values":valueses[i]
		})
	# finally, send out the data
	batch_update(worksheet,batch_data)

# quota protection func
def batch_clear(worksheet:gspread.worksheet,ranges)->None:
	try:
		worksheet.batch_clear(ranges)
	except gspread.exceptions.APIError as error:
		# check if hit quota
		if error.response.status_code==429:
			print(HIT_QUOTA_PRINT)

			# wait
			print("waiting %d seconds..."%BACKOFF_TIME)
			time.sleep(BACKOFF_TIME)

			# retry
			batch_clear(worksheet,ranges)
		else:
			raise error

def batch_clear_from(worksheet:gspread.Worksheet,row:int,col:int,data:list)->None:
	"""
	figures out the range relative to row and col from how big the data list is
	"""
	height:int=len(data)
	width:int=1
	for row_data in data:
		width=max(width,len(row_data))
	
	batch_clear(worksheet,[rowcol_to_a1_range(row,col,row+height-1,row+width-1)])

# quota protection func
def add_rows(worksheet:gspread.worksheet,num_rows:int)->None:
	try:
		worksheet.add_rows(num_rows)
	except gspread.exceptions.APIError as error:
		# check if hit quota
		if error.response.status_code==429:
			print(HIT_QUOTA_PRINT)

			# wait
			print("waiting %d seconds..."%BACKOFF_TIME)
			time.sleep(BACKOFF_TIME)

			# retry
			add_rows(worksheet,num_rows)
		else:
			raise error

# quota protection func
def append_rows(worksheet:gspread.worksheet,values:list[str])->None:
	try:
		worksheet.append_rows(values)
	except gspread.exceptions.APIError as error:
		# check if hit quota
		if error.response.status_code==429:
			print(HIT_QUOTA_PRINT)

			# wait
			print("waiting %d seconds..."%BACKOFF_TIME)
			time.sleep(BACKOFF_TIME)

			# retry
			append_rows(worksheet,values)
		else:
			raise error

# quota protection func
def delete_rows(worksheet:gspread.worksheet,start_index:int,end_index:int=None)->None:
	try:
		worksheet.delete_rows(start_index,end_index)
	except gspread.exceptions.APIError as error:
		# check if hit quota
		if error.response.status_code==429:
			print(HIT_QUOTA_PRINT)

			# wait
			print("waiting %d seconds..."%BACKOFF_TIME)
			time.sleep(BACKOFF_TIME)

			# retry
			delete_rows(worksheet,start_index,end_index)
		else:
			raise error

# quota protection func
def duplicate(worksheet:gspread.worksheet,insert_sheet_index:int=None,new_sheet_id:int=None,
		new_sheet_name:str=None)->gspread.Worksheet:
	try:
		return worksheet.duplicate(insert_sheet_index,new_sheet_id,new_sheet_name)
	except gspread.exceptions.APIError as error:
		# check if hit quota
		if error.response.status_code==429:
			print(HIT_QUOTA_PRINT)

			# wait
			print("waiting %d seconds..."%BACKOFF_TIME)
			time.sleep(BACKOFF_TIME)

			# retry
			return duplicate(worksheet,insert_sheet_index,new_sheet_id,new_sheet_name)
		else:
			raise error

# quota protection func
def update_title(worksheet:gspread.worksheet,title:str)->None:
	try:
		worksheet.update_title(title)
	except gspread.exceptions.APIError as error:
		# check if hit quota
		if error.response.status_code==429:
			print(HIT_QUOTA_PRINT)

			# wait
			print("waiting %d seconds..."%BACKOFF_TIME)
			time.sleep(BACKOFF_TIME)

			# retry
			update_title(worksheet,title)
		else:
			raise error