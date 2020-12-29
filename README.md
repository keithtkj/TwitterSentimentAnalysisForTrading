# TwitterSentimentAnalysisForTrading


Natural Language Processing (NLP) is used to analyze the sentiment of tweets to predict movements in the financial markets. A trading strategy can be built around the sentiments of a stock and backtested with historical data to analyze its performance. With certain Python libraries, tweets about a particular stock are assigned a positive or negative score which suggests an increase or decrease in price. For example, Elon Musk tweeted about Tesla falling behind its production schedule in 2018 and the Tesla stock traded 6% lower the following day.


After creating a Twitter developer account, a unique consumer API key and access token is given. Twitter authenticates requests through unique consumer keys when data is requested. The Tweepy Python library is used to access data from the Twitter API.


In this example, the Apple stock, ‘$AAPL’, is used. To analyze the sentiments of Apple’s stock, we need to retrieve all the tweets that mention ‘$AAPL’ within a given time period.


The strategy includes removing bot-user accounts and their tweets from the data retrieved. Bots are created for purposes such as promoting products or spreading inaccurate news about a stock, causing irregularities in the strategy. The Botometer library uses a machine learning algorithm to compute a bot score and filters out tweets from bot accounts. To access the Botometer library, a unique API key is required which can obtained from https://rapidapi.com/OSoMe/api/botometer-pro.


A sentiment score of every tweet fetched is calculated with the Valence Aware Dictionary and sEntiment Reasoner (VADER) Python library. The words in a tweet are categorized into either ‘positive’, ‘negative’, or ‘neutral’. Depending on its intensity, a word is assigned a score. The compound score of a tweet is calculated by summing the scores of all words and normalizing the result to between 0 and +1.


The trading strategy involves taking a position (buy/sell) when the market opens and the trade is exited before the market closes on the same day. This position is determined by the sentiment of tweets fetched between the previous day’s market closing time and that day’s opening time as new information has not been factored into the stock price. For example, if the previous day’s closing time is 4pm and the next day’s opening time is 9am, and the sentiment of tweets surrounding AAPL stock between this time period is positive, the stock price is expected to increase and the strategy will long the stock.


The strategy is backtested with historical price data of AAPL’s stock exported into an excel sheet from Yahoo Finance, with the use of the panda_datareader library. 


Lastly, the performance of the strategy is analyzed by plotting its returns against market returns using the Matplotlib library.
