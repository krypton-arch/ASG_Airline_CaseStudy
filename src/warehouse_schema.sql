CREATE TABLE dim_flight (
    flight_schedule_key VARCHAR(20) PRIMARY KEY,
    flight_id VARCHAR(5) NOT NULL,
    airline VARCHAR(50) NOT NULL,
    source CHAR(3) NOT NULL,
    destination CHAR(3) NOT NULL,
    departure_time TIMESTAMP NOT NULL,
    arrival_time TIMESTAMP NOT NULL,
    duration_minutes INTEGER NOT NULL,
    overnight_adjusted BOOLEAN NOT NULL,
    has_anomaly BOOLEAN NOT NULL,
    anomaly_type VARCHAR(100)
);

CREATE TABLE dim_passenger_masked (
    passenger_key CHAR(64) PRIMARY KEY,
    age_band VARCHAR(20),
    gender VARCHAR(10),
    date_of_birth DATE
);

CREATE TABLE fact_booking (
    booking_id VARCHAR(20) PRIMARY KEY,
    passenger_key CHAR(64) NOT NULL,
    flight_id VARCHAR(5) NOT NULL,
    flight_schedule_key VARCHAR(20),
    booking_date TIMESTAMP NOT NULL,
    status VARCHAR(20) NOT NULL,
    seat_number VARCHAR(5),
    flight_match_status VARCHAR(20) NOT NULL
);

CREATE TABLE fact_payment (
    payment_id VARCHAR(20) PRIMARY KEY,
    booking_id VARCHAR(20) NOT NULL,
    amount DECIMAL(12,2),
    payment_method VARCHAR(20) NOT NULL,
    payment_status VARCHAR(20) NOT NULL
);
