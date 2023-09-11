import tweepy

def format_tweet():
def post_tweet(config_data, detector_data, call_data, mp3_url):
    client = tweepy.Client(consumer_key=config_data["twitter_settings"]["consumer_key"],
                           consumer_secret=config_data["twitter_settings"]["consumer_secret"],
                           access_token=config_data["twitter_settings"]["access_token"],
                           access_token_secret=config_data["twitter_settings"]["access_token_secret"])
    try:
        tweet_response = client.create_tweet(text=tweet_text)
        return tweet_response.data
    except tweepy.TweepyException as e:
        print(f"Error posting tweet: {e}")
        return None
