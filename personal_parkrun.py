# -*- coding: utf-8 -*-
"""
Personal parkrun
Created on Thu Apr 27 13:30:12 2017

@author: scotw
"""
import pandas as pd
from os import path

__version__ = 2.0


def personal_parkrun_df(name):
    """
    Converts personal table of parkruns from
    http://www.parkrun.org.uk/results/athleteresultshistory/?athleteNumber=1086827
    to dictionary

    Use excel, data from web to import Event Summaries table from
    http://www.parkrun.org.uk/results/athleteresultshistory/?athleteNumber=1086827
    and save as name_parkruns.csv
    """

    # import personal parkruns
    subfolder = path.normpath("user")
    filename = path.normpath(name+"_parkruns.csv")
    user_file = path.join(subfolder, filename)
    if path.exists(user_file):
        personal_parkruns = pd.read_csv(user_file, engine="python")
    else:
        raise IOError("User parkrun file not found")
    personal_parkruns = personal_parkruns[["Event", "Runs"]]
    # remove nan events
    personal_parkruns.dropna(inplace=True)

    for index, row in personal_parkruns.iterrows():
        event = personal_parkruns.loc[index, "Event"]
        # remove word parkrun
        event = event.replace(" parkrun", "")
        if "," in event:
            comma = event.index(",")
            event = event[:comma]

        personal_parkruns.loc[index, "Event"] = event
    return personal_parkruns


def group_parkrun(names=[]):
    group_parkruns = pd.DataFrame({"Event": [""], "Runs": [0]})

    for name in names:
        personal_parkruns = personal_parkrun_df(name)
        for index, row in personal_parkruns.iterrows():
            event = row["Event"]
            if event in group_parkruns["Event"].values:
                group_parkruns.loc[group_parkruns.Event == event,
                                   "Runs"] += row["Runs"]
            else:
                group_parkruns = group_parkruns.append(row, ignore_index=True)
    group_parkruns = group_parkruns[group_parkruns.Event != ""]
    group_parkruns.reset_index(inplace=True, drop=True)
    return group_parkruns


if __name__ == "__main__":
    scot_tourism = personal_parkrun_df("scot")
    hayleigh_tourism = personal_parkrun_df("hayleigh")
#    group = group_parkrun(names=["scot", "hayleigh"])
