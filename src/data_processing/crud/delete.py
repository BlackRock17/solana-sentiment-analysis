from sqlalchemy.orm import Session
from src.data_processing.models.database import SolanaToken, Tweet, SentimentAnalysis, TokenMention
from datetime import datetime


def delete_solana_token(db: Session, token_id: int, check_mentions: bool = True) -> bool:
    """
    Delete a Solana token record

    Args:
        db: Database session
        token_id: The ID of the token to delete
        check_mentions: If True, will check if token has mentions and prevent deletion

    Returns:
        True if deletion was successful, False if token not found or has mentions
    """
    # Get the token by ID
    db_token = db.query(SolanaToken).filter(SolanaToken.id == token_id).first()

    # Return False if token doesn't exist
    if db_token is None:
        return False

    # Check if the token has mentions
    if check_mentions:
        mentions_count = db.query(TokenMention).filter(TokenMention.token_id == token_id).count()
        if mentions_count > 0:
            raise ValueError(
                f"Cannot delete token with ID {token_id} as it has {mentions_count} mentions. Remove mentions first or use cascade delete.")

    # Delete the token
    db.delete(db_token)
    db.commit()

    return True


def delete_tweet(db: Session, tweet_id: int, cascade: bool = True) -> bool:
    """
    Delete a tweet record

    Args:
        db: Database session
        tweet_id: The internal database ID of the tweet to delete
        cascade: If True, will also delete associated sentiment analysis and token mentions

    Returns:
        True if deletion was successful, False if tweet not found
    """
    # Get the tweet by ID
    db_tweet = db.query(Tweet).filter(Tweet.id == tweet_id).first()

    # Return False if tweet doesn't exist
    if db_tweet is None:
        return False

    # Handle cascade deletion
    if cascade:
        # Delete associated sentiment analysis
        db.query(SentimentAnalysis).filter(SentimentAnalysis.tweet_id == tweet_id).delete()

        # Delete associated token mentions
        db.query(TokenMention).filter(TokenMention.tweet_id == tweet_id).delete()
    else:
        # Check if tweet has associated records
        sentiment_count = db.query(SentimentAnalysis).filter(SentimentAnalysis.tweet_id == tweet_id).count()
        mentions_count = db.query(TokenMention).filter(TokenMention.tweet_id == tweet_id).count()

        if sentiment_count > 0 or mentions_count > 0:
            raise ValueError(
                f"Cannot delete tweet with ID {tweet_id} as it has {sentiment_count} sentiment analyses and {mentions_count} token mentions. Use cascade delete or remove associated records first.")

    # Delete the tweet
    db.delete(db_tweet)
    db.commit()

    return True


def delete_sentiment_analysis(db: Session, sentiment_id: int) -> bool:
    """
    Delete a sentiment analysis record

    Args:
        db: Database session
        sentiment_id: The ID of the sentiment analysis record to delete

    Returns:
        True if deletion was successful, False if record not found
    """
    # Get the sentiment analysis by ID
    db_sentiment = db.query(SentimentAnalysis).filter(SentimentAnalysis.id == sentiment_id).first()

    # Return False if record doesn't exist
    if db_sentiment is None:
        return False

    # Delete the sentiment analysis
    db.delete(db_sentiment)
    db.commit()

    return True


def delete_token_mention(db: Session, mention_id: int) -> bool:
    """
    Delete a token mention record

    Args:
        db: Database session
        mention_id: The ID of the token mention record to delete

    Returns:
        True if deletion was successful, False if record not found
    """
    # Get the token mention by ID
    db_mention = db.query(TokenMention).filter(TokenMention.id == mention_id).first()

    # Return False if record doesn't exist
    if db_mention is None:
        return False

    # Delete the token mention
    db.delete(db_mention)
    db.commit()

    return True


def delete_tweet_by_twitter_id(db: Session, twitter_id: str, cascade: bool = True) -> bool:
    """
    Delete a tweet record using its Twitter ID

    Args:
        db: Database session
        twitter_id: The original Twitter ID (not the database ID)
        cascade: If True, will also delete associated sentiment analysis and token mentions

    Returns:
        True if deletion was successful, False if tweet not found
    """
    # Get the tweet by Twitter ID
    db_tweet = db.query(Tweet).filter(Tweet.tweet_id == twitter_id).first()

    # Return False if tweet doesn't exist
    if db_tweet is None:
        return False

    # Call the existing delete function with the database ID
    return delete_tweet(db=db, tweet_id=db_tweet.id, cascade=cascade)


def delete_solana_token_by_address(db: Session, token_address: str, check_mentions: bool = True) -> bool:
    """
    Delete a Solana token record using its blockchain address

    Args:
        db: Database session
        token_address: The token's address on Solana blockchain
        check_mentions: If True, will check if token has mentions and prevent deletion

    Returns:
        True if deletion was successful, False if token not found or has mentions
    """
    # Get the token by address
    db_token = db.query(SolanaToken).filter(SolanaToken.token_address == token_address).first()

    # Return False if token doesn't exist
    if db_token is None:
        return False

    # Call the existing delete function with the database ID
    return delete_solana_token(db=db, token_id=db_token.id, check_mentions=check_mentions)


def delete_solana_token_cascade(db: Session, token_id: int) -> bool:
    """
    Delete a Solana token record along with all its mentions

    Args:
        db: Database session
        token_id: The ID of the token to delete

    Returns:
        True if deletion was successful, False if token not found
    """
    # Get the token by ID
    db_token = db.query(SolanaToken).filter(SolanaToken.id == token_id).first()

    # Return False if token doesn't exist
    if db_token is None:
        return False

    # Delete all mentions of this token
    db.query(TokenMention).filter(TokenMention.token_id == token_id).delete()

    # Delete the token
    db.delete(db_token)
    db.commit()

    return True
