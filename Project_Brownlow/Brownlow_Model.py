"""
Utilises pre-matched player data and game data to form predictions on the 2025 AFL Brownlow medal count.
"""
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix

# Loading DataFrame
df = pd.read_csv("C:/Users/tyler/Documents/AFL_Coding/Python_Brownlow_Disposals/2025_AFL_Coding/Master_AFL_Data.csv")

# --- FEATURE ENGINEERING ---
# Margin as relative score difference
def calculate_margin(row):
    if row["Team"] == row["HT_Code"]:
        return row["Home_Total"] - row["Away_Total"]
    elif row["Team"] == row["AT_Code"]:
        return row["Away_Total"] - row["Home_Total"]
    else:
        # If team info is missing or player not assigned properly
        return 0
max_score = df[["Home_Total", "Away_Total"]].max(axis=1).replace(0, 1)
df["Margin"] = df.apply(calculate_margin, axis=1) / max_score

# Past year Brownlow vote count
# First, group by player ID and season, and sum the votes
season_votes = df.groupby(["ID", "Year"])["Brownlow"].sum().reset_index()
season_votes.rename(columns={"Brownlow": "Season_Votes"}, inplace=True)
# Shift the season votes forward by 1 year per player
season_votes["Past_Votes"] = season_votes.groupby("ID")["Season_Votes"].shift(1)
# Merge back into the main DataFrame on player and year
df = df.merge(season_votes[["ID", "Year", "Past_Votes"]], on=["ID", "Year"], how="left")

# For 2023 year need to enter count manually so 2024 will have look back data same with 2017
votes_2023 = {
    "Lachie Neale": 31,
    "Marcus Bontempelli": 29,
    "Nick Daicos": 28,
    "Zak Butters": 27,
    "Errol Gulden": 27,
    "Christian Petracca": 26,
    "Jack Viney": 24,
    "Caleb Serong": 24,
    "Noah Anderson": 22,
    "Patrick Cripps": 22,
    "Jack Sinclair": 21,
    "Connor Rozee": 21,
    "Toby Greene": 20,
    "Jordan Dawson": 20,
    "Rory Laird": 20,
    "Tim Taranto": 19,
    "Jai Newcombe": 18,
    "Brad Crouch": 18,
    "Charlie Curnow": 17,
    "Zach Merrett": 17,
    "Tom Liberatore": 17,
    "Taylor Walker": 16,
    "Jason Horne-Francis": 16,
    "Tom Green": 16,
    "Chad Warner": 16,
    "Darcy Parish": 15,
    "Jack Steele": 15,
    "Shai Bolton": 14,
    "Luke Davies-Uniacke": 13,
    "Jeremy Cameron": 13,
    "Tom Mitchell": 12,
    "James Sicily": 12,
    "Matt Rowell": 12,
    "Patrick Dangerfield": 12,
    "Joe Daniher": 12,
    "Tim English": 11,
    "James Worpel": 11,
    "Tim Kelly": 11,
    "Nic Martin": 10,
    "Will Ashcroft": 10,
    "Stephen Coniglio": 10,
    "Luke Parker": 10,
    "Andrew Brayshaw": 10,
    "Harris Andrews": 8,
    "Jordan de Goey": 8,
    "Dustin Martin": 8,
    "Will Day": 8,
    "Charlie Cameron": 8,
    "Jack Lukosius": 8,
    "Josh Daicos": 8,
    "Josh Kelly": 8,
    "Dan Houston": 7,
    "Tom Hawkins": 7,
    "Izak Rankine": 7,
    "Nick Larkey": 7,
    "Max Gawn": 7,
    "Ben King": 7,
    "Sam Docherty": 7,
    "Dom Sheed": 6,
    "Lachie Schultz": 6,
    "Tom Stewart": 6,
    "Jacob Weitering": 6,
    "Dion Prestia": 6,
    "Jeremy Finlayson": 6,
    "Clayton Oliver": 6,
    "Noah Balta": 6,
    "Luke Ryan": 6,
    "Luke Jackson": 6,
    "Scott Pendlebury": 6,
    "Tarryn Thomas": 5,
    "Jamie Elliott": 5,
    "Max King": 5,
    "Taylor Adams": 5,
    "Brody Mihocek": 5,
    "Sam Walsh": 5,
    "Zac Bailey": 5,
    "Nick Blakey": 5,
    "Jamarra Ugle-Hagan": 5,
    "Hayden Young": 5,
    "George Hewett": 5,
    "Daniel Rioli": 5,
    "Lachie Whitfield": 5,
    "Angus Brayshaw": 4,
    "Bailey Scott": 4,
    "Bailey Smith": 4,
    "Josh Dunkley": 4,
    "Tom Papley": 4,
    "Joel Amartey": 4,
    "Nasiah Wanganeen-Milera": 4,
    "Adam Treloar": 4,
    "Bayley Fritsch": 4,
    "Jamie Cripps": 3,
    "Jesse Hogan": 3,
    "Hugh McCluggage": 3,
    "Nic Newman": 3,
    "Touk Miller": 3,
    "Alex Pearce": 3,
    "Sam Taylor": 3,
    "Steven May": 3,
    "Jack Gunston": 3,
    "Liam Henry": 3,
    "Mason Cox": 3,
    "Brad Close": 3,
    "Andrew Phillips": 3,
    "Jamaine Jones": 3,
    "Adam Saad": 3,
    "Callum Mills": 3,
    "Lachie Hunter": 3,
    "Blake Acres": 3,
    "Aliir Aliir": 3,
    "Callan Ward": 3,
    "Bailey Dale": 3,
    "Reilly OBrien": 3,
    "Darcy Fogarty": 3,
    "Jake Stringer": 3,
    "Liam Baker": 3,
    "Jack Higgins": 3,
    "Kyle Langford": 3,
    "Steele Sidebottom": 3,
    "Charlie Dixon": 3,
    "Darcy Moore": 3,
    "Keidean Coleman": 3,
    "Rowan Marshall": 3,
    "Mark Blicavs": 3,
    "Harry Sheezel": 3,
    "Jack Crisp": 2,
    "Jake Melksham": 2,
    "Gryan Miers": 2,
    "Harry Petty": 2,
    "Jack Silvagni": 2,
    "Tyson Stengle": 2,
    "Isaac Quaynor": 2,
    "Luke Shuey": 2,
    "Brayden Fiorini": 2,
    "Isaac Heeney": 2,
    "Cody Weightman": 2,
    "Trent Cotchin": 2,
    "Jake Riccardi": 2,
    "Peter Wright": 2,
    "Cameron Zurhaar": 2,
    "Caleb Daniel": 2,
    "Ben Keays": 2,
    "Jack Ziebell": 2,
    "Kade Chandler": 2,
    "Aaron Naughton": 2,
    "Jacob van Rooyen": 2,
    "Cam Rayner": 2,
    "Sean Darcy": 2,
    "Mitch Duncan": 2,
    "Callum Wilkie": 2,
    "Riley Thilthorpe": 2,
    "Sam Frost": 2,
    "Jake Waterman": 2,
    "Andrew McGrath": 2,
    "Kysaiah Pickett": 2,
    "Karl Amon": 2,
    "Oliver Henry": 2,
    "Adam Cerra": 2,
    "Sam Powell-Pepper": 2,
    "George Wardlaw": 2,
    "Rory Sloane": 2,
    "Jye Caldwell": 2,
    "Harry McKay": 2,
    "Lachie Weller": 2,
    "Rory Lobb": 1,
    "Will Phillips": 1,
    "Jack Ginnivan": 1,
    "Will Hayward": 1,
    "Jarrod Berry": 1,
    "Hayden McLean": 1,
    "Bailey Williams": 1,
    "Luke Breust": 1,
    "Tom Atkins": 1,
    "Jack Martin": 1,
    "Sam Flanders": 1,
    "John Noble": 1,
    "Eric Hipwood": 1,
    "Gary Rohan": 1,
    "Christian Salem": 1,
    "Mitch Lewis": 1,
    "Todd Marshall": 1,
    "Mason Redman": 1,
    "Connor Idun": 1,
    "Dylan Moore": 1,
    "Josh Weddle": 1,
    "Jaeger OMeara": 1,
    "Brodie Smith": 1,
    "Nathan Broad": 1,
    "Max Holmes": 1,
    "Jake Soligo": 1,
    "Jacob Hopper": 1,
    "Mattaes Phillipou": 1,
    "Daniel Rich": 1,
    "Sam Switkowski": 1,
    "Mason Wood": 1,
    "Nathan Murphy": 1,
    "Logan McDonald": 1,
    "Jordan Ridley": 1,
    "Ben Brown": 1,
    "Dane Rampe": 1
}
votes_2017 = {
 'Dustin Martin': 36,
 'Patrick Dangerfield': 33,
 'Tom Mitchell': 25,
 'Josh Kennedy': 13,  # appears twice, latest entry overwrites earlier
 'Lance Franklin': 22,
 'Josh Kelly': 21,
 'Rory Sloane': 20,
 'Marcus Bontempelli': 19,
 'Ollie Wines': 18,
 'Dayne Beams': 17,
 'Luke Parker': 16,
 'Scott Pendlebury': 15,
 'Nat Fyfe': 15,
 'Zach Merrett': 15,
 'Brad Ebert': 15,
 'Lachie Neale': 14,
 'Dayne Zorko': 14,
 'Gary Ablett': 14,
 'Dyson Heppell': 14,
 'Ben Brown': 14,
 'Sebastian Ross': 14,
 'Steele Sidebottom': 14,
 'Taylor Adams': 14,
 'Joel Selwood': 13,
 'Robbie Gray': 12,
 'Clayton Oliver': 12,
 'Jack Steven': 11,
 'Jack Billings': 11,
 'Bryce Gibbs': 11,
 'Adam Treloar': 11,
 'Matt Crouch': 11,
 'David Zaharakis': 11,
 'Dylan Shiel': 11,
 'Callan Ward': 11,
 'Ben Cunnington': 11,
 'Mitch Duncan': 11,
 'Luke Shuey': 10,
 'Michael Walters': 10,
 'Sam Jacobs': 10,
 'Travis Boak': 10,
 'Rory Atkins': 10,
 'Aaron Hall': 10,
 'Jack Viney': 9,
 'Andrew Gaff': 9,
 'Tom McDonald': 9,
 'Rory Laird': 9,
 'Joe Daniher': 9,
 'Shaun Higgins': 9,
 'Marc Murphy': 9,
 'Toby Greene': 8,
 'Kade Simpson': 8,
 'Charlie Dixon': 8,
 'Jack Macrae': 8,
 'Trent Cotchin': 8,
 'Alex Rance': 8,
 'Michael Hibberd': 7,
 'Shannon Hurn': 7,
 'Shaun Grigg': 7,
 'Orazio Fantasia': 7,
 'Nathan Jones': 7,
 'Jason Johannisen': 7,
 'Taylor Walker': 7,
 'Tom Lynch': 4,  # appears twice, latest entry kept
 'Sam Mitchell': 7,
 'Jarryd Roughead': 6,
 'Jarryd Lyons': 6,
 'Sam Menegola': 6,
 'Jack Gunston': 6,
 'Jack Riewoldt': 6,
 'Luke Dahlhaus': 6,
 'Dan Hannebery': 6,
 'Paddy Ryder': 6,
 'Zac Williams': 6,
 'Jonathon Patton': 6,
 'Stefan Martin': 6,
 'Jordan de Goey': 5,
 'Liam Jones': 5,
 'Shaun Burgoyne': 5,
 'Patrick Cripps': 5,
 'Ben McEvoy': 5,
 'Eddie Betts': 5,
 'Matthew Kreuzer': 5,
 'Lachie Whitfield': 5,
 'Sam Docherty': 5,
 'Dylan Roberton': 5,
 'David Mundy': 5,
 'Dion Prestia': 5,
 'Liam Shiels': 5,
 'Jeremy Cameron': 5,
 'Connor Blakely': 5,
 'Cameron Pedersen': 4,
 'Chad Wingard': 4,
 'Michael Hurley': 4,
 'Cale Hooker': 4,
 'Isaac Heeney': 4,
 'Elliot Yeo': 4,
 'Nick Riewoldt': 4,
 'Will Hoskin-Elliott': 4,
 'James Kelly': 4,
 'Jared Polec': 4,
 'Harry Taylor': 4,
 'Bradley Hill': 4,
 'Daniel Rich': 4,
 'Sam Gray': 3,
 'Jesse Hogan': 3,
 'Josh Caddy': 3,
 'Jack Steele': 3,
 'Daniel Wells': 3,
 'Tom Hawkins': 3,
 'Callum Sinclair': 3,
 'Liam Picken': 3,
 'Gary Rohan': 3,
 'Ricky Henderson': 3,
 'Jake Stringer': 3,
 'Sam Petrevski-Seton': 3,
 'Jarrad Waite': 3,
 'Steven Motlop': 3,
 'Christian Salem': 3,
 'Stephen Coniglio': 3,
 'Brad Crouch': 3,
 'Matt Priddis': 3,
 'Ben Reid': 3,
 'Jeremy McGovern': 3,
 'Tom Scully': 3,
 'Brandon Matera': 3,
 'Leigh Montagna': 3,
 'Dom Tyson': 3,
 'Sam Reid': 3,
 'Max Gawn': 3,
 'Tom Bellchambers': 2,
 'Isaac Smith': 2,
 'Tom Rockliff': 2,
 'Luke Ryan': 2,
 'Jordan Murdoch': 2,
 'Lachie Hunter': 2,
 'Liam Duggan': 2,
 'Tim Membrey': 2,
 'Josh Jenkins': 2,
 'Eric Hipwood': 2,
 'Kane Lambert': 2,
 'Jack Darling': 2,
 'Jarrod Harbrow': 2,
 'Jake Lloyd': 2,
 'Christian Petracca': 2,
 'Steven May': 2,
 'Pearce Hanley': 2,
 'Jeff Garlett': 2,
 'Zak Jones': 2,
 'Michael Barlow': 2,
 'Jordan Lewis': 2,
 'Toby Nankervis': 2,
 'Shane Mumford': 2,
 'Dane Rampe': 2,
 'Heath Grundy': 2,
 'Dom Sheed': 2,
 'Jack Newnes': 2,
 'Ryan Burton': 2,
 'Zach Tuohy': 2,
 'Brodie Grundy': 2,
 'Darcy Byrne-Jones': 1,
 'Jamie Elliott': 1,
 'Jaeger OMeara': 1,
 'Luke Dunstan': 1,
 'Jacob Townsend': 1,
 'Brodie Smith': 1,
 'James Sicily': 1,
 'Jack Ziebell': 1,
 'Shane Biggs': 1,
 'Zac Smith': 1,
 'Jake Carlisle': 1,
 'Ryan Lester': 1,
 'Jake Lever': 1,
 'Mark Blicavs': 1,
 'Oscar McDonald': 1,
 'Sam Gibson': 1,
 'Conor McKenna': 1,
 'Lewis Taylor': 1,
 'Bachar Houli': 1,
 'Scott Selwood': 1,
 'Brandon Ellis': 1,
 'Andy Otten': 1,
 'Tom Jonas': 1,
 'Jarrod Witts': 1,
 'Mason Wood': 1,
 'Jasper Pittard': 1,
 'Matthew Wright': 1,
 'Caleb Daniel': 1,
 'Aaron Sandilands': 1,
 'Toby McLean': 1,
 'Jamie Cripps': 1,
 'Sam Rowe': 1,
 'Stephen Hill': 1,
 'Jack Watts': 1,
 'Sam Powell-Pepper': 1,
 'Richard Douglas': 1,
 'Adam Saad': 1
}

# For 2024 entries with missing past votes (i.e., 2023), fill using dict
df["Player_Title"] = df["Player"].str.title()
df.loc[df["Year"] == 2024, "Past_Votes"] = df.loc[df["Year"] == 2024, "Player_Title"].map(votes_2023)
df.loc[df["Year"] == 2018, "Past_Votes"] = df.loc[df["Year"] == 2018, "Player_Title"].map(votes_2017)

# Fill missing values with 0
df["Past_Votes"] = df["Past_Votes"].fillna(0).astype(int)

# Normalize disposals by % time played
df["Disposals"] = df["Kicks"] + df["Hand Balls"]
df["Disposals_per_Time"] = df["Disposals"] / df["% Time Played"].replace(0, 1)  # avoid div by zero
# Goals * Clearances — impact midfielders
df["Goals_Clearances"] = df["Goals"] * df["Clearances"]
# Contested Possessions * Tackles — contested, defensive effort
df["Contested_Tackles"] = df["Contested Possessions"] * df["Tackles"]
# Clangers * Frees Against — error indicator
df["Clangers_FreesAgainst"] = df["Clangers"] * df["Frees Against"]
# Marks Inside 50 * Contested Marks — aerial dominance near goals
df["MarksI50_ContestedMarks"] = df["Marks Inside 50"] * df["Contested Marks"]
# Goal Assists * Inside 50s — offensive setup
df["GoalAssists_Inside50"] = df["Goal Assists"] * df["Inside 50"]
# Clearances / Contested Possessions — clearance efficiency
df["Clearance_Efficiency"] = df["Clearances"] / df["Contested Possessions"].replace(0, 1)
# Tackles / Clangers — defensive reliability
df["Tackles_Clangers_Ratio"] = df["Tackles"] / df["Clangers"].replace(0, 1)
# Score Involvement = Goals + Goal Assists
df["Score_Involvement"] = df["Goals"] + df["Goal Assists"]
# Margin * Past Votes — effect of star players in big wins
df["Margin_PastVotes"] = df["Margin"] * df["Past_Votes"]
# Rebounds * One Percenters — defensive effort and transition
df["Rebounds_OnePercenters"] = df["Rebounds"] * df["One Percenters"]

# Exporting Dataframe with feature engineering
df.to_csv("C:/Users/tyler/Documents/AFL_Coding/Python_Brownlow_Disposals/2025_AFL_Coding/AFL_Data_Feature_Eng.csv")

# --- CLEANING DATA ---
# Define feature columns (make sure these exist and are numeric)
feature_cols = [
    "Kicks", "Hand Balls", "Marks", "Goals", "Behinds", "Hit Outs",
    "Tackles", "Rebounds", "Inside 50", "Clearances", "Clangers",
    "Frees For", "Frees Against", "Contested Possessions",
    "Uncontested Possessions", "Contested Marks", "Marks Inside 50",
    "One Percenters", "Bounces", "Goal Assists", "% Time Played",
    "Margin", "Past_Votes", "Disposals_per_Time", "Goals_Clearances", 
    "Contested_Tackles", "Clangers_FreesAgainst", "MarksI50_ContestedMarks", 
    "GoalAssists_Inside50", "Clearance_Efficiency", "Tackles_Clangers_Ratio", 
    "Score_Involvement", "Margin_PastVotes", "Rebounds_OnePercenters"
]
# Drop any rows with missing feature values
df_model = df.dropna(subset=feature_cols + ["Brownlow"])
# Filter 2025 prediction data
predict_df = df[df["Year"] == 2025].copy()
# Use only past years for training
train_df = df[df["Year"] < 2025].copy()
# Create binary target for train data (1 if any votes, else 0)
train_df["Brownlow_binary"] = (train_df["Brownlow"] > 0).astype(int)
# Final train set
X = train_df[feature_cols]
y = train_df["Brownlow_binary"]
print("Class distribution:\n", y.value_counts(normalize=True))

# --- TRAIN/TEST SPLIT ---
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# HERE COMMENT FOR FITTING MODEL
# # Convert to DMatrix for XGBoost (optional, but can use sklearn API for GridSearchCV)
# # For GridSearchCV, it's easier to use XGBClassifier directly (sklearn wrapper)
# from xgboost import XGBClassifier
# from sklearn.model_selection import GridSearchCV

# # Define model for GridSearchCV
# xgb_clf = XGBClassifier(
#     objective='binary:logistic',
#     use_label_encoder=False,
#     eval_metric='logloss',
#     scale_pos_weight=(y_train == 0).sum() / (y_train == 1).sum(),
#     random_state=42
# )

# # Define hyperparameter grid
# param_grid = {
#     'max_depth': [7, 9],                # Two values around current 9
#     'learning_rate': [0.02, 0.03],     # Narrow range close to current
#     'n_estimators': [300, 400],        # Two options for boosting rounds
#     'subsample': [0.7, 0.8],           # Slight variation from current 0.7
#     'colsample_bytree': [0.7, 0.8],    # Same here
#     'scale_pos_weight': [10, 12],      # Just two values around current 10
#     'gamma': [1, 5],                   # Two values to try moderate regularization
# }

# # Run GridSearchCV
# grid_search = GridSearchCV(
#     estimator=xgb_clf,
#     param_grid=param_grid,
#     scoring='f1',
#     cv=3,
#     verbose=2,
#     n_jobs=-1
# )

# grid_search.fit(X_train, y_train)

# print("Best parameters found: ", grid_search.best_params_)

# # Use best estimator for prediction
# best_model = grid_search.best_estimator_

# # Predict and evaluate on test set
# y_pred = best_model.predict(X_test)
# print("\nClassification Report:")
# print(classification_report(y_test, y_pred))
# print("Confusion Matrix:")
# print(confusion_matrix(y_test, y_pred))

# HERE UNCOMMENT

# --- TRAINING ---
# Convert to DMatrix
dtrain = xgb.DMatrix(X_train, label=y_train)
dtest = xgb.DMatrix(X_test, label=y_test)

# Optimised parameters for classification
params = {
    "objective": "binary:logistic",
    "eval_metric": "logloss",
    "scale_pos_weight": 10,
    "seed": 42,
    "eta": 0.03,
    "max_depth": 9,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "gamma": 1,
    "verbosity": 1
}

# Train with early stopping on test set
evallist = [(dtrain, 'train'), (dtest, 'eval')]
num_round = 100
bst = xgb.train(params, dtrain, num_round, evallist, early_stopping_rounds=10, verbose_eval=10)

# --- EFFECTIVENESS ---
# Predict probabilities on test set
probs = bst.predict(dtest)

# Evauate threshold 0.7
y_pred_07 = (probs >= 0.7).astype(int)
print("\nClassification Report at threshold 0.7:")
print(classification_report(y_test, y_pred_07))
print("Confusion Matrix at threshold 0.7:")
print(confusion_matrix(y_test, y_pred_07))

# Evaluate threshold 0.5
y_pred_05 = (probs >= 0.5).astype(int)
print("\nClassification Report at threshold 0.5:")
print(classification_report(y_test, y_pred_05))
print("Confusion Matrix at threshold 0.5:")
print(confusion_matrix(y_test, y_pred_05))

# Evaluate threshold 0.3
y_pred_03 = (probs >= 0.3).astype(int)
print("\nClassification Report at threshold 0.3:")
print(classification_report(y_test, y_pred_03))
print("Confusion Matrix at threshold 0.3:")
print(confusion_matrix(y_test, y_pred_03))

# --- TOP PREDICTIONS FOR VOTE GETTERS ---
# High-confidence predictions (prob > 0.8)
high_conf_idx = probs > 0.8
high_conf_players = X_test.loc[high_conf_idx].copy()
high_conf_players["Prob_Vote"] = probs[high_conf_idx]

print("\nTop high-confidence predicted vote-getters:")
print(high_conf_players.sort_values("Prob_Vote", ascending=False).head(10))

######################
# Exporting Results
######################
# --- PREDICTIONS ON 2025 AFL DATA ---
dpredict = xgb.DMatrix(predict_df[feature_cols])
predict_df["vote_probability"] = bst.predict(dpredict)
# Show top predicted vote-getters for 2025
top_preds = predict_df.sort_values("vote_probability", ascending=False)
top_preds["Adjusted_Round"] = top_preds["Round"] - 1 # So opening round is round 0
print("\nTop 2025 predicted vote-getters:")
print(top_preds[["Player", "vote_probability", "Team", "Adjusted_Round"]].head(10))
predict_df.to_csv("C:/Users/tyler/Documents/AFL_Coding/Python_Brownlow_Disposals/2025_AFL_Coding/Output/2025_AFL_Data_with_Probabilities.csv", index=False)
# top_preds[["Player", "vote_probability", "Team", "Adjusted_Round"]].to_csv("C:/Users/tyler/Documents/AFL_Coding/Python_Brownlow_Disposals/2025_AFL_Coding/Output/Best_Predictions.csv", index=False)

# --- PROBABILITY OF SCORING ANY VOTE HEAT MAP ---
# Assuming predict_df has columns: Player, Team, Round, vote_probability
predict_df["Adjusted_Round"] = predict_df["Round"] - 1 # So opening round is round 0
# Create pivot table: index = Player and Team, columns = Adjusted_Round, values = vote_probability
pivot_df = predict_df.pivot_table(
    index=["Player", "Team"],
    columns="Adjusted_Round",
    values="vote_probability",
    fill_value=0)
# Rename columns to "Round 0", "Round 1", ...
pivot_df.columns = [f"Round {int(col)}" for col in pivot_df.columns]
# Sum across rounds for sorting by total predicted votes
pivot_df["Total_Predicted_Votes"] = pivot_df.sum(axis=1)
# Sort descending by total predicted votes
pivot_df = pivot_df.sort_values(by="Total_Predicted_Votes", ascending=False)
# Drop the total votes column if you don't want it in final output
# Or keep it for reference
pivot_df = pivot_df.drop(columns=["Total_Predicted_Votes"])
# Export to CSV
pivot_df.to_csv("C:/Users/tyler/Documents/AFL_Coding/Python_Brownlow_Disposals/2025_AFL_Coding/Output/2025_Brownlow_Heatmap_Probability.csv")
# To display the top 10 players in this format
print(pivot_df.head(10))

# --- ASSIGNING 3-2-1 VOTES FOR EACH ROUND ---
# Sort by Game ID and vote_probability
predict_df = predict_df.sort_values(["Game ID", "vote_probability"], ascending=[True, False])
# Assign 3-2-1 votes
predict_df["votes"] = predict_df.groupby("Game ID").cumcount().map({0: 3, 1: 2, 2: 1}).fillna(0)
# Pivot table
pivot_votes = predict_df.pivot_table(
    index=["Player", "Team"],
    columns="Adjusted_Round",
    values="votes",
    aggfunc="sum",
    fill_value=0
)
pivot_votes.columns = [f"Round {int(col)}" for col in pivot_votes.columns]
# Add total votes column
pivot_votes["Total Votes"] = pivot_votes.sum(axis=1)
# Sort by total votes descending
pivot_votes = pivot_votes.sort_values(by="Total Votes", ascending=False)
pivot_votes.to_csv("C:/Users/tyler/Documents/AFL_Coding/Python_Brownlow_Disposals/2025_AFL_Coding/Output/2025_Brownlow_Heatmap_Votes.csv")