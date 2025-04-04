import pandas as pd
import os
import glob
import streamlit as st
import plotly.graph_objects as go
from datetime import datetime

def expected_score(rating_a, rating_b):
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))

def new_rating(rating, expected, actual, k=20):
    return rating + k * (actual - expected)

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


def elo_line_plot(elo_histories, focused_players=None):
    fig = go.Figure()

    num_weeks = len(elo_histories['Nath'])
    weeks = list(range(1, num_weeks+1))
    # Add teams with enhanced styling
    for player, elo_list in elo_histories.items():
        # Determine line styling based on whether this is a focused team
        if player in focused_players:
            line_width = 4
            opacity = 1.0
        else:
            line_width = 2
            opacity = 0.5

        # Add the line trace
        fig.add_trace(go.Scatter(
            x=weeks,
            y=elo_list,
            mode='lines',
            name=player,
            line=dict(
                width=line_width
            ),
            opacity=opacity,
            hovertemplate=f"{player}<br>Week: %{{x}}<br>Elo: %{{y}}<extra></extra>"
        ))

        # Add end-of-line labels
        if player in focused_players or not focused_players:
            fig.add_annotation(
                x=weeks[-1],
                y=elo_list[-1],
                xanchor='left',
                yanchor='middle',
                xshift=5,
                showarrow=False,
                font=dict(
                    size=10,
                ),
                opacity=opacity
            )

    fig.update_layout(
        title=dict(
            text='Player Elo Rating',
            x=0.5,
            y=0.95,
            xanchor='center',
            yanchor='top',
            font=dict(size=24)
        ),
        height=600,
        plot_bgcolor='white',
        showlegend=False,
        margin=dict(r=100),
        xaxis_title="Week",
        yaxis_title="Elo Rating",
        #xaxis_tickformat='%Y-%m-%d',
        hovermode='closest'
    )

    fig.update_xaxes(
        mirror=True,
        ticks='outside',
        showline=True,
        linecolor='black',
        gridcolor='lightgrey',
        zeroline=False,
        tickmode='linear',
        tick0=1,
        dtick=1
    )

    fig.update_yaxes(
        mirror=True,
        ticks='outside',
        showline=True,
        linecolor='black',
        gridcolor='lightgrey',
        zeroline=False,
        tickformat='.0f'
    )

    return fig
def main():

    data_path = os.path.join(os.getcwd(),'data')
    results_files = sorted(glob.glob(os.path.join(data_path,'results_*')))


    match_df = get_all_match_df(results_files)
    match_df['player1_deck'] = match_df['player1_deck'].fillna('Unknown')
    match_df['player2_deck'] = match_df['player2_deck'].fillna('Unknown')

    players_list = set(list(match_df['player1']) + list(match_df['player2']))


    date_list = sorted([file.split('_')[-1].replace('.csv','') for file in results_files])
    date_list.insert(0,'20250318')
    elos = {}

    for player in players_list:
        elos[player] = [1200]

    calculate_elo_history(results_files, elos)


    df_ratings = pd.DataFrame({
        'Player': list(elos.keys()),
        'Current Elo': [round(elo_list[-1], 1) for elo_list in elos.values()],
        'Change': [round(elos[player][-1] - elos[player][-2], 1) for player in elos.keys()]
    })
    df_ratings = df_ratings.sort_values('Current Elo', ascending=False)


    st.set_page_config(layout="wide", page_title="NBA Elo Ratings")
    st.title('Zulus leaderboard')
    st.header('Leaderboard and match history for Digimon locals at Zulu\'s Board Game Cafe')
    st.write('Just for fun, please don\'t take this too seriously')
    tab1, tab2 = st.tabs(["Leaderboard and Elo History", "Match History"])
    with tab1:
        st.header("Current Leaderboard")
        st.dataframe(df_ratings, use_container_width=True, hide_index=True)
        st.header("Elo Rating History")
        st.write("Elo history for all tracked local matches")
        # Add multiselect for teams
        focused_players = st.multiselect(
            "Select players to highlight:",
            options=sorted(players_list),
            help="You can select multiple players to compare their performance"
        )

        fig_line = elo_line_plot(elos, focused_players)
        st.plotly_chart(fig_line, use_container_width=True)

    with tab2:
        selected_player = st.selectbox("Select a player", players_list)

        if selected_player:
            # Filter all matches the player was involved in
            player_matches = match_df[
                (match_df['player1'] == selected_player) | (match_df['player2'] == selected_player)
                ].copy()

            # Generate a list of unique opponents based on selected player
            opponents = sorted(
                set(
                    player_matches['player2'][player_matches['player1'] == selected_player].tolist() +
                    player_matches['player1'][player_matches['player2'] == selected_player].tolist()
                )
            )

            selected_opponents = st.multiselect("Filter by opponent(s)", opponents)

            if selected_opponents:
                player_matches = player_matches[
                    ((player_matches['player1'] == selected_player) & (
                        player_matches['player2'].isin(selected_opponents))) |
                    ((player_matches['player2'] == selected_player) & (player_matches['player1'].isin(selected_opponents)))
                    ]


            # Format and display match results
            def format_match(row):
                if row['player1'] == selected_player:
                    opponent = row['player2']
                    player_deck = row['player1_deck']
                    opponent_deck = row['player2_deck']
                    result = "WIN" if row['player1_win'] else "LOSS"
                else:
                    opponent = row['player1']
                    player_deck = row['player2_deck']
                    opponent_deck = row['player1_deck']
                    result = "WIN" if not row['player1_win'] else "LOSS"

                date_str = str(row['tournament_date'])
                formatted_date = f"{date_str[4:6]}/{date_str[6:]}/{date_str[2:4]}"
                line = f"{formatted_date}:  {selected_player} ({player_deck}) vs {opponent} ({opponent_deck}) {result}"
                return line, result


            for _, row in player_matches.iterrows():
                match_str, result = format_match(row)
                color = "green" if result == "WIN" else "red"
                st.markdown(f"<span style='color: {color}; font-weight: bold;'>{match_str}</span>", unsafe_allow_html=True)
if __name__ == '__main__':
    main()
