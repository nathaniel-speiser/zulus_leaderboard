import pandas as pd
import os
import glob
import streamlit as st

def expected_score(rating_a, rating_b):
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))

def new_rating(rating, expected, actual, k=20):
    return rating + k * (actual - expected)

players_df = pd.read_csv('data/players.csv')
players_list = list(players_df['player_tag'])

data_path = os.path.join(os.getcwd(),'data')
results_files = sorted(glob.glob(os.path.join(data_path,'results_*')))

elos = {}

for player in players_list:
    elos[player] = [1200]

def update_elo(result_path: str, elo_dict):
    """
    Update elo dict for one week of results
    :param result_path: Path to result csv
    :param elo_dict: Global elo history dictionary
    :return:
    """
    result_df = pd.read_csv(result_path)

    # Get most recent elos:
    new_elos = {key: elo_dict[key][-1] for key in elo_dict.keys()}
    print(f'Starting elo values: {new_elos}')

    for _, row in result_df.iterrows():
        if row['draw']:
            #If there was a draw for some reason skip the update
            continue
        p1 = row['player1']
        p2 = row['player2']
        p1_win = 1 if row['player1_win'] else 0
        p2_win = 1-p1_win

        p1_elo = new_elos[p1]
        p2_elo = new_elos[p2]

        expected_p1_score = expected_score(p1_elo, p2_elo)
        expected_p2_score = expected_score(p2_elo, p1_elo)

        new_p1_elo = new_rating(p1_elo, expected_p1_score, p1_win)
        new_p2_elo = new_rating(p2_elo, expected_p2_score, p2_win)

        new_elos[p1] = new_p1_elo
        new_elos[p2] = new_p2_elo

    for player in elo_dict.keys():
        elo_dict[player].append(new_elos[player])


def calculate_elo_history(file_list, elo_dict):
    for result_file in file_list:
        update_elo(result_file, elo_dict)

def get_all_match_df(file_list):
    match_df = pd.DataFrame()
    for file in file_list:
        tournament_date = file.split('_')[-1].replace('.csv','')
        new_df = pd.read_csv(file)
        new_df['tournament_date'] = [tournament_date] * len(new_df)
        match_df = pd.concat([match_df,new_df], ignore_index=True)
    return match_df

calculate_elo_history(results_files, elos)

print(elos)

print(get_all_match_df(results_files))