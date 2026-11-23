# Release Day Radar ER Diagram

```mermaid
erDiagram
    FILMS ||--o{ TRAILER_STATS : has
    FILMS ||--o{ COMMENTS : receives
    FILMS {
        varchar movie_id PK
        varchar movie_name
        varchar language
        varchar genre
        date release_date
        int runtime
        decimal cast_popularity
        decimal tmdb_rating
        int vote_count
    }
    TRAILER_STATS {
        varchar video_id PK
        varchar movie_id FK
        bigint views
        bigint likes
        bigint comment_count
        datetime published_at
        decimal views_per_day
        decimal like_rate
        decimal comment_rate
    }
    COMMENTS {
        varchar comment_id PK
        varchar movie_id FK
        varchar video_id
        text comment_text
        varchar sentiment
        decimal sentiment_score
        varchar topic
    }
```
