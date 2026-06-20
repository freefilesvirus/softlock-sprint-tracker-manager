import sheet

SHEET_FROM_ROW:int=5
SHEET_FROM_COLUMN:int=2
SHEET_TO_COLUMN:int=13
SHEET_DESCRIPTION_COLUMN:int=3
SHEET_DISCIPLINE_COLUMN:int=2
SHEET_STATUS_COLUMN:int=4
SHEET_PRIORITY_COLUMN:int=5
SHEET_DATE_COMPLETED_COLUMN:int=7
SHEET_BLOCKERS_COLUMN:int=12
SHEET_COMMENTS_COLUMN:int=13
SHEET_ASSIGNED_USERS_COLUMN:int=9
SHEET_ASSIGNED_USERS_COUNT:int=3

SHEET_ELEMENT_COLUMN:int=2

SHEET_CURRENT_TITLE:str="current"
SHEET_TEMPLATE_TITLE:str="template"

DEFAULT_STATUS="Not started"
COMPLETE_STATUS="Complete"

domains:dict={}

cached_element_colors:dict={}

class SprintTask:
	# its all strs
	# what is this, a stirring contest?
	# what is this, a...
	# what is this, a spoon convention?
	description:str=""
	discipline:str=""
	status:str=DEFAULT_STATUS
	priority:str=""
	date_completed:str=""
	blockers:str=""
	comments:str=""
	assigned_users:list[str]

	def __init__(self):
		# grr
		self.assigned_users=[]

	def sort(self)->float:
		score=0.0

		# check for bad task
		for property in [self.description,self.discipline,self.status,self.priority]:
			if property=="":
				return 999999.0

		# more important for the sort in descending order
		for pair in [("disciplines",self.discipline),("priorities",self.priority),("statuses",self.status)]:
			score*=10
			for index,element in enumerate(domains[pair[0]]):
				if pair[1].lower().strip()==element.lower().strip():
					score+=index/len(domains[pair[0]])

					break

		return score

	def get_list(self)->list[str]:
		"""
		returns a list of strings used to fill a spreadsheet
		"""
		task_list=[""]*(SHEET_TO_COLUMN-SHEET_FROM_COLUMN+1)

		# add all the one cell stuff
		for pair in [(self.description,SHEET_DESCRIPTION_COLUMN),(self.discipline,SHEET_DISCIPLINE_COLUMN),
			   (self.status,SHEET_STATUS_COLUMN),(self.priority,SHEET_PRIORITY_COLUMN),
			   (self.date_completed,SHEET_DATE_COMPLETED_COLUMN),(self.blockers,SHEET_BLOCKERS_COLUMN),
			   (self.comments,SHEET_COMMENTS_COLUMN)]:
			task_list[pair[1]-SHEET_FROM_COLUMN]=pair[0]

		# add the users
		for i,assigned_user in enumerate(self.assigned_users):
			task_list[SHEET_ASSIGNED_USERS_COLUMN-SHEET_FROM_COLUMN+i]=assigned_user

			# check if hit max sheet users
			if i>=SHEET_ASSIGNED_USERS_COUNT-1:
				break

		return task_list

	def invalidate(self)->None:
		"""
		ensures that the information on the google sheet is accurate to this

		if the current sheet contains a task with a matching description, it will overwrite all the information with
		whats stored in this<br>
		otherwise, itll create a new task and populate it with the information from this
		"""
		# look for existing task
		worksheet=get_current_worksheet()
		sheet_task_lists=get_sheet_task_lists(worksheet)
		
		task_index:int=-1
		for i,task in enumerate(sheet_task_lists):
			if (len(task)>=SHEET_DESCRIPTION_COLUMN-SHEET_FROM_COLUMN
					and task[SHEET_DESCRIPTION_COLUMN-SHEET_FROM_COLUMN]==self.description):
				task_index=i
				break
		
		task_list:list[str]=self.get_list()
		if task_index==-1:
			# found no matching description, create a new row to fill
			sheet.add_rows(worksheet,1)
			task_index=worksheet.row_count-SHEET_FROM_ROW
		else:
			# found a matching description
			sheet_task_list:list[str]=sheet_task_lists[task_index]
			# make sure sheet task is the right length
			while len(sheet_task_list)<=SHEET_TO_COLUMN-SHEET_FROM_COLUMN:
				sheet_task_list.append("")

			if sheet_task_list==task_list:
				# already matching, nothing to do
				return
			
			# if there are any spaces where the sheet has something filled in and the task list doesnt, the whole row
			# needs to be cleared or the extra data will linger
			for i in range(len(sheet_task_list)):
				if sheet_task_list[i]!=task_list[i] and task_list[i]=="":
					# clear task
					sheet.batch_clear_from(worksheet,task_index+SHEET_FROM_ROW,SHEET_FROM_COLUMN,[task_list])
					break
		
		# add data
		sheet.batch_update_from(worksheet,task_index+SHEET_FROM_ROW,SHEET_FROM_COLUMN,[task_list])

def get_element_color(element:str):
	"""
	returns the background color from the element cells in the domain sheets

	:param element: any element that is part of a domain<br>
	e.g. "Design" or "Waiting on Paperwork"
	"""
	# valid check
	if element is None:
		return None

	# format
	element=element.lower().strip()

	# check if its already in cache
	if element in cached_element_colors:
		return cached_element_colors[element]
	
	# search if element is valid
	for domain,elements in domains.items():
		for i in range(len(elements)):
			if elements[i].lower().strip()==element:
				# element is valid
				return (sheet.get_user_entered_format(sheet.get_worksheet(domain),SHEET_FROM_ROW+i,SHEET_ELEMENT_COLUMN)
						.backgroundColor)

	# invalid element
	return None

def get_current_worksheet()->sheet.gspread.worksheet:
	return sheet.get_worksheet(SHEET_CURRENT_TITLE)

def get_sheet_task_lists(worksheet)->list[list[str]]:
	"""
	returns a list of all task lists from the current spreadsheet
	"""
	return sheet.batch_get_values_from_to(get_current_worksheet(),SHEET_FROM_ROW,SHEET_FROM_COLUMN,
		worksheet.row_count,SHEET_TO_COLUMN)

def from_list(task_list:list[str])->SprintTask:
	"""
	returns a task from a list of strings from a spreadsheet
	"""
	# bulk to the right length
	while len(task_list)<=SHEET_TO_COLUMN-SHEET_FROM_COLUMN:
		task_list.append("")

	task=SprintTask()

	# set the one cell stuff
	task.description=task_list[SHEET_DESCRIPTION_COLUMN-SHEET_FROM_COLUMN]
	task.discipline=task_list[SHEET_DISCIPLINE_COLUMN-SHEET_FROM_COLUMN]
	task.status=task_list[SHEET_STATUS_COLUMN-SHEET_FROM_COLUMN]
	task.priority=task_list[SHEET_PRIORITY_COLUMN-SHEET_FROM_COLUMN]
	task.date_completed=task_list[SHEET_DATE_COMPLETED_COLUMN-SHEET_FROM_COLUMN]
	task.blockers=task_list[SHEET_BLOCKERS_COLUMN-SHEET_FROM_COLUMN]
	task.comments=task_list[SHEET_COMMENTS_COLUMN-SHEET_FROM_COLUMN]

	# set the users
	assigned_user_start:int=SHEET_ASSIGNED_USERS_COLUMN-SHEET_FROM_COLUMN
	for i in range(SHEET_ASSIGNED_USERS_COUNT):
		assigned_user_index:int=assigned_user_start+i

		# bounds check
		if assigned_user_index>=len(task_list):
			break

		if task_list[assigned_user_index]!="":
			# not empty, append
			task.assigned_users.append(task_list[assigned_user_index])

	return task

def from_sheet_description(description:str)->SprintTask:
	"""
	returns a task from the current spreadsheet matching the description
	"""
	for sheet_task_list in get_sheet_task_lists(get_current_worksheet()):
		if sheet_task_list[SHEET_DESCRIPTION_COLUMN-SHEET_FROM_COLUMN]==description:
			# found it
			return from_list(sheet_task_list)
	
	# didnt find a matching task
	return None

def get_sheet_tasks()->list[SprintTask]:
	"""
	returns a list of all tasks from the current spreadsheet
	"""
	sheet_tasks:list[SprintTask]=[]
	for sheet_task_list in get_sheet_task_lists(get_current_worksheet()):
		sheet_tasks.append(from_list(sheet_task_list))
	return sheet_tasks

def organize_sheet()->None:
	"""
	reorganizes the tasks in the current worksheet
	"""
	# collect and organize
	tasks=get_sheet_tasks()
	tasks.sort(key=SprintTask.sort)
	
	# to lists
	task_lists=[]
	for task in tasks:
		task_lists.append(task.get_list())

		# bulk up to the left
		for _ in range(SHEET_FROM_COLUMN-1):
			task_lists[-1].append("")
	
	# update
	worksheet=get_current_worksheet()
	# adds new rows to house the organized tasks and then delete the old rows to avoid a catastrophic event where it
	# crashes after clearing but before updating and all that data is lost
	sheet.append_rows(worksheet,task_lists)
	sheet.delete_rows(worksheet,SHEET_FROM_ROW,len(task_lists)+SHEET_FROM_ROW-1)

def close_sprint(archive_title:str)->None:
	"""
	archives the current worksheet and creates a new one

	:param title: the title for the current sheets archive
	"""
	# close out the old
	former_current=get_current_worksheet()
	sheet.update_title(former_current,archive_title)

	# make the new
	return sheet.duplicate(sheet.get_worksheet(SHEET_TEMPLATE_TITLE),0,new_sheet_name=SHEET_CURRENT_TITLE)

# collect domains
for domain in ["disciplines","statuses","priorities","users"]:
	# collect from sheet
	worksheet=sheet.get_worksheet(domain)
	column_data:list[list[str]]=sheet.batch_get_values_from_to(worksheet,SHEET_FROM_ROW,SHEET_ELEMENT_COLUMN,
			worksheet.row_count,SHEET_ELEMENT_COLUMN)
	
	# parse
	domains[domain]=[]
	for row_data in column_data:
		for value in row_data:
			# check that value isnt empty
			value=value.strip()
			if value!="":
				domains[domain].append(value)