USE airportdb;
CREATE VIEW flight_view AS 
SELECT  Date(`departure`) AS `date`, airlinename, COUNT(1) AS flights_count
FROM flight f
JOIN airline a
USING(airline_id)
JOIN airport ap
ON ap.airport_id = f.from
GROUP BY Date(`departure`), airlinename
