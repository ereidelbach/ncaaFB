#!/usr/bin/env python3.7
# -*- coding: utf-8 -*-
"""
Created on Mon Nov 12 12:56:56 2018

@author: ejreidelbach

:DESCRIPTION:

:REQUIRES:
   
:TODO:
    
"""
 
#==============================================================================
# Package Import
#==============================================================================
import datetime
import numpy as np
import os  
import pandas as pd
import pathlib
import re
import requests
from bs4 import BeautifulSoup

#==============================================================================
# Function Definitions / Reference Variable Declaration
#==============================================================================
def soupifyURL(url):
    '''
    Purpose: Turns a specified URL into BeautifulSoup formatted HTML 

    Input: url (string): Link to the designated website to be scraped
    
    Output: soup (html): BeautifulSoup formatted HTML data stored as a
        complex tree of Python objects
    '''
    r = requests.get(url)
    soup = BeautifulSoup(r.content,'html.parser')   
    return soup

def scrapeTeamNames():
    '''
    Purpose: Scrapes and extracts the URL for every division FBS
        team on the CFBStats website. The team name and associated URL
        are stored in the dictionary `dict_teams` which is returned by
        this function.
        
    Input:
        - NONE
        
    Output:
        - dict_teams (dictionary): Dictionary containing all FBS teams
                and the URL to their respective team page
    '''
    # Turn the main page into BeautifulSoup HTML
    soup = soupifyURL('http://www.cfbstats.com/')
    
    # Extract the team links found on the left-hand side of the screen
    html_teams = soup.find('ul', class_='sub1')
    html_teams_clean = html_teams.findAll('li', class_='sub1')

    dict_teams = {}
    
    # Iterate over every team on the site and extract its url
    for team in html_teams_clean:
        # Use the team name as the key, the url as the value
        dict_teams[team.text] = team.find('a', href=True)['href']
        
    return dict_teams

def directoryCheck(team_name):
    '''
    Purpose: Run a check of the /Data/CFBStats/ folder to see if a folder
        exists for the specified team.  If it doesn't, create it.
        
    Input:
        - team_name (string): Name of the school being scraped
    
    Outpu:
        - NONE
    '''
    pathlib.Path('Data/CFBStats/'+team_name).mkdir(parents=True, exist_ok=True)

def scrapeTeamYears(team_url):
    '''
    Purpose: Given a team, scrape the URL for every year of statistics that is
        on file for that team
    
    Input:
        - team_url (string): URL of the school's page on CFBStats.com
    
    Output:
        - dict_years (dictionary): Dictionary containing every year for which
            team statistics are recorded and the URL to those statistics
    '''
    # Turn the page into BeautifulSoup HTML
    soup = soupifyURL('http://www.cfbstats.com' + team_url)
    
    # Extract the years (and associated URLs) for the team's historic stats
    html_years = soup.find('div', {'id':'seasons'})
    html_years_clean = html_years.findAll('li')[1:] # Avoid `SELECTED` LI
    
    dict_years = {}
    
    # Iterate over every year and place the year-URL combo into a dictionary
    for year in html_years_clean:
        dict_years[year.text] = year.find('a', href=True)['href']

    # Add the current year to the dictionary
    dict_years[team_url.split('/')[1].split('/')[0]] = team_url
    
    return dict_years

def scrapeTeamRecords(team_name, dict_years):
    '''
    Purpose: Scrape the record's portion of a team's stats for all season
        
    Input:
        - team_name (string): Name of the school being scraped
        - dict_years (dictionary): Dictionary containing every year for which
            team statistics are recorded and the URL to those statistics
    
    Output:
        - A .csv file containing the scraped information (records.csv)
    '''
    # Create the master dictionary for storing records for all seasons/years
    dict_records = {}
    
    # Scrape each year contained in `dict_years`
    for year, url in dict_years.items():
        # Create a dictionary for the year being scraped
        dict_year = {}
        
        # Retrieve the HTML data at the specified URL and add it to `dict_year`
        soup = soupifyURL('http://www.cfbstats.com' + url)
        table_record = soup.find('table', {'class':'team-record'})
        for row in table_record.findAll('tr')[1:]:  # ignore table header
            
            # Specify the Name of the Split being scraped (e.g. `All Games`)
            split_name = row.find('td', {'class':'split-name'}).text
            
            # Values will be stored for `Wins`, `Losses` and `Win Pct`
            # Wins
            dict_year[split_name + ' (Wins)'] = row.findAll(
                                                    'td')[1].text.split('-')[0]
            # Losses
            dict_year[split_name + ' (Losses)'] = row.findAll(
                                                    'td')[1].text.split('-')[1]
            # Win Pct
            if dict_year[split_name + ' (Losses)'] == '0': # Handle divide by 0
                dict_year[split_name + ' (Win %)'] = 0  
            else:
                dict_year[split_name + ' (Win %)'] = round(int(
                    dict_year[split_name + ' (Wins)']) / int(
                            dict_year[split_name + ' (Losses)']), 2)
                
            # Add year to master dictionary
            dict_records[year] = dict_year
    
    # Convert `dict_records` to a Pandas DataFrame
    df_records = pd.DataFrame.from_dict(dict_records, orient='index')
    
    # Export the newly created Pandas DataFrame to a .csv
    df_records.to_csv('Data/CFBStats/' + team_name + '/records.csv')
    
def scrapeTeamSchedules(team_name, dict_years):
    '''
    Purpose: Scrape the schedule portion of a team's stats for all seasons
        
    Input:
        - team_name (string): Name of the school being scraped
        - dict_years (dictionary): Dictionary containing every year for which
            team statistics are recorded and the URL to those statistics
    
    Output:
        - A .csv file containing the scraped information (schedules.csv)
    '''
    # Create the master dictionary for storing schedules for all seasons/years
    dict_schedules = {}
    
    # Scrape each year contained in `dict_years`
    for year, url in dict_years.items():
        # Create a dictionary for the year being scraped
        dict_year = {}
        
        # Retrieve the HTML data at the specified URL and add it to `dict_year`
        soup = soupifyURL('http://www.cfbstats.com' + url)
        table_schedule = soup.find('table', {'class':'team-schedule'})
        
        # Loop over all games in the schedule (ignore table headers)
        for row_index, row in enumerate(table_schedule.findAll('tr')[1:-1]):  
            dict_year = {}
                       
            # Scrape Date into `Year`, `Month`, `Day`, and `Weekday` Variables
            date = row.find('td', {'class':'date'}).text
            dict_year['year'] = int(datetime.datetime.strptime(date,
                     "%m/%d/%y").strftime('%Y'))
            dict_year['month'] = datetime.datetime.strptime(date,
                     "%m/%d/%y").strftime('%B')
            dict_year['day'] = int(datetime.datetime.strptime(date,
                     "%m/%d/%y").strftime('%e').strip())
            dict_year['day_of_week'] = datetime.datetime.strptime(date,
                     "%m/%d/%y").strftime('%A')
            dict_year['date'] = date
            
            # Scrape where the game was played (Home or Away)
            opponent = row.find('td', {'class':'opponent'}).text
            if opponent.split(' ')[0] == '@':
                dict_year['home_away'] = 'Away'
                opponent = opponent.replace('@ ','')
            elif opponent.split(' ')[0] == '+':
                dict_year['home_away'] = 'Neutral'
                opponent = opponent.replace('+ ','')
            else:
                dict_year['home_away'] = 'Home'
            
            # Scrape the Opponent's AP ranking
            try:
                dict_year['opp_rank'] = int(opponent.split(' ')[0])
            except:
                dict_year['opp_rank'] = np.nan

            # Scrape the Opponent
            dict_year['opponent'] = ''.join(
                    [s for s in opponent if not re.search(r'\d',s)]).strip()
            
            # Scrape the Result (Win or Loss)
            score = row.find('td', {'class':'result'}).text
            if score == '':
                dict_year['result'] = ''
            else:
                dict_year['result'] = score[0]
            
            # Scrape the Team's Points total
            if score == '':
                dict_year['pts_for'] = np.nan
            else:
                dict_year['pts_for'] = int(score.split(' ')[1].split('-')[0])

            # Scrape the Opponent's Points Total
            if score == '':
                dict_year['pts_against'] = np.nan
            else:
                dict_year['pts_against'] = int(score.split(' ')[1].split('-')[1])
                
            # Calculate the point difference between the teams
            dict_year['pts_diff'] = dict_year['pts_for'] - dict_year['pts_against']
            
            # Scrape the Game Time (hh:mm)
            if row.findAll('td')[3].text == '':
                dict_year['game_time_hh'] = np.nan
                dict_year['game_time_mm'] = np.nan
            else:
                dict_year['game_time_hh'] = int(
                        row.findAll('td')[3].text.split(':')[0])
                dict_year['game_time_mm'] = int(
                        row.findAll('td')[3].text.split(':')[1])
            
            # Scrape the Attendance
            if row.findAll('td')[4].text == '':
                dict_year['attendance'] = np.nan
            else:
                dict_year['attendance'] = int(
                        row.findAll('td')[4].text.replace(',',''))
            
            # Add year to master dictionary
            idx = str(row_index).zfill(2)
            dict_schedules[str(dict_year['year']) +'_' + idx] = dict_year
    
    # Convert `dict_schedules` to a Pandas DataFrame
    df_schedules = pd.DataFrame.from_dict(dict_schedules, orient='index')
    
    # Export the newly created Pandas DataFrame to a .csv
    df_schedules.to_csv('Data/CFBStats/' + team_name + '/schedules.csv')

def scrapeTeamSplitStats(team_name, dict_years):
    '''
    Purpose: Scrape the split statistics for every available year for
        every available statistical category
        
    Input:
        - team_name (string): Name of the school being scraped
        - dict_years (dictionary): Dictionary containing every year for which
            team statistics are recorded and the URL to those statistics
    
    Output:
        - A .csv file containing the scraped information (CategorySplitStats.csv)
    '''

def scrapeTeamGameLogs(team_name, dict_years):
    '''
    Purpose: Scrape the statistical game logs for every available year for
        every available statistical category
        
    Input:
        - team_name (string): Name of the school being scraped
        - dict_years (dictionary): Dictionary containing every year for which
            team statistics are recorded and the URL to those statistics
    
    Output:
        - A .csv file containing the scraped information (CategoryLogs.csv)
    '''

def nameFirst(name):
    '''
    Purpose: Extract the first name from a player's name formatted as 
        `Last Name, First Name`
        first and last name variables (accounting for suffixes such as Jr./Sr.)
    
    Input:
        - name (string): Player's name in the format `Last name, First name`
    
    Output:
        - (string): The player's first name
    '''
    list_split_name = name.split(', ')   # split name on `, `
    
    if len(list_split_name) == 1:       # handle 1-word names
        return('')
    elif len(list_split_name) == 2:     # handle 2-word names
        return(list_split_name[1])
    else:                               # handle 3-word names
        return(list_split_name[2])

def nameLast(name):
    '''
    Purpose: Extract the last name from a player's name formatted as 
        `Last Name, First Name` (accounting for suffixes such as Jr./Sr.)
    
    Input:
        - name (string): Player's name in the format `Last name, First name`
    
    Output:
        - (string): The player's last name (to include suffixes)
    '''
    list_split_name = name.split(', ')   # split name on `, `
    
    if len(list_split_name) == 1:       # handle 1-word names
        return(name)
    elif len(list_split_name) == 2:     # handle 2-word names
        return(list_split_name[0])
    else:                               # handle 3-word names
        return(list_split_name[0] + ' ' + list_split_name[1])
            
def heightInches(height):
    '''
    Purpose: Convert a height variable formatted in `Feet - Inches` into
        a variable of inches only (i.e. feet * 12 inches + inches)
        
    Input:
        - height (string): Height of player formatted in `Feet - Inches`
    
    Output:
        - (int): Height of player in total inches
    '''        
    if height == '-':
        return(np.nan)
    else:
        heightFeet = int(height.split('-')[0])
        heightInches = int(height.split('-')[1])
        
        return(heightFeet*12 + heightInches)

def scrapeTeamRosters(team_name, dict_years):
    '''
    Purpose: Scrape the roster for every available year
        
    Input:
        - team_name (string): Name of the school being scraped
        - dict_years (dictionary): Dictionary containing every year for which
            team statistics are recorded and the URL to those statistics
    
    Output:
        - A .csv file containing the scraped information (Rosters.csv)
    '''
    # Create the master dictionary for storing schedules for all seasons/years
    df_rosters = pd.DataFrame()
    
    # Scrape each year contained in `dict_years`
    for year, url in dict_years.items():

        # Create the roster URL
        url_roster = url.split('index.html')[0] + 'roster.html'
        
        # Retrieve the HTML data at the specified URL and add it to `dict_year`
        soup = soupifyURL('http://www.cfbstats.com' + url_roster)
        table_roster = soup.find('table', {'class':'team-roster'})    
        
        # Convert the roster into a pandas dataframe
        df_year = pd.read_html(str(table_roster))[0]
        
        # Make the first row the column names, then remove the first row
        df_year.columns = list(df_year.iloc[0])
        df_year.drop(df_year.index[0], inplace=True)
        
        # Add a year column to track the season the roster is for
        df_year['season'] = int(year)
        
        # Append the year DataFrame to the master DataFrame
        df_rosters = df_rosters.append(df_year)
        
    # Create a First Name Variable
    df_rosters['name_first'] = df_rosters['Name'].apply(lambda x: nameFirst(x))

    # Create a Last Name Variable
    df_rosters['name_last'] = df_rosters['Name'].apply(lambda x: nameLast(x))
            
    # Create a Height (Inches) Variable
    df_rosters['height_inches'] = df_rosters['Ht'].apply(lambda x: heightInches(x))
    
    # Create a Hometown (City) Variable
    df_rosters['city'] = df_rosters['Hometown'].apply(lambda x: x.split(', ')[0])
    
    # Create a Hometown (State) Variable
    def toState(hometown):
        if hometown == '-':
            return hometown
        elif len(hometown.split(', ')) == 1:
            return hometown
        else:
            return(hometown.split(', ')[1])                
    df_rosters['state'] = df_rosters['Hometown'].apply(lambda x: toState(x))

    
    # Remove unnecessary columns, rename columns, and reorder columns
    df_rosters.drop(['Name', 'Hometown'], axis = 1, inplace=True)
    df_rosters.rename(columns = {'No':'number', 'Pos':'position', 'Yr':'year',
                                 'Ht':'height', 'Wt':'weight', 
                                 'Last School':'prev_school'}, inplace=True)
    df_rosters = df_rosters[['season', 'name_last', 'name_first', 'number', 
                             'position', 'year', 'height', 'height_inches', 
                             'weight', 'city', 'state',
                             'prev_school']]
    
    # Reformat the weight column to a numeric value
    df_rosters['weight'] = df_rosters['weight'].apply(
            lambda x: int(x) if x != '-' else np.nan)

    # Export the newly created Pandas DataFrame to a .csv
    df_rosters.to_csv('Data/CFBStats/' + team_name + '/rosters.csv', index=False)

def scrapeTeamStats(team_name, team_url):
    '''
    Purpose: Direct the scraping all the statistical information for all
        college teams on CFBStats.com
        
    Input:
        - team_name (string): Name of the school being scraped
        - team_url (string): URL of the school's page on CFBStats.com
    
    Output:
        - None
    '''
    # Check to see if the team's directory exists (and if not -> make it)
    directoryCheck(team_name)
    
    # Obtain links to obtain info for every year available for the team
    dict_years = scrapeTeamYears(team_url)
       
#    # Scrape Record (i.e. wins-losses) for every year 
#    scrapeTeamRecords(team_name, dict_years)
#    
#    # Scrape Schedule information for every year
#    scrapeTeamSchedules(team_name, dict_years)

    # Scrape Rosters for every year
    scrapeTeamRosters(team_name, dict_years)
    
#    # Scrape Split Statistics for every year
#    scrapeTeamSplitStats(team_name, dict_years)
#
#    # Scrape Statistical Game Logs for every year
#    scrapeTeamGameLogs(team_name, dict_years)
    
    # Provide a status update
    print('Done with: ' + team_name)
    
'''
- soup (HTML): BeautifulSoup version of HTML for a team's season    
'''
    
#==============================================================================
# Working Code
#==============================================================================

# Set the project working directory
os.chdir(r'/home/ejreidelbach/Projects/CollegeFootball')

# Start a headless browser of Firefox 
#browser = initiateBrowser('http://www.cfbstats.com/', True)

# Create a dictionary of team names and links
dict_teams = scrapeTeamNames()

# Scrape the stats for each team (creating CSV files along the way)
for team_name, team_url in dict_teams.items():
    scrapeTeamStats(team_name, team_url)