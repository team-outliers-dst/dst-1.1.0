CREATE TABLE IF NOT EXISTS films (
    movie_id VARCHAR(64) PRIMARY KEY,
    movie_name VARCHAR(255) NOT NULL,
    language VARCHAR(32),
    genre VARCHAR(255),
    release_date DATE,
    runtime INT,
    cast_popularity DECIMAL(12,4),
    tmdb_rating DECIMAL(4,2),
    vote_count INT
);

CREATE TABLE IF NOT EXISTS trailer_stats (
    video_id VARCHAR(32) PRIMARY KEY,
    movie_id VARCHAR(64) NOT NULL,
    views BIGINT,
    likes BIGINT,
    comment_count BIGINT,
    published_at DATETIME,
    views_per_day DECIMAL(20,6),
    like_rate DECIMAL(20,8),
    comment_rate DECIMAL(20,8),
    CONSTRAINT fk_trailer_film FOREIGN KEY (movie_id) REFERENCES films(movie_id)
);

CREATE TABLE IF NOT EXISTS comments (
    comment_id VARCHAR(255) PRIMARY KEY,
    movie_id VARCHAR(64) NOT NULL,
    video_id VARCHAR(32),
    comment_text TEXT,
    sentiment VARCHAR(16),
    sentiment_score DECIMAL(8,6),
    topic VARCHAR(32),
    CONSTRAINT fk_comment_film FOREIGN KEY (movie_id) REFERENCES films(movie_id),
    CONSTRAINT fk_comment_trailer FOREIGN KEY (video_id) REFERENCES trailer_stats(video_id)
);
