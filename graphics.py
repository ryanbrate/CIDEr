#Written by RJB 2019

from bokeh.plotting import figure, show, output_file #basic plots
from bokeh.models.widgets import RangeSlider #time range slider
from bokeh.layouts import column, gridplot, widgetbox, Spacer
from bokeh.models import Label, LabelSet, ColumnDataSource, HoverTool, Circle, GlyphRenderer, HBar
from bokeh.io import curdoc

import pandas as pd
import json
import numpy as np

class Graphic():
    '''
    Class defining/populating each graph object
    '''

    def __init__(self):

        #data
        self.data = {}#data store wrt current view
        self.subpops = []
        self.colours = {}

        self.totals = {}

        self.number_of_entries = None
        self.min_corr_abs = None

        self.source = None #data as bokeh ColumnDataSource object

        #basic plot/ output setup
        self.output = output_file("graphic.html")
        self.plot = None
        self.plot_start = 0

        #plot properties
        self.bar_scale = 0.5 #relative scale of bars


    def reset(self):
        '''
            run by self.get_data(), i.e. reset all object variables prior to populating with new values
        '''
        self.data ={}
        self.subpops = []
        self.colours = {}

        self.totals = {}

        self.number_of_entries = None 
        self.min_corr_abs = None 

        self.source = None 


    def get_data(self, d, sub_indices):
        '''
            populate self.data, i.e. the dictionary storing the current plot info
            Args:
                d:               A complete dictionary of correlation data (structure below), corresponding to a specific year period
                sub_indices:     a list of sub-indices representing the information level of the current view
        '''

        #structure of self.d

        #{
        # corr=[                                    #list of lists for correlation statistics for each variable pair
        #       [var1, var2, corr, corr_abs],
        #       [var1, var2, corr, corr_abs],
        #        ...
        #      ]
        # subs:{
        #       "Gemiddelde Amsterdam":{
        #                               corr=[                              
        #                                       [var1, var2, corr, corr_abs],  
        #                                       [var1, var2, corr, corr_abs],
        #                                       ...
        #                                    ]
        #                               subs:{pattern continued depending on number of nested indices}
        #                               }
        #       }
        #}

        self.reset()

        #recursive lambda function to return dictionary at a specific sub-index (given by list, "sub_indices")
        #Args: d = base dictionary, s = list of sub-indices at which to return dict e.g. sub_indices = ["Amsterdam", "zuid"]
        get_sub_index = lambda d, sub_indices=[]: d if len(sub_indices) == 0 else get_sub_index(d["subs"][sub_indices[0]], sub_indices[1:])

        #populate self.data based on current level
        d_at_level = get_sub_index(d,sub_indices) #dictionary @ sub-index level

        self.data["first"] = [i[0] for i in d_at_level["corr"]]
        self.data["second"] = [i[1] for i in d_at_level["corr"]]
        self.data["corr"] = [i[2] for i in d_at_level["corr"]]
        self.data["corr_abs"] = [i[3] for i in d_at_level["corr"]]

        self.number_of_entries = len(d_at_level["corr"])

        #populate sub-population dot data (if present)
        self.get_subpop_data(d_at_level)

        #other variables
        self.number_of_entries = len(self.data["corr"])
        self.data["rank"] = [i+1 for i in range(0,self.number_of_entries)]
        self.data["y"] = [-i+1 for i in self.data["rank"]]

        #generate annotations for bars
        self.data["annotation1"] = [self.data["first"][i] for i in range(0,self.number_of_entries)]
        self.data["annotation2"] = [self.data["second"][i] for i in range(0,self.number_of_entries)]
        self.data["corr_formatted"] = [round(i,2) for i in self.data["corr"]]

        #generate x value plotting points for annotations
        self.data["x_annotations"] = [self.plot_start for i in range(0,self.number_of_entries)]
        self.data["x_corr"] = [self.data["corr_abs"][i] for i in range(0,self.number_of_entries)]

        #get number of pos, neg and total correlations 
        self.totals = {"pos":0, "neg":0, "total":0}
        for c in self.data["corr"]:
            if c >= 0: 
                self.totals["pos"] += 1
            elif c<0:
                self.totals["neg"] += 1

        self.totals["total"] = self.totals["pos"] + self.totals["neg"]

        # with open('out.json', 'w') as f:
        #     json.dump(self.data, f)

        self.source = ColumnDataSource(data=self.data)


    def get_subpop_data(self, d_at_level):

        #populate the self.data[s], i.e. correlation values wrt sub-pop (or "NA" is not present)
        if "subs" in d_at_level.keys():
            for s in d_at_level["subs"].keys():
                self.subpops.append(s)
                self.data[s] = []
                for i in d_at_level["corr"]:
                    pair_search = (i[0], i[1])
                    self.data[s].append("NA")
                    for j in d_at_level["subs"][s]["corr"]:
                        pair_try = (j[0], j[1])
                        pair_try2 = (j[1], j[0])
                        if pair_search == pair_try or pair_search == pair_try2:
                            self.data[s][-1] = j[2]
                            break

            #corr_abs values for dots:
            for s in self.subpops:
                self.data[s+"_abs"] = self.new_list(self.data[s], criteria="", apply = "abs" )
            
            #create s_outlier and s_non_outlier
            #

            #initialise self.data[s+_outlier]=[] and self.data[s+_non_outlier]=[] for each subpop s 
            for s in self.subpops:
                self.data[s+"_outlier"] = []
                self.data[s+"_non_outlier"] = []

            #iterate through each variable pair
            for index in range(0,self.number_of_entries):
                
                #assemble list of self.data[s][index] for each s to determine the outliers
                subpop_corrs_for_variable_pair = [self.data[s][index] for s in self.subpops] #these values could all be "NA"

                if len([i for i in subpop_corrs_for_variable_pair if i != "NA"]) > 0:
                    lb, ub = self.outliers(subpop_corrs_for_variable_pair)
                else:
                    lb = None; ub = None
                
                for s in self.subpops: 
                    item = self.data[s][index]     
                    if item == "NA":
                        self.data[s+"_outlier"].append("NA")
                        self.data[s+"_non_outlier"].append("NA")
                    else:
                        if item > ub or item < lb:
                            self.data[s+"_outlier"].append(item)
                            self.data[s+"_non_outlier"].append("NA")
                        else:
                            self.data[s+"_outlier"].append("NA")
                            self.data[s+"_non_outlier"].append(item)

            #
            #create s_outlier_pos, s_non_outlier_pos and s_outlier_neg, s_non_outlier_neg
            #     
            for s in self.subpops:
                self.data[s+"_outlier_pos"] = self.new_list(self.data[s+"_outlier"], criteria=">=0", apply = "abs")
                self.data[s+"_non_outlier_pos"] = self.new_list(self.data[s+"_non_outlier"], criteria=">=0", apply = "abs")

                self.data[s+"_outlier_neg"] = self.new_list(self.data[s+"_outlier"], criteria="<0", apply = "abs")
                self.data[s+"_non_outlier_neg"] = self.new_list(self.data[s+"_non_outlier"], criteria="<0", apply = "abs")


    def new_list(self,reference_list,criteria = "", apply = None):

        '''
            create a new list of ...based on a reference list and criteria
            Args:
                reference_list:     The base list, from which values are incorporated if criteria met, otherwise "NA" appended to new list
                critera:            Inclusion criteria, as a string, e.g. ">=0"
                apply:              function to apply to reference_list values
        '''

        new = []
        for item in reference_list:
            if item != "NA":
                if eval(str(item) + criteria): 
                    if apply == None:
                        to_append = item
                    else:
                        to_append = list(map(eval(apply), [item]))[0]
                    new.append(to_append)
                else:
                    new.append("NA")
            else:
                new.append("NA") 
                
        return new

    def colours_for_subpops(self):

        available_colours = ['#003f5c', '#2f4b7c', '#665191', '#a05195', '#d45087', '#f95d6a', '#ff7c43','#ffa600',
                            "Green", "DarkSlateBlue",
                            "BlueViolet", "Crimson", "Navy","OliveDrab", "HotPink",
                            "CornflowerBlue", "DarkOrange","Plum","MistyRose","Moccasin",
                            "LightSkyBlue", "DarkRed", "PaleVioletRed", "Lime","DarkBlue"
                           ]


        #iterate through the sub-pops; give colour to those subpops with outliers
        colours_used = 0

        for s in self.subpops:
            if len([i for i in self.data[s+"_outlier"] if i != "NA"])>0:
                self.colours[s] = available_colours[colours_used]
                colours_used += 1
            else:
                self.colours[s] = "lightgrey"

    def outliers(self,dataset):
        '''
            return (lowerbound, upperbound) i.e. the boundaries outside which elements in the data set are deemed outliers
            Args:
                dataset:   a list of values
        '''
        dataset = [d for d in dataset if d!="NA"]

        q1, q3 = np.percentile(dataset,[25,75])
        iqr = q3 - q1
        lowerbound = q1 -(1.5 * iqr) 
        upperbound = q3 +(1.5 * iqr) 

        return (lowerbound, upperbound)

    def generate(self, tab="all", by = "descending"):

        ##amend self.data and output new self.source depending on 
        if tab == "positive":
            df = pd.DataFrame.from_dict(self.data)
            self.data=df[df["corr"] >= 0.0].to_dict("list")

        elif tab == "negative":
            df = pd.DataFrame.from_dict(self.data)
            self.data=df[df["corr"] <= 0.0].to_dict("list")
        else:
            pass

        self.number_of_entries = len(self.data["corr"])
        self.data["rank"] = [i+1 for i in range(0, self.number_of_entries)]
        self.data["y"] = [-i+1 for i in self.data["rank"]]
        self.order(by=by)

        self.source = ColumnDataSource(data=self.data) 

        ##setup basic plot
        self.plot = figure(plot_width=850, 
                           plot_height=self.number_of_entries*90, 
                           toolbar_location=None,
                           tools ="",
                           y_range=(-1*self.number_of_entries, 1),
                          ) # "ywheel_pan" = closest to scroll

        ##turn off axes and x/y grid
        self.plot.axis.visible = False
        self.plot.xgrid.grid_line_color = None
        self.plot.ygrid.grid_line_color = None

        ##add the bar plots
        self.add_bars()

        ##add dots
        hover_tools = []
        renderers = []

        #plot dots
        if len(self.subpops) > 0:
            self.colours_for_subpops()

            for s in self.subpops:
                h, r = self.add_dots(s, "lightgrey", "_non_outlier_pos", "green")
                hover_tools.append(h) ; renderers.append(r)

                h, r = self.add_dots(s, "lightgrey", "_non_outlier_neg", "red")
                hover_tools.append(h) ; renderers.append(r)

                h, r = self.add_dots(s, self.colours[s], "_outlier_pos", "green", extra_tips=" (outlier)")
                hover_tools.append(h) ; renderers.append(r)

                h, r = self.add_dots(s, self.colours[s], "_outlier_neg", "red", extra_tips=" (outlier)")
                hover_tools.append(h) ; renderers.append(r)

            #plot
            self.plot.tools.extend(hover_tools)
            self.plot.renderers.extend(renderers)

        # #add annotations
        self.annotate_bars()
        self.annotate_corr()

    def add_bars(self):
        '''
            add (abs) correlation value bars to the graph
        '''

        #plot the bars
        self.data["bar_colours"] = []
        for index,c in enumerate(self.data["corr"]):

            #determine bar colour based on positive or negative correlation values
            if c < 0: 
                colour = "lightcoral"
            else:
                colour = "darkseagreen"

            self.data["bar_colours"].append(colour)
        
        self.source = ColumnDataSource(data=self.data)

        # self.plot.hbar(y=-1*index, height=self.bar_scale, left=self.plot_start,right=[abs(c)], color=colour) 
        self.plot.hbar(y="y", height=self.bar_scale, left=self.plot_start,right="corr_abs", color="bar_colours", source = self.source) 



    def add_dots(self, sub, colour, suffix, line_colour, extra_tips = None):
        '''
            return the Hovertool object and renderer object for plotting sub-population corr dots with tooltips
        
        '''
        #reference example
        #https://github.com/bokeh/bokeh/blob/f76ccc44fb39007743ffbe71659b282759915653/examples/glyphs/data_tables.py
        
        #outer line colour indicates whether sup-population correlation pos or neg


        glyph = Circle(x=sub+suffix, y="y", fill_color=colour, line_color=line_colour, line_width = 1 , size=15, fill_alpha=1, line_alpha=1)
        renderer = GlyphRenderer(data_source=self.source, glyph=glyph)

        if extra_tips:
            return HoverTool(renderers=[renderer], tooltips=[(sub, "@{" + sub + "}" + extra_tips)]), renderer
        else:
            return HoverTool(renderers=[renderer], tooltips=[(sub, "@{" + sub + "}")]), renderer
        

    def annotate_bars(self):
        '''
            annotate plot with var1 vs var2 labels
            assumes: self.source = {"corr"=[], .... }
        '''
        #plot the annotations
        labels1 = LabelSet(x='x_annotations', y='y', text='annotation1', text_font_size = "8pt", level='overlay',
              x_offset=0, y_offset=32, source=self.source, render_mode="canvas")
        
        labels2 = LabelSet(x='x_annotations', y='y', text='annotation2', text_font_size = "8pt",level='overlay',
              x_offset=0, y_offset=22, source=self.source, render_mode='canvas')

        labels3 = LabelSet(x=0, y='y', text="rank", text_font_size = "8pt",level='overlay',
              x_offset=-25 , y_offset=-5 , source=self.source, render_mode='canvas')
        
        self.plot.add_layout(labels1)
        self.plot.add_layout(labels2)
        self.plot.add_layout(labels3)

    def annotate_corr(self):
        '''
            append correlation values to plots as annotations
        '''
        #append annotations to the plot
        labels = LabelSet(x='x_corr', y='y', text="corr_formatted", text_font_size = "8pt", level='overlay',
              x_offset=4, y_offset=9, source=self.source, render_mode='canvas')

        self.plot.add_layout(labels)
        
    def order(self, by="descending"):
        '''
            re-assign self.data["y"] values based on self.data["corr"] values
        '''

        rows = list(range(0, self.number_of_entries))

        #find row order based on self.data["corr_abs"]
        if by == "descending":
            rows = [x for _, x in sorted(zip(self.data["corr_abs"],rows), reverse = True)] 
        elif by == "ascending":
            rows = [x for _, x in sorted(zip(self.data["corr_abs"],rows), reverse = False)] 

        #assign self.data["rank values"] accordingly
        for index,i in enumerate(rows):
            self.data["rank"][i] = index + 1
        self.data["y"] = [-i+1 for i in self.data["rank"]]

        
        self.source = ColumnDataSource(data=self.data)

    def get_subs(self):
        '''
            return a list of sub-populations 1 layer deep wrt current view and a list of associated colours
        '''
      
        return self.subpops


    def get_colours(self):

        return self.colours


    def get_totals(self):

        return self.totals
        

