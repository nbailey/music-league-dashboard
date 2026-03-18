-- Music League Stats — Analytics Views
-- All views auto-update as data changes. No materialization needed at this scale.

-- ============================================================
-- RAW AFFINITY: total points from voter -> submitter per league
-- ============================================================
CREATE VIEW IF NOT EXISTS v_voter_submitter_affinity AS
SELECT
    v.league_id,
    l.league_name,
    v.voting_user_id,
    voter.user_name AS voter_name,
    v.submission_user_id,
    submitter.user_name AS submitter_name,
    SUM(v.points) AS total_points_given,
    COUNT(*) AS rounds_voted,
    ROUND(AVG(v.points), 2) AS avg_points_given
FROM votes v
JOIN users voter ON v.voting_user_id = voter.user_id
JOIN users submitter ON v.submission_user_id = submitter.user_id
JOIN leagues l ON v.league_id = l.league_id
WHERE v.voting_user_id != v.submission_user_id
GROUP BY v.league_id, v.voting_user_id, v.submission_user_id;

-- ============================================================
-- VOTER BASELINE: each voter's average points per submission per round
-- This is the denominator for adjusted affinity.
-- ============================================================
CREATE VIEW IF NOT EXISTS v_voter_baseline AS
SELECT
    v.league_id,
    v.voting_user_id,
    voter.user_name AS voter_name,
    v.round_id,
    SUM(v.points) AS total_points_in_round,
    COUNT(*) AS submissions_voted_on,
    ROUND(CAST(SUM(v.points) AS REAL) / COUNT(*), 2) AS avg_points_per_submission
FROM votes v
JOIN users voter ON v.voting_user_id = voter.user_id
WHERE v.voting_user_id != v.submission_user_id
GROUP BY v.league_id, v.voting_user_id, v.round_id;

-- ============================================================
-- ADJUSTED VOTES: each vote minus the voter's round average
-- Positive = voter liked this more than usual
-- Negative = voter liked this less than usual
-- ============================================================
CREATE VIEW IF NOT EXISTS v_adjusted_votes AS
SELECT
    v.league_id,
    v.round_id,
    v.voting_user_id,
    voter.user_name AS voter_name,
    v.submission_user_id,
    submitter.user_name AS submitter_name,
    v.points,
    vb.avg_points_per_submission AS voter_round_avg,
    ROUND(v.points - vb.avg_points_per_submission, 2) AS points_vs_avg
FROM votes v
JOIN users voter ON v.voting_user_id = voter.user_id
JOIN users submitter ON v.submission_user_id = submitter.user_id
JOIN v_voter_baseline vb ON v.league_id = vb.league_id
    AND v.voting_user_id = vb.voting_user_id
    AND v.round_id = vb.round_id
WHERE v.voting_user_id != v.submission_user_id;

-- ============================================================
-- BIGGEST FANS: who consistently over-votes for whom (per league)
-- Sort by total_adjusted_surplus descending to find the strongest affinities.
-- ============================================================
CREATE VIEW IF NOT EXISTS v_biggest_fans AS
SELECT
    league_id,
    voting_user_id,
    voter_name,
    submission_user_id,
    submitter_name,
    ROUND(SUM(points_vs_avg), 2) AS total_adjusted_surplus,
    COUNT(*) AS rounds_together,
    ROUND(AVG(points_vs_avg), 2) AS avg_adjusted_surplus
FROM v_adjusted_votes
GROUP BY league_id, voting_user_id, submission_user_id;

-- ============================================================
-- BIGGEST FANS (CROSS-LEAGUE): same as above but aggregated across all leagues
-- ============================================================
CREATE VIEW IF NOT EXISTS v_biggest_fans_all AS
SELECT
    voting_user_id,
    voter_name,
    submission_user_id,
    submitter_name,
    ROUND(SUM(points_vs_avg), 2) AS total_adjusted_surplus,
    COUNT(*) AS rounds_together,
    ROUND(AVG(points_vs_avg), 2) AS avg_adjusted_surplus,
    COUNT(DISTINCT league_id) AS leagues_together
FROM v_adjusted_votes
GROUP BY voting_user_id, submission_user_id;

-- ============================================================
-- CONTRARIAN SCORES: voting variance per user per league
-- High variance = unusual/contrarian taste (strong loves AND strong dislikes)
-- ============================================================
CREATE VIEW IF NOT EXISTS v_contrarian_scores AS
SELECT
    league_id,
    voting_user_id,
    voter_name,
    COUNT(*) AS total_votes,
    ROUND(AVG(points_vs_avg * points_vs_avg) - AVG(points_vs_avg) * AVG(points_vs_avg), 4) AS variance,
    ROUND(SQRT(AVG(points_vs_avg * points_vs_avg) - AVG(points_vs_avg) * AVG(points_vs_avg)), 4) AS std_dev
FROM v_adjusted_votes
GROUP BY league_id, voting_user_id;

-- ============================================================
-- ROUND STANDINGS: per-round submission rankings
-- ============================================================
CREATE VIEW IF NOT EXISTS v_round_standings AS
SELECT
    s.league_id,
    l.league_name,
    s.round_id,
    r.round_number,
    r.round_name,
    s.user_id,
    u.user_name,
    s.song_title,
    s.artist,
    s.total_points,
    s.finishing_place,
    s.spotify_uri
FROM submissions s
JOIN leagues l ON s.league_id = l.league_id
JOIN rounds r ON s.round_id = r.round_id
JOIN users u ON s.user_id = u.user_id
ORDER BY s.league_id, r.round_number, s.finishing_place;

-- ============================================================
-- LEAGUE STANDINGS: aggregate points per user per league
-- ============================================================
CREATE VIEW IF NOT EXISTS v_league_standings AS
SELECT
    s.league_id,
    l.league_name,
    s.user_id,
    u.user_name,
    SUM(s.total_points) AS total_points,
    COUNT(*) AS rounds_played,
    ROUND(AVG(s.total_points), 2) AS avg_points_per_round,
    ROUND(AVG(s.finishing_place), 2) AS avg_finish,
    MIN(s.finishing_place) AS best_finish,
    SUM(CASE WHEN s.finishing_place = 1 THEN 1 ELSE 0 END) AS first_place_count
FROM submissions s
JOIN leagues l ON s.league_id = l.league_id
JOIN users u ON s.user_id = u.user_id
GROUP BY s.league_id, s.user_id
ORDER BY s.league_id, total_points DESC;

-- ============================================================
-- CROSS-LEAGUE STATS: all-time player stats
-- ============================================================
CREATE VIEW IF NOT EXISTS v_cross_league_stats AS
SELECT
    u.user_id,
    u.user_name,
    COUNT(DISTINCT s.league_id) AS leagues_played,
    COUNT(*) AS total_rounds,
    SUM(s.total_points) AS total_points_all_time,
    ROUND(AVG(s.total_points), 2) AS avg_points_per_round,
    ROUND(AVG(s.finishing_place), 2) AS avg_finish,
    MIN(s.finishing_place) AS best_finish,
    SUM(CASE WHEN s.finishing_place = 1 THEN 1 ELSE 0 END) AS first_place_count
FROM submissions s
JOIN users u ON s.user_id = u.user_id
GROUP BY u.user_id
ORDER BY total_points_all_time DESC;

-- ============================================================
-- MUTUAL FANS: bidirectional affinity pairs
-- Combines A→B surplus with B→A surplus to find pairs that
-- consistently vote highly for EACH OTHER.
-- ============================================================
CREATE VIEW IF NOT EXISTS v_mutual_fans AS
SELECT
    a.voting_user_id AS player_a_id,
    a.voter_name AS player_a,
    a.submission_user_id AS player_b_id,
    a.submitter_name AS player_b,
    ROUND(a.total_adjusted_surplus, 2) AS a_to_b_surplus,
    ROUND(b.total_adjusted_surplus, 2) AS b_to_a_surplus,
    ROUND(a.total_adjusted_surplus + b.total_adjusted_surplus, 2) AS mutual_surplus,
    a.rounds_together
FROM v_biggest_fans_all a
JOIN v_biggest_fans_all b
    ON a.voting_user_id = b.submission_user_id
    AND a.submission_user_id = b.voting_user_id
WHERE a.voting_user_id < a.submission_user_id   -- deduplicate pairs
ORDER BY mutual_surplus DESC;

-- ============================================================
-- ARTIST STATS: per-artist aggregate stats via junction table
-- ============================================================
CREATE VIEW IF NOT EXISTS v_artist_stats AS
SELECT
    sa.artist_name,
    COUNT(*) AS submission_count,
    COUNT(DISTINCT s.user_id) AS unique_submitters,
    SUM(s.total_points) AS total_points,
    ROUND(AVG(s.total_points), 2) AS avg_points,
    COUNT(DISTINCT s.league_id) AS leagues_appeared
FROM submission_artists sa
JOIN submissions s ON sa.submission_id = s.submission_id
GROUP BY sa.artist_name
ORDER BY submission_count DESC;

-- ============================================================
-- USER ARTIST STATS: which artists does each user submit most
-- ============================================================
CREATE VIEW IF NOT EXISTS v_user_artist_stats AS
SELECT
    s.user_id,
    u.user_name,
    sa.artist_name,
    COUNT(*) AS times_submitted,
    SUM(s.total_points) AS total_points,
    ROUND(AVG(s.total_points), 2) AS avg_points
FROM submission_artists sa
JOIN submissions s ON sa.submission_id = s.submission_id
JOIN users u ON s.user_id = u.user_id
GROUP BY s.user_id, sa.artist_name
ORDER BY s.user_id, times_submitted DESC;

-- ============================================================
-- SUBMISSION DETAILS: denormalized for easy dashboard queries
-- ============================================================
CREATE VIEW IF NOT EXISTS v_submission_details AS
SELECT
    s.submission_id,
    s.league_id,
    l.league_name,
    s.round_id,
    r.round_number,
    r.round_name,
    s.user_id,
    u.user_name,
    s.song_title,
    s.artist,
    s.album,
    s.spotify_uri,
    s.total_points,
    s.finishing_place,
    s.submitter_comment
FROM submissions s
JOIN leagues l ON s.league_id = l.league_id
JOIN rounds r ON s.round_id = r.round_id
JOIN users u ON s.user_id = u.user_id;
