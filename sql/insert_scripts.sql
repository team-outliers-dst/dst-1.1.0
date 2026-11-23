-- Populate this script only after export/integration has verified the source rows.
-- IDs and values should come from data/cleaned/movie_engagement.csv and
-- data/cleaned/analysed_comments.csv rather than being typed by hand.

INSERT INTO films (
    movie_id, movie_name, language, genre, release_date, runtime,
    cast_popularity, tmdb_rating, vote_count
) VALUES (
    'RD001', 'Dhurandhar', 'Hindi', 'Action, Crime, Thriller',
    '2025-12-05', 214, 2.662, 7.319, 393
) ON DUPLICATE KEY UPDATE movie_name=VALUES(movie_name);
