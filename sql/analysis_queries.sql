SELECT * FROM films;

SELECT f.genre, AVG(t.views_per_day) AS average_views_per_day
FROM films f JOIN trailer_stats t ON t.movie_id = f.movie_id
GROUP BY f.genre;

SELECT f.language, AVG(t.views_per_day) AS average_views_per_day
FROM films f JOIN trailer_stats t ON t.movie_id = f.movie_id
GROUP BY f.language;

SELECT f.movie_name, f.cast_popularity, t.views_per_day
FROM films f JOIN trailer_stats t ON t.movie_id = f.movie_id
ORDER BY f.cast_popularity DESC;

SELECT f.movie_name, c.sentiment, COUNT(*) AS comment_count
FROM films f JOIN comments c ON c.movie_id = f.movie_id
GROUP BY f.movie_name, c.sentiment;
