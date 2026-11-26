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

SELECT f.movie_name, f.language, t.views_per_day, COUNT(c.comment_id) AS total_comments, 
SUM(CASE WHEN c.sentiment = 'positive' THEN 1 ELSE 0 END) AS positive_comments, ROUND(100.0 * SUM(CASE WHEN c.sentiment = 'positive' THEN 1 ELSE 0 END)/ COUNT(c.comment_id),2) AS positive_pct
FROM films f
JOIN trailer_stats t ON t.movie_id = f.movie_id
JOIN comments      c ON c.movie_id = f.movie_id
GROUP BY f.movie_name, f.language, t.views_per_day
HAVING positive_pct > (SELECT 100.0 * SUM(CASE WHEN sentiment = 'positive' THEN 1 ELSE 0 END)/ COUNT(*)FROM comments)
ORDER BY positive_pct DESC;
