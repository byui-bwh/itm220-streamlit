USE airportdb;
CREATE VIEW flight_view AS 
SELECT  Date(`departure`) as `date`, airlinename, count(1) as flights_count
FROM flight f
JOIN airline a
using(airline_id)
JOIN airport ap
ON ap.airport_id = f.from
GROUP BY Date(`departure`), airlinename