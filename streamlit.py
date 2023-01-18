# This Python 3 environment comes with many helpful analytics libraries installed
# It is defined by the kaggle/python Docker image: https://github.com/kaggle/docker-python
# For example, here's several helpful packages to load

import streamlit as st
import numpy as np # linear algebra
import pandas as pd # data processing, CSV file I/O (e.g. pd.read_csv)
import seaborn as sns
import plotly.express as px
import requests
import json
import re
from pandas import json_normalize
from datetime import datetime
from scipy.stats import norm
from html.parser import HTMLParser

st.set_option('deprecation.showPyplotGlobalUse', False)


skill2searchTerm = st.sidebar.multiselect('Skill that you have?',
['SAP', 'Java', 'PHP', 'Magento', 'GIS', 'C++', 'Python', 'JavaScript', 'AWS', 'React'],
['SAP', 'Java', 'PHP'])


location = st.sidebar.selectbox('Your location?',
('D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8', 'D9'),
0)

applicantsPerProject = st.sidebar.slider(
    "Applicants per Project",
    1, 30, 15
)

stundensatz = st.sidebar.slider(
    "Stundensatz",
    1, 200, 65
)

weeks = st.sidebar.slider(
    "Wochen",
    1, 6, 2
)

@st.cache(allow_output_mutation=True)
def loadSearchResults(skill2searchTerm):
    skill2searchResults = {}

    for skill in skill2searchTerm:
        r = requests.post("https://www.gulp.de/gulp2/rest/internal/projects/search", data=json.dumps({"query":skill,"regions":[],"cities":[],"projectTypes":[],"limit":1000,"page":0}), headers={'Content-Type':'application/json', 'Accept': 'application/json'})
        json_body = r.json()
        skill2searchResults[skill] = json_body
    return skill2searchResults

skill2searchResults = loadSearchResults(skill2searchTerm)

st.markdown("# Aktuelle Anzahl von Projekten nach Skill")

skill2totalCount = {"x": [], "y": []}
for skill, projects in skill2searchResults.items():
    skill2totalCount["x"].append(skill)
    skill2totalCount["y"].append(projects["totalCount"])
ax = sns.barplot(x="x", y="y", data=skill2totalCount)
st.pyplot()
projects = []
for skill, jsonProjects in skill2searchResults.items():
    for project in jsonProjects["projects"]:
        project["skill"] = skill
        projects.append(project)

dfProjects = pd.DataFrame.from_dict(projects)
dfProjects['originalPublicationDate'] = pd.to_datetime(dfProjects['originalPublicationDate'])
dfProjects['weekNumber'] = dfProjects['originalPublicationDate'].dt.isocalendar().week.astype("int64")
dfProjects


st.markdown("# Projekte nach Veröffentlichung")

dfProjectsByWeek = dfProjects.groupby(['weekNumber', 'skill']).size().reset_index(name='counts')
# Plot the responses for different events and regions
sns.lineplot(x="weekNumber", y="counts", hue="skill", style="skill", markers=True, dashes=False,
             data=dfProjectsByWeek)
st.pyplot()

st.markdown("# Projekte der letzten 2 Wochen")
currentCalendarWeek = datetime.now().isocalendar()[1]
lastTwoWeeks = dfProjectsByWeek[list(map(lambda x : x in [currentCalendarWeek, currentCalendarWeek-1], dfProjectsByWeek["weekNumber"]))]
# Plot the responses for different events and regions
sns.lineplot(x="weekNumber", y="counts", hue="skill", style="skill", markers=True, dashes=False,
             data=lastTwoWeeks)
st.pyplot()


st.markdown("# Projekte der letzten 2 Wochen in "+location)
currentCalendarWeek = datetime.now().isocalendar()[1]
lastTwoWeeksD1 = dfProjects[(dfProjects["location"] == location) | ((location == 'D1') & (dfProjects["location"] == "Berlin"))].groupby(['weekNumber', 'skill']).size().reset_index(name='counts')
lastTwoWeeksD1 = lastTwoWeeksD1[list(map(lambda x : x in [currentCalendarWeek, currentCalendarWeek-1], lastTwoWeeksD1["weekNumber"]))]
# Plot the responses for different events and regions
try:
    sns.lineplot(x="weekNumber", y="counts", hue="skill", style="skill", markers=True, dashes=False,
             data=lastTwoWeeksD1)
    st.pyplot()
except Exception as err:
    print(f"Unexpected {err=}, {type(err)=}")

lastTwoWeeksD1 = lastTwoWeeks

skills2averageWeeklyEventsInLastTwoWeeks = lastTwoWeeksD1[['skill', 'counts']][list(map(lambda x : x in [currentCalendarWeek-1], lastTwoWeeksD1["weekNumber"]))].groupby('skill').mean()

@st.cache
def loadStundensatzHtml():
    skill2StundensatzHtml = {}
    for skill in skill2searchTerm:
        r = requests.get("https://www.gulp.de/cgi-gulp/trendneu.exe/MONEYFORMDLL?txtPosition=Softwareentwickler+&txtFachSchwer="+skill+"&lstvAndOr=und&resultsample=50")
        html_body = r.text
        skill2StundensatzHtml[skill] = r.text
    return skill2StundensatzHtml

skill2StundensatzHtml = loadStundensatzHtml()

class MyHTMLParser(HTMLParser):
    
    first = True
    table = 0
    amountDisplayFetching = False
    stundensatzFetching = False
    avgStundensatz = None
    stundensaetze = []
    tdCount = 0
    
    def handle_starttag(self, tag, attrs):
        if(tag == "table"):
            self.table += 1
        if(tag == "td" and self.table == 2):
            self.tdCount += 1
            # start with the second row
            if(self.tdCount > 4 and self.tdCount%4 == 3):
                self.stundensatzFetching = True
        if(len(attrs) > 0 and attrs[0][0] == "class" and attrs[0][1] == "amount-display"):
            self.amountDisplayFetching = True

    def handle_endtag(self, tag):
        self.amountDisplayFetching = False
        self.stundensatzFetching = False

    def handle_data(self, data):
        if(self.amountDisplayFetching and self.first):
            self.first = False
        if(self.amountDisplayFetching and not self.first):
            self.avgStundensatz = int(re.sub("[^0-9.\-]","",data))
        if(self.stundensatzFetching):
            self.stundensaetze.append(int(re.sub("[^0-9.\-]","",data)))
    


skill2searchResultsForDf = {"skill":[], "avgStundensatz":[], "stdStundensatz":[]}

for skill, html in skill2StundensatzHtml.items():
    parser = MyHTMLParser()
    parser.feed(html)
    skill2searchResultsForDf["skill"].append(skill)
    skill2searchResultsForDf["avgStundensatz"].append(parser.avgStundensatz)
    stdStundensatz = np.std(parser.stundensaetze)
    skill2searchResultsForDf["stdStundensatz"].append(stdStundensatz)

sns.barplot(x="skill", y="avgStundensatz", data=skill2searchResultsForDf)
st.pyplot()
skill2searchResultsDf = pd.DataFrame.from_dict(skill2searchResultsForDf)

skills2data = pd.merge(skills2averageWeeklyEventsInLastTwoWeeks, skill2searchResultsDf, on='skill')

probabilityWinningNoProject = 1
probabilitToWinProjectWithSkill = {}
probabilityToWinAProjectWithSkills = []
for index, row in skills2data.iterrows():
    probabilityToWinOneProject = pow((1-norm.cdf(stundensatz, row["avgStundensatz"], row["stdStundensatz"])), applicantsPerProject)
    probabilityToWinAProjectWithSkill = 1
    for x in range(int(row["counts"]*weeks)):
        probabilityWinningNoProject = probabilityWinningNoProject*(1-probabilityToWinOneProject)
        probabilityToWinAProjectWithSkill = probabilityToWinAProjectWithSkill*(1-probabilityToWinOneProject)
    probabilityToWinAProjectWithSkills.append(1-probabilityToWinAProjectWithSkill)

skills2data["probabilityToWinAProjectWithSkill"] = probabilityToWinAProjectWithSkills
fig = px.pie(skills2data, names="skill", values="probabilityToWinAProjectWithSkill", title="Wenn ein Projekt gewonnen wir, dann wahrscheinlich mit diesem Skill")
st.plotly_chart(fig)

st.write("Wahrscheinlichkeit ein Projekt im Bereich {} innerhalb von {} Wochen mit einem Stundensatz von {} € mit {} Bewerben zu gewinnen".format(skill2searchTerm, weeks, stundensatz, applicantsPerProject))

st.write("<div style=\"font-size: 3rem; text-align: center\">{:.2f}%</div>".format((1-probabilityWinningNoProject)*100), unsafe_allow_html=True) 
skills2data
