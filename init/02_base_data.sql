-- ============================================
-- FROSTEL SEED DATA
-- Simple test data for Docker initialization
-- ============================================

USE frostel_db;
-- Password: "password123" hashed with bcrypt

INSERT INTO user (name, surname, email, password, date_of_birth, membership)
VALUES ('John', 'Doe', 'john.doe@example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYvXN8z9ZKu',
        '1990-05-15', 'GOLD'),
       ('Jane', 'Smith', 'jane.smith@example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYvXN8z9ZKu',
        '1985-08-22', 'PLATINUM'),
       ('Carlos', 'Garcia', 'carlos.garcia@example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYvXN8z9ZKu',
        '1992-11-03', 'BRONZE'),
       ('Maria', 'Rodriguez', 'maria.rodriguez@example.com',
        '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYvXN8z9ZKu', '1988-03-17', 'FREE'),
       ('Ahmed', 'Hassan', 'ahmed.hassan@example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYvXN8z9ZKu',
        '1995-07-28', 'FREE');

INSERT INTO hotel (name, country, city, address, description, star_rating)
VALUES ('Grand Plaza Hotel', 'Spain', 'Madrid', 'Gran Via 123',
        'Luxury hotel in the heart of Madrid with stunning city views', 5),
       ('Beach Paradise Resort', 'Spain', 'Barcelona', 'Passeig Maritim 45',
        'Beautiful beachfront resort with Mediterranean cuisine', 4),
       ('Mountain View Lodge', 'Switzerland', 'Zurich', 'Bahnhofstrasse 78',
        'Cozy alpine hotel with mountain views and spa facilities', 4),
       ('City Center Inn', 'United Kingdom', 'London', 'Oxford Street 234',
        'Modern budget hotel near major attractions and shopping', 3),
       ('Sunset Beach Hotel', 'USA', 'Miami', 'Ocean Drive 567', 'Art Deco hotel on South Beach with ocean views', 5);

INSERT INTO hotel_contact_information (hotel_id, phone, email)
VALUES (1, '+34 91 123 4567', 'reservations@grandplaza.com'),
       (1, '+34 91 123 4568', 'concierge@grandplaza.com'),
       (2, '+34 93 234 5678', 'info@beachparadise.com'),
       (3, '+41 44 345 6789', 'booking@mountainview.ch'),
       (4, '+44 20 456 7890', 'reception@citycenterinn.co.uk'),
       (5, '+1 305 567 8901', 'reservations@sunsetbeach.com');

INSERT INTO airport (code, name, city, country)
VALUES ('MAD', 'Adolfo Suárez Madrid-Barajas Airport', 'Madrid', 'Spain'),
       ('BCN', 'Barcelona-El Prat Airport', 'Barcelona', 'Spain'),
       ('JFK', 'John F. Kennedy International Airport', 'New York', 'USA'),
       ('LHR', 'London Heathrow Airport', 'London', 'United Kingdom'),
       ('CDG', 'Charles de Gaulle Airport', 'Paris', 'France');

INSERT INTO airline (code, name, country, logo_url)
VALUES ('IB', 'Iberia', 'Spain', 'https://example.com/logos/iberia.png'),
       ('BA', 'British Airways', 'United Kingdom', 'https://example.com/logos/ba.png'),
       ('AF', 'Air France', 'France', 'https://example.com/logos/airfrance.png'),
       ('AA', 'American Airlines', 'USA', 'https://example.com/logos/aa.png'),
       ('LH', 'Lufthansa', 'Germany', 'https://example.com/logos/lufthansa.png');

INSERT INTO discount (name, description, discount_percentage, applicable_to, start_date, end_date, is_active)
VALUES ('Summer Sale 2025', 'Save big on beach hotels this summer!', 25.00, 'HOTEL', '2025-06-01 00:00:00',
        '2025-08-31 23:59:59', TRUE),
       ('Early Bird Flight Deal', 'Book 30 days in advance and save', 15.00, 'FLIGHT', '2025-01-01 00:00:00',
        '2025-12-31 23:59:59', TRUE),
       ('Black Friday Special', 'Massive discounts on all bookings', 30.00, 'HOTEL', '2025-11-25 00:00:00',
        '2025-11-30 23:59:59', TRUE),
       ('Weekend Getaway', 'Special rates for weekend stays', 20.00, 'HOTEL', '2025-01-01 00:00:00',
        '2025-12-31 23:59:59', TRUE),
       ('Holiday Season Sale', 'Celebrate the holidays with great deals', 10.00, 'FLIGHT', '2025-12-15 00:00:00',
        '2025-12-31 23:59:59', TRUE);
