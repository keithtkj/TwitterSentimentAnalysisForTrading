"""Twitter-sentiment trading strategy for $AAPL.

Illustrative end-to-end pipeline: collect tweets (Tweepy), filter bot accounts
(Botometer), score sentiment (VADER), map each tweet to the trading window it
should influence, generate daily buy/sell signals from retweet-weighted
sentiment vs. its 21-day average, and backtest against Yahoo Finance prices.

Requires your own Twitter API credentials and a RapidAPI key for Botometer;
fill in the placeholders below before running.
"""

from datetime import datetime, timedelta

import tweepy
import Botometer
import numpy as np
import pandas as pd
import pandas_datareader as web
import matplotlib.pyplot as plt
from pandas.tseries.offsets import BDay
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


# --- Twitter API credentials (fill these in) ---
twitter_token = {
    'consumer_key': "Copy your consumer key here",
    'consumer_secret': "Copy your consumer secret here",
    'access_token': "Copy your access token here",
    'access_token_secret': "Copy your access token secret here",
}
consumer_key = twitter_token['consumer_key']
consumer_secret = twitter_token['consumer_secret']

# Authenticate and create the Twitter API client.
authen = tweepy.AppAuthHandler(consumer_key, consumer_secret)
twitter_api = tweepy.API(authen, wait_on_rate_limit=True)

# Fetch tweets over a time window (180 days in this example).
start = (datetime.now() + timedelta(180)).strftime("%Y-%m-%d")
end = (datetime.now()).strftime("%Y-%m-%d")
cursor_results = tweepy.Cursor(twitter_api.search, q='$AAPL', since=start, until=end, count=100)
tweets_info = cursor_results.items()

# Collect tweet fields into a dataframe.
tweets_df = pd.DataFrame()
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

# Use the tweet ID as the index, then round-trip through Excel.
tweets_df.index = tweets_df['Tweet ID']
tweets_df.to_excel(r'...\Tweets with AAPL.xlsx', header=True)
tweet_ids = pd.read_excel(r'...\Tweets with AAPL.xlsx')


################################# Remove bot accounts #########################################

def get_tweet_objects_from_id(tweet_id_list):
    """Look up full tweet objects in batches of 100 (API limit)."""
    tweet_list = []
    for i in range(0, len(tweet_id_list), 100):
        tweet_list = tweet_list + twitter_api.statuses_lookup(tweet_id_list[i:(100 + i)], tweet_mode='extended')
    return tweet_list


def get_tweet_details_by_id(tweet_id_list):
    """Return a dataframe of the tweet fields needed downstream."""
    tweet_list = get_tweet_objects_from_id(tweet_id_list)
    tweets = pd.DataFrame()
    tweets['tweet_object'] = tweet_list
    tweets['tweet_text'] = tweets['tweet_object'].apply(lambda t: t.full_text)
    tweets['tweet_username'] = tweets['tweet_object'].apply(lambda t: t.user.screen_name)
    tweets['tweet_id'] = tweets['tweet_object'].apply(lambda t: t.id_str)
    tweets['retweet_count'] = tweets['tweet_object'].apply(lambda t: t.retweet_count)
    tweets['created_date'] = tweets['tweet_object'].apply(lambda t: t.created_at)
    return tweets[["tweet_id", "created_date", "tweet_username", "tweet_text", "retweet_count"]]


tweets = get_tweet_details_by_id(list(tweet_ids.tweet_id))

# Score each unique account with Botometer and drop likely bots.
unique_user_accounts = tweets['tweet_username'].unique()
users = pd.DataFrame()
users["tweet_username"] = unique_user_accounts

rapid_api_key = '........'  # replace with your unique RapidAPI key
botometer = Botometer(mashape_key=rapid_api_key, **twitter_token, wait_on_ratelimit=True)

users['bot_score'] = users['tweet_username'].apply(lambda name: botometer.check_account(name)["raw_scores"]["english"]["overall"])
users['cap_score'] = users['tweet_username'].apply(lambda name: botometer.check_account(name)["cap"]["english"])
users['is_bot'] = np.where(users['bot_score'] > users['cap_score'], True, False)

tweets = pd.merge(users, tweets)
tweets = tweets.loc[~(tweets.is_bot), :]


############################# Build The Strategy ########################################

def get_market_open(date):
    """Map a tweet's timestamp to the market-open time whose session it should inform.

    A tweet posted between the previous close and the next open feeds that
    upcoming session; a tweet posted during trading hours is ignored (returns
    None) because its information is already reflected in the live price.
    """
    curr_date_open = pd.to_datetime(date).floor('d').replace(hour=9, minute=30) - BDay(0)
    curr_date_close = pd.to_datetime(date).floor('d').replace(hour=16, minute=0) - BDay(0)
    prev_date_close = (curr_date_open - BDay()).replace(hour=16, minute=0)
    next_date_open = (curr_date_open + BDay()).replace(hour=9, minute=30)

    if (pd.to_datetime(date) >= prev_date_close) and (pd.to_datetime(date) < curr_date_open):
        return curr_date_open
    elif (pd.to_datetime(date) >= curr_date_close) and (pd.to_datetime(date) < next_date_open):
        return next_date_open
    else:
        return None


# Assign each tweet to a trading window and drop tweets made during market hours.
tweets["market_open_time"] = tweets["created_date"].apply(get_market_open)
tweets = tweets.loc[~(tweets["market_open_time"].isna()), :]

# Score sentiment with VADER and keep tweets with a non-neutral score.
analyzer = SentimentIntensityAnalyzer()
tweets["compound_score"] = tweets["tweet_text"].apply(lambda t: analyzer.polarity_scores(t)['compound'])
daily_sentiments = tweets.loc[(tweets["compound_score"] != 0), :]

# Per-window tweet and retweet counts.
tweet_daily_count = daily_sentiments.groupby("market_open_time").market_open_time.agg('count').to_frame('total_unique_tweets')
retweet_daily_count = daily_sentiments.groupby("market_open_time").retweet_count.agg('sum').to_frame('total_retweets')

daily_sentiments.set_index("market_open_time", inplace=True)
daily_sentiments = daily_sentiments.join(tweet_daily_count, how='outer')
daily_sentiments = daily_sentiments.join(retweet_daily_count, how='outer')


#################### Export AAPL's Stock Data From Yahoo Finance ####################

start_date = start
end_date = end

# Fetch AAPL prices over the window and round-trip through Excel.
df = web.DataReader("AAPL", 'yahoo', start_date, end_date)
df.to_excel("AAPL_prices.xlsx")


################## Organize Stock Price Data ##########################

prices = pd.read_excel(r'...\AAPL_prices.xlsx')
prices["Date"] = pd.to_datetime(prices["Date"]).dt.floor("d")
prices.set_index("Date", inplace=True)

# Open-to-close return, since the strategy buys at open and sells at close.
prices['return'] = (prices["Close"] - prices["Open"]) / prices["Open"]

# Align the sentiment series with the price series on the trading date.
daily_sentiments["date"] = pd.to_datetime(daily_sentiments["date"], format="%d-%m-%Y").dt.floor("d")
daily_sentiments.set_index("date", inplace=True)
prices = prices.join(daily_sentiments, how='outer')
prices.dropna(inplace=True)


########################### Generate Buy/Sell Signals #####################################

# Buy when today's sentiment beats its trailing 21-day average, sell when below.
prices['signal'] = 0
prices.loc[(prices['retweet_weighted_sentiment'] > prices['retweet_weighted_sentiment'].rolling(21).mean().shift(1)), 'signal'] = 1
prices.loc[(prices['retweet_weighted_sentiment'] < prices['retweet_weighted_sentiment'].rolling(21).mean().shift(1)), 'signal'] = -1


############################# Backtest The Strategy and Analyze Returns ######################

prices['strategy_return'] = prices['signal'] * prices['return']

plt.figure(figsize=(15, 7))
plt.plot(((prices.strategy_return) + 1).cumprod() * 100)   # strategy
plt.plot(((prices['return']) + 1).cumprod() * 100)         # market benchmark
plt.legend(['Strategy Return', 'Market Return'], loc='upper left')
plt.xlabel('Date')
plt.ylabel('Percentage Return')
