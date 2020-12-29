# Twitter Sentiment Analysis for Trading

An **NLP-driven algorithmic trading strategy** that mines Twitter sentiment about
a stock, converts it into daily buy/sell signals, and backtests the resulting
strategy against the market. Built in **Python** and demonstrated on Apple
(`$AAPL`).

The premise: news and opinion move markets before prices fully adjust. By
measuring the sentiment of tweets posted *between* one day's market close and the
next day's open, the strategy takes an intraday position in the direction the
crowd is leaning — then exits before the close.

## Pipeline

1. **Data collection** — pull tweets mentioning `$AAPL` via the Twitter API
   (**Tweepy**).
2. **Bot filtering** — score each account with **Botometer** and drop tweets
   from likely bots, which distort sentiment by pushing promotional or
   misleading content.
3. **Sentiment scoring** — score each tweet with **VADER**, a lexicon-based
   sentiment analyzer tuned for social-media text, producing a normalized
   compound score.
4. **Signal construction** — map each tweet to the correct trading window
   (respecting weekends and market hours), aggregate a retweet-weighted daily
   sentiment, and generate a **buy** signal when sentiment exceeds its trailing
   21-day average and a **sell** signal when it falls below.
5. **Backtest & evaluation** — join sentiment with historical `$AAPL` prices
   from Yahoo Finance, compute strategy returns from open-to-close moves, and
   plot cumulative **strategy return vs. market return** with Matplotlib.

## Stack

`tweepy` · `vaderSentiment` · `Botometer` · `pandas` · `numpy` ·
`pandas-datareader` (Yahoo Finance) · `matplotlib`

## Running it

```bash
pip install tweepy vaderSentiment botometer pandas numpy pandas-datareader matplotlib
python main.py
```

You'll need your own **Twitter API** credentials (consumer key/secret + access
token) and a **RapidAPI** key for Botometer; add them where indicated in
`main.py`.

## What it demonstrates

Combining natural-language processing with quantitative finance — API data
collection, bot detection, lexicon-based sentiment analysis, market-hours
signal timing, and backtesting a strategy against a benchmark.

> Personal project exploring the link between social-media sentiment and
> short-term price movement. Educational only — not financial advice.
