from flask import Flask, render_template, request
import json

#imports for "/graphics"
from bokeh.embed import components
from graphics import Graphic #import our graphic class
import backend
# from flask import session

#imports for "/input1"
from flask import render_template,request, redirect, flash,url_for
import os
import pandas as pd
from pathlib import Path

#imports for "input2"
import pandas as pd
from flask import render_template,request,redirect,url_for #, session
import os
import numpy as np


app = Flask(__name__)
app.secret_key = 'super secret key'
session = {}

def set_session():
	'''
		set/reset to default session values
	'''
	session.clear()

	#stored for /graphics
	session["tab"] = None #graphic view tab; i.e. all, positive or negative only
	session["year_from"] = None
	session["year_to"] = None
	session["index"] = [] #stored the current graphic view indices as a list e.g. ["Amsterdam", "West"]
	session["order"] = "descending" #current view, plot "ascending" or "descending"
	session["totals"]=[]
	session["d"]=None
	session["row_indexes"] = None

	#stored for /input
	session["filename"] = None

	#stored  for /input2
	session["row_header_to"] = 1 #multi index? "multi" or "single"
	session["column_header_start"] = None
	session["column_header_to"] = None

	session["year"] = None #year (date) column

	session["year_min"] = None #dataset minimum possible year
	session["year_max"] = None #dataset max possible year

#---------------
#/input1
#---------------
@app.route('/')
def upload_file():

	#reset session variables
	set_session()

	return render_template('upload1.html')

@app.route('/upload1')
def read_file():	

	args = request.args

	if "file" in args:
		session["filename"]=os.path.abspath(args["file"])

	return show_data()

#-----------------------
#/upload2
#-----------------------

@app.route('/upload2')
def show_data():

	#HTML variables
	args = request.args
	if "row_header_to" in args:
		session["row_header_to"] = int(args["row_header_to"])

		#update the row headers
		session["row_indices"] = list(range(0,session["row_header_to"]))

		#reset session["year"]
		session["year"] = None

	if "column_header_start" in args:
		if args["column_header_start"] != "None":
			session["column_header_start"] = args["column_header_start"] if args["column_header_start"]==None else int(args["column_header_start"])
		else:
			session["column_header_start"] = None

		#if != None (i.e. ==1), also set session["column_header_to"] = 1
		if session["column_header_start"]:
			session["column_header_to"] = 1
		else:
			session["column_header_to"] =  None

	if "column_header_to" in args:
		session["column_header_to"] = int(args["column_header_to"])

	#generate "row_indices" and "column_indices_backend" 
	session["row_indices"] = list(range(0,session["row_header_to"])) #list of row indices (consecutive) representing headers

	if session["column_header_to"]:
		session["column_indices"] = list(range(0,session["column_header_to"])) #list of row indices (consecutive) representing headers
		session["column_indices_backend"] = list(range(0,session["column_header_to"]+1))
	else:
		session["column_indices"] = None
		session["column_indices_backend"] = [0]
	
	#generate dataframe for current variables for 
	filename = session["filename"]
	ext = os.path.splitext(filename)[1]
	if ext=='csv':
		new_file=pd.read_csv(os.path.join(filename),header=session["row_indices"],index_col=session["column_indices"])
	else:
		new_file=pd.read_excel(os.path.join(filename),header=session["row_indices"],index_col=session["column_indices"])
	
	new_file = new_file.reset_index()
	new_file.columns = pd.MultiIndex.from_tuples(list(enumerate(new_file,1)))

	#generate tables for views
	tables=[new_file.to_html(classes='data')]

	# ext = os.path.splitext(filename)[1]
	# if ext=='csv':
	# 	new_file=pd.read_csv(os.path.join(filename),header=session["row_indices"],index_col=session["column_indices_backend"])
	# else:
	# 	new_file=pd.read_excel(os.path.join(filename),header=session["row_indices"],index_col=session["column_indices_backend"])
	
	# new_file = new_file.reset_index()
	# print(new_file.iloc[0])

	# generate year pull down options
	# if session["row_indices"][-1] > 0:
	# 	new_file.columns = [' '.join(col) for col in new_file.columns]

	
	# sheets["time_index"] = new_file.columns.get_loc(sheets[""])

	#get values associated with "year" pulldown
	if "year" in args:
		session["year"] = int(args["year"])
		session["year_min"] = None; session["year_max"] = None #reset year range on new data column selection
		try:
			session["year_min"] = min([int(i) for i in new_file.iloc[:,session["year"]-1]])
			session["year_max"] = max([int(i) for i in new_file.iloc[:,session["year"]-1]])
		except: 
			pass

	columns = range(0,5)

	# print("helloWWWWWWWW\n\n", session["year"])
	# print(new_file)
	# print("helloWWWWWWWW\n\n", new_file.columns.get_loc(session["year"]))

	
	return render_template('upload2.html',
							tables = tables, 
							titles=new_file.columns.values,
							filename=filename,

							columns = columns,
							year = session["year"],

							row_header_to = session["row_header_to"],
							column_header_to = session["column_header_to"],
							column_header_start = session["column_header_start"],

							year_min = session["year_min"],
							year_max = session["year_max"]
							)

#---------------
# /graphics
#---------------

# session = {"tab":None, "year_from":None, "year_to":None, "index":[], "order":"descending", "totals":[], "d":None}

@app.route('/graphics')
def graphics():

	#-----------------
	#If year range if know from a selected column in /upload 2; set year_options, session["year_from"] and session["year_to"]
	#otherwise these variables = None, if date data not known, this is hidden from plot options
	#-----------------

	#get the limiting years wrt. the data set (from /upload2 i.e. def show_data)
	start_time = session["year_min"]
	end_time = session["year_max"]

	if start_time and end_time:
		year_options = list(range(start_time, end_time+1))
	else:
		year_options = None

	#set initial values of year_to and year_from ONLY IF year_options != None
	if session["year_from"] == None and year_options: 
		session["year_from"] = year_options[0] 

	if session["year_to"] == None and year_options: 
		session["year_to"] = year_options[-1]

	#------------------
	#get variables form HTML
	#------------------

	#get the more recent variable values
	args = request.args
	
	#"tab" variables from HTML
	if "tab" in args:
		session["tab"] = args["tab"]

	#year variables from 
	if "year_from" in args:
		session["year_from"] = int(args["year_from"]) ; print("\n\n", session["year_from"],"\n\n")
		session["d"] = backend.backend(session["filename"],session["row_indices"], session["column_indices_backend"], session["year"], session["year_from"], session["year_to"])
			
	#year variables from 
	if "year_to" in args:
		session["year_to"] = int(args["year_to"]) ; print("\n\n", session["year_to"],"\n\n")
		session["d"] = backend.backend(session["filename"],session["row_indices"], session["column_indices_backend"], session["year"], session["year_from"], session["year_to"] )

	#year variables from 
	if "index" in args:
		session["index"].append(args["index"].replace("_____", " "))

	if "crumb" in args:
		if args["crumb"] == "All Populations":
			session["index"] = []
		else:
			r = session["index"].index(args["crumb"].replace("_____", " "))
			session["index"] = session["index"][0:r+1]

	if "order" in args:
		session["order"] = args["order"]

	#get data from backend
	if not session["d"]:
		session["d"] = backend.backend(session["filename"],session["row_indices"], session["column_indices_backend"], session["year"], session["year_from"], session["year_to"])


	#output json file for testing
	with open('data.json', 'w') as f:
		json.dump(session["d"], f)

	# Create the plot
	graph = Graphic()	
	graph.get_data(session["d"], session["index"])
	graph.generate(session["tab"], by=session["order"])

	#generate extra variables

	if year_options:
		year_from_options = year_options[0:year_options.index(int(session["year_to"]))+1]
		year_to_options = year_options[year_options.index(int(session["year_from"])):]
	else:
		year_from_options = None
		year_to_options = None
	
	# generate ordered version of sub-pop dictionary 
	colours = graph.get_colours()
	subs = graph.get_subs()
	ordered_subs = [s for s in subs if colours[s] != "lightgrey"] + [s for s in subs if colours[s] == "lightgrey"]
    
	# Embed plot into HTML via Flask Render
	script, div = components(graph.plot)
	return render_template("graphics.html", 
						   script=script, 
						   div=div, 

						   tab_options = ["all", 
						   				  "positive", 
										  "negative"],
						   tab_current = session["tab"],

						   year_options = year_options,
						   year_from_options = year_from_options,
						   year_to_options = year_to_options,

						   year_from = session["year_from"],
						   year_to = session["year_to"],

						   subs = ordered_subs,
						   crumbs = session["index"], #navigation index level as list

						   order = session["order"],
						   order_options = ["ascending", "descending"],

						   colours = colours,

						   totals = graph.get_totals()

						   #subs = ordered_subs  
						   )

# With debug=True, Flask server will auto-reload 
# when there are code changes
if __name__ == '__main__':

    app.run(port=5000, debug=True)
