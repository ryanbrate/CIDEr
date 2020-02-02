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
from flask import render_template,request,redirect,url_for#, session
import os
from pathlib import Path
import numpy as np
import copy

app = Flask(__name__)
app.secret_key = 'super secret key'
session = {}

def reset_session():
    '''
       sets default values for session variables (only for those variables that require it)
    '''
    session.clear()
    
    #stored for /graphics
    session["tab"] = None #graphic view tab; i.e. all, positive or negative only
    session["year_from"] = None
    session["year_to"] = None
    session["indices"] = [] #stored the current graphic view indices as a list e.g. ["Amsterdam", "West"]
    session["order"] = "descending" #current view, plot "ascending" or "descending"
    session["totals"]=[]
    session["d"]=None
    session["row_indexes"] = None

    
    #stored  for /input2
    session["row_header_to"] = 1 #i.e. defaults to single index only
    session["column_header_start"] = "No subpopulations"#i.e. defaults to there being no sub-populations whatsoever
    session["column_header_to"] = None 
    session["column_header_from"]=0

    session["year"] = None #year (date) column

    session["year_min"] = None #dataset minimum possible year
    session["year_max"] = None #dataset max possible year

#---------------
#/input1
#---------------
@app.route('/')
def upload_file():

    return render_template('upload1.html')

@app.route('/upload1')
def read_file():
    '''get filename and store as session variable'''
     
    reset_session()

    #read in the selected filename 
    args = request.args
    if "file" in args:
        session["file"] = args["file"]
        
    return show_data()

#-----------------------
#/upload2
#-----------------------

@app.route('/upload2')
def show_data():
    
    #
    #acknowledge a change in page variables (row_header_to, column_header_start or column_header_to, year) 
    #

    args = request.args
    
    #handle a change to the number or row indices
    if "row_header_to" in args:
        session["row_header_to"] = int(args["row_header_to"])

        #reset session["year"]
        session["year"] = None

    #handle a change to "column_header_start" page var. (i.e. first column index)
    if "column_header_start" in args:
        if args["column_header_start"] != "No subpopulations":
            session["column_header_start"] = 1
            session["column_header_to"] = 1
        else:
            session["column_header_start"] = "No subpopulations"
            session["column_header_to"] =  None
    
    #handle a change in "column_header_to" page var (i.e. final column index) 
    if "column_header_to" in args:
        session["column_header_to"] = int(args["column_header_to"])
    
    
    #
    # populate the lists of column/ row indices from the input variables
    #
    
    #row indices (i.e. single row -> [0], two rows -> [0,1])
    session["row_indices"] = list(range(0,session["row_header_to"])) #list of row indices (consecutive) representing headers
    
    #column indices (i.e. no subpops -> indices = None, indices_backend=[0], 1 subpop -> indices = [0], indices_backend = [0,1])
    if session["column_header_start"] != "No subpopulations":
        session.pop("column_indices_backend", None) 
        session["column_indices_backend"] = list(range(0,session["column_header_to"]+1))
    else:
        session["column_indices_backend"] = [0]
   
    #generate dataframe for current variables for
    new_file=pd.read_excel(session["file"],header=session["row_indices"],index_col=[0])
    
    new_file = new_file.reset_index()
    new_file.columns = pd.MultiIndex.from_tuples(list(enumerate(new_file,1)))
    
    #get values associated with "year" pulldown
    if "year" in args:
        session["year"] = int(args["year"])
        session["year_min"] = None; session["year_max"] = None #reset year range on new data column selection
        try:
            session["year_min"] = min([int(i) for i in new_file.iloc[:,session["year"]-1]])
            session["year_max"] = max([int(i) for i in new_file.iloc[:,session["year"]-1]])
        except:
            pass


    #generate tables for views
    tables=[new_file.to_html(classes='data', index=False)]

    
    #the max number of sub-population columns
    columns = range(0,5)

    return render_template('upload2.html',
                            tables = tables,
                            titles=new_file.columns.values,

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


@app.route('/graphics')
def graphics():

    
    #create the range of possible years from selected year column max and min values 
    if session["year_min"] and session["year_max"]:
        year_options = list(range(session["year_min"],session["year_max"]+1))
    else:
        year_options = None

    #set initial values of year_to and year_from ONLY IF year_options != None
    if session["year_from"] == None and year_options:
        session["year_from"] = year_options[0]

    if session["year_to"] == None and year_options:
        session["year_to"] = year_options[-1]

    #------------------
    #update variables from HTML
    #------------------

    args = request.args

    #"tab" variables from HTML
    if "tab" in args:
        session["tab"] = args["tab"]

    #year variables from
    if "year_from" in args:
        session["year_from"] = int(args["year_from"])
        session["d"] = backend.backend(session["file"],session["row_indices"], session["column_indices_backend"], session["year"], session["year_from"], session["year_to"])

    #year variables from
    if "year_to" in args:
        session["year_to"] = int(args["year_to"])
        session["d"] = backend.backend(session["file"],session["row_indices"], session["column_indices_backend"], session["year"], session["year_from"], session["year_to"] )


    #year variables from
    if "index" in args:
        temp = args["index"].replace("_____", " ")
        session["indices"].append(temp)
        print("\n\n", session["indices"], "\n\n")
    
    if "crumb" in args:
        if args["crumb"] == "All Populations":
            session["indices"] = []
        else:
            r = session["indices"].index(args["crumb"].replace("_____", " ")) 
            session["indices"] = session["indices"][0:r+1]

    if "order" in args:
        session["order"] = args["order"]

    #get data from backend
    if not session["d"]:
        session["d"] = backend.backend(session["file"],session["row_indices"], session["column_indices_backend"], session["year"], session["year_from"], session["year_to"])


   #  #output json file for testing
    # with open('data.json', 'w') as f:
        # json.dump(session["d"], f)

    # Create the plot
    graph = Graphic()
    graph.get_data(session["d"], session["indices"])
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
                           crumbs = session["indices"], #navigation index level as list

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
