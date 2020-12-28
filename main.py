# Import libraries
import sys
import tweepy
import Botometer
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
sys.path.append('...') # replace '...' with your unique path

# Create a Twitter developer account to get a unique Twitter token
# Store this information in a dictionary:
twitter_token = {
        'consumer_key': "Copy your consumer key here",
        'consumer_secret': "Copy your consumer secret here here",
        'access_token': "Copy your access token here",
        'access_token_secret': "Copy your access token secret here",
    }
consumer_key = twitter_token['consumer_key']
consumer_secret = twitter_token['consumer_secret']

# Create authentication object
authen = tweepy.AppAuthHandler(consumer_key, consumer_secret)
# Create Twitter API object
twitter_api = tweepy.API(authen, wait_on_rate_limit=True)

# Fetch all tweets using Tweepy's Cursor method within a timeframe
# 180 days (3 months) is used in this example
from datetime import datetime, timedelta
start = (datetime.now()+timedelta(180)).strftime("%Y-%m-%d")
end = (datetime.now()).strftime("%Y-%m-%d")
cursor_results = tweepy.Cursor(twitter_api.search, q='$AAPL', since=start, until=end, count = 100)

# Extract information from tweets - to store them in a dataframe later
tweets_info = cursor_results.items()

# Store tweets' information in a dataframe
tweets_df = pd.DataFrame
for tweet in tweets_info:
    tweets_df = tweets_df.append(
                                    {
                                        'Tweet ID': tweet.id_str,
                                        'Created At': tweet.created_at,
                                        'User Screen Name': tweet.user.screen_name,
                                        'Tweet Text': tweet.text,
                                        'Retweet Count': tweet.retweet_count,
                                        'Favourite Count': tweet.favorite_count,
                                        'Language': tweet.lang,
                                    },
                                    ignore_index=True
    )

# Establish tweet ID as the index of the dataframe
tweets_df.index = tweets_df['Tweet ID']

# Export dataframe into an excel file
# Replace '...' with your unique path
tweets_df.to_excel(r'...\Tweets with AAPL.xlsx', header=True)

# Read the excel file
tweet_ids = pd.read_excel(r'...\Tweets with AAPL.xlsx')




################################# Remove bot accounts #########################################

# Returns list of tweet objects
def get_tweet_objects_from_id(tweet_id_list):
    tweet_list = []
    for i in range(0, len(tweet_id_list), 100):
        tweet_list = tweet_list + (twitter_api.statuses_lookup(tweet_id_list[i:(100 + i)], tweet_mode='extended'))

    return tweet_list

# Returns a dictionary of the required tweet information
def get_tweet_details_by_id(tweet_id_list):
    tweet_list = get_tweet_objects_from_id(tweet_id_list)
    tweets = pd.DataFrame()
    tweets['tweet_object'] = tweet_list
    tweets['tweet_text'] = tweets['tweet_object'].apply(tweet_list.full_text)
    tweets['tweet_username'] = tweets['tweet_object'].apply(tweet_list.user.screen_name)
    tweets['tweet_id'] = tweets['tweet_object'].apply(tweet_list.id_str)
    tweets['retweet_count'] = tweets['tweet_object'].apply(tweet_list.retweet_count)
    tweets['created_date'] = tweets['tweet_object'].apply(tweet_list.created_at)

    return tweets[["tweet_id", "created_date", "tweet_username", "tweet_text", "retweet_count"]]

# Get tweet details from tweet id
tweets = get_tweet_details_by_id(list(tweet_ids.tweet_id))

# Identify unique user accounts from the tweet details & store them into dataframe
unique_user_accounts = tweets['tweet_username'].unique()
users = pd.DataFrame()
users["tweet_username"] = unique_user_accounts

rapid_api_key = '........' # replace with your unique rapid API key
botometer = Botometer(mashape_key=rapid_api_key, **twitter_token, wait_on_ratelimit=True)

# Calculate scores of all unique users using Botometer
users['bot_score'] = users['tweet_username'].apply(lambda name: botometer.check_account(name)["raw_scores"]["english"]["overall"])
users['cap_score'] = users['tweet_username'].apply(lambda name: botometer.check_account(name)["cap"]["english"])

# Identity bots and indicate them on dataframe - if bot score > threshold value then it is a bot
users['is_bot'] = np.where(users['bot_score']>users['cap_score'],True,False)

# Merge the 2 dataframes: tweets and users, and delete tweets from bots
tweets = pd.merge(users, tweets)
tweets = tweets.loc[~(tweets.is_bot),:]




############################# Build The Strategy ########################################
from pandas.tseries.offsets import BDay

# Function that calculates market open time for tweets:
def get_market_open(date): # takes the datetime at which the tweet was made
    # Calculate market open time, if tweet was made on a weekend then subtract  BDay(0) to fetch the next business day's market open time
    curr_date_open = pd.to_datetime(date).floor('d').replace(hour=9, minute=30) - BDay(0)
    # Calculate market closing time, if tweet was made on a weekend then subtract  BDay(0) to fetch the next business day's market close time
    curr_date_close = pd.to_datetime(date).floor('d').replace(hour=16, minute=0) - BDay(0)
    # Calculate previous business day's market close time
    prev_date_close = (curr_date_open - BDay()).replace(hour=16, minute=0)
    # Calculate next business day's market open time for the tweet
    next_date_open = (curr_date_open + BDay()).replace(hour=9, minute=30)
    # If the tweet was made after the close of the previous business day but
    # on the next day before the market opens then the function assigns the curr_date_open as the opening time
    # when this tweet should be used to trade
    if (pd.to_datetime(date) >= prev_date_close) and (pd.to_datetime(date) < curr_date_open):
        return curr_date_open
    # If the tweet was made after the close of the current business day but
    # on the same day then the function assigns the next_date_open as the opening time
    # when this tweet should be used to trade
    elif (pd.to_datetime(date) >= curr_date_close) and (pd.to_datetime(date) < next_date_open):
        return next_date_open
    # If the tweet was made during the market trading hours then function returns nothing
    else:
        return None

# Apply the above function to get the market opening times when a tweet's sentiment should be used for each tweet
tweets["market_open_time"] = tweets["created_date"].apply(get_market_open)

# Remove tweets made during market hours
tweets = tweets.loc[~(tweets["market_open_time"].isna()),:]

# Create an object of SentimentIntensityAnalyzer class
analyzer = SentimentIntensityAnalyzer()

# Calculate sentiment (compound) scores of tweets and update the dataframe with the scores
tweets["compound_score"] = tweets["tweet_text"].apply(lambda t: analyzer.polarity_scores(t)['compound'])

# Count tweets with non-zero sentiment scores
daily_sentiments = tweets.loc[(tweets["compound_score"]!=0),:]

# Count all the unique tweets for a given day before the market opens
tweet_daily_count = daily_sentiments.groupby("market_open_time").market_open_time.agg('count').to_frame('total_unique_tweets')

# Count the total number of retweets for a given day before the market opens
retweet_daily_count = daily_sentiments.groupby("market_open_time").retweet_count.agg('sum').to_frame('total_retweets')

# Join the retweet count and the unique tweet count to the daily_sentiments dataframe
daily_sentiments.set_index("market_open_time", inplace = True)
daily_sentiments = daily_sentiments.join(tweet_daily_count, how='outer')
daily_sentiments = daily_sentiments.join(retweet_daily_count, how='outer')




#################### Export AAPL's Stock Data From Yahoo Finance Into Excel File ####################
import panda_datareader as web

# Start and end dates to fetch date - dates were established previously
start_date = start
end_date = end

# Fetch price data for AAPL stock within timeframe and exports into excel file in same folder as this script
df = web.DataReader("AAPL", 'yahoo', start_date, end_date)
df.to_excel("AAPL_prices.xlsx")


################## Organize Stock Price Data ##########################

# Fetch AAPL data from excel file
prices = pd.read_excel(r'...\AAPL_prices.xlsx')

# Set date as index
prices["Date"] = pd.to_datetime(prices["Date"]).dt.floor("d")
prices.set_index("Date", inplace = True)

# Calculate the percentage returns of the stock using the Open and Close prices
# As the strategy would buy at the opening of the market and sell at the market closing time
prices['return'] = (prices["Close"] - prices["Open"])/prices["Open"]

# Join the Daily Sentiment dataframe with this Prices dataframe
# Ensure that daily_sentiments has the same index and same date time format
daily_sentiments["date"] = pd.to_datetime(daily_sentiments["date"], format="%d-%m-%Y").dt.floor("d")
daily_sentiments.set_index("date", inplace=True)
prices = prices.join(daily_sentiments, how='outer')

# Drop the null values if any
prices.dropna(inplace=True)


########################### Generate Buy/Sell Signals #####################################

# Trading Strategy: Buy the stock whenever the sentiment before the market opening
# is more than the past 21-day average sentiment. Sell the stock when the sentiment
# before the market opening is less than the past 21-day average

# Create signal column that holds the buy/sell signals
prices['signal'] = 0

# Generate a buy signal when retweet_weighted_sentiment > its past 21 days mean
prices.loc[(prices['retweet_weighted_sentiment'] > prices['retweet_weighted_sentiment'].rolling(21).mean().shift(1)),'signal'] = 1
# Generate a sell signal when retweet_weighted_sentiment < its past 21 days mean
prices.loc[(prices['retweet_weighted_sentiment'] < prices['retweet_weighted_sentiment'].rolling(21).mean().shift(1)),'signal'] = -1



############################# Backtest The Strategy and Analyze Returns ######################

# Calculate strategy's returns
prices['strategy_return'] = prices['signal']*prices['return']

plt.figure(figsize=(15,7))

# Plot the strategy returns
plt.plot(((prices.strategy_return)+1).cumprod()*100)

# Plot the market returns for comparison
plt.plot(((prices['return'])+1).cumprod()*100)

# Label the graph
plt.legend(['Strategy Return','Market Return'],loc='upper left')
plt.xlabel('Date')
plt.ylabel('Percentage Return')