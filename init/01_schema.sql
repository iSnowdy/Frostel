CREATE SCHEMA IF NOT EXISTS frostel_db DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE frostel_db;
SHOW WARNINGS;


DROP TABLE IF EXISTS user;
CREATE TABLE IF NOT EXISTS user
(
    id            INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name          VARCHAR(255) NOT NULL,
    surname       VARCHAR(255) NOT NULL,
    email         VARCHAR(255) NOT NULL,
    password      VARCHAR(255) NOT NULL, -- Encryption?
    date_of_birth DATE         NOT NULL,
    membership    ENUM ('FREE', 'BRONZE', 'GOLD', 'PLATINUM') DEFAULT 'FREE',
    created_at    TIMESTAMP                                   DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP                                   DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY unique_email (email),
    INDEX idx_membership (membership)
) ENGINE = InnoDB;

DROP TABLE IF EXISTS hotel;
CREATE TABLE IF NOT EXISTS hotel
(
    id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(255)     NOT NULL,
    country     VARCHAR(255)     NOT NULL,
    city        VARCHAR(255)     NOT NULL,
    address     VARCHAR(255)     NOT NULL,
    description TEXT,
    star_rating TINYINT UNSIGNED NOT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT chk_star_rating CHECK (star_rating BETWEEN 1 AND 5),
    INDEX idx_country (country),
    INDEX idx_city (city),
    INDEX idx_name (name)
) ENGINE = InnoDB;


DROP TABLE IF EXISTS hotel_contact_information;
CREATE TABLE IF NOT EXISTS hotel_contact_information
(
    id           INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    hotel_id     INT UNSIGNED NOT NULL,
    phone        VARCHAR(50)  NOT NULL,
    email        VARCHAR(320) NOT NULL,
    contact_type ENUM ('MAIN', 'RESERVATIONS', 'SUPPORT', 'EMERGENCY') DEFAULT 'MAIN',

    CONSTRAINT hotel_contact_information_hotel_id_fk FOREIGN KEY (hotel_id) REFERENCES hotel (id) ON DELETE CASCADE,
    UNIQUE KEY unique_hotel_phone (hotel_id, phone),
    INDEX idx_hotel_id (hotel_id)
) ENGINE = InnoDB;


DROP TABLE IF EXISTS room_type;
CREATE TABLE IF NOT EXISTS room_type
(
    id            INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    hotel_id      INT UNSIGNED                                NOT NULL,
    name          VARCHAR(100)                                NOT NULL,
    type_category ENUM ('SINGLE', 'DOUBLE', 'TRIPLE', 'QUAD') NOT NULL,
    base_price    DECIMAL(10, 2)                              NOT NULL,
    max_occupancy TINYINT UNSIGNED                            NOT NULL,
    description   TEXT,
    amenities     JSON,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT room_type_hotel_id_fk FOREIGN KEY (hotel_id) REFERENCES hotel (id) ON DELETE CASCADE,
    UNIQUE (hotel_id, name, type_category),
    INDEX idx_hotel_category (hotel_id, type_category)
) ENGINE = InnoDB;

DROP TABLE IF EXISTS room;
CREATE TABLE IF NOT EXISTS room
(
    id           INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    hotel_id     INT UNSIGNED                                                          NOT NULL,
    room_type_id INT UNSIGNED                                                          NOT NULL,
    room_number  VARCHAR(50)                                                           NOT NULL, -- 101 or A-101...
    room_status  ENUM ('AVAILABLE', 'OCCUPIED', 'RESERVED', 'MAINTENANCE', 'CLEANING') NOT NULL DEFAULT 'AVAILABLE',
    created_at   TIMESTAMP                                                                      DEFAULT CURRENT_TIMESTAMP,
    updated_at   TIMESTAMP                                                                      DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT room_room_type_id_fk FOREIGN KEY (room_type_id) REFERENCES room_type (id) ON DELETE CASCADE,
    CONSTRAINT room_hotel_id_fk FOREIGN KEY (hotel_id) REFERENCES hotel (id) ON DELETE CASCADE,
    UNIQUE KEY unique_room_number (hotel_id, room_number),
    INDEX idx_room_type_id (room_type_id),
    INDEX idx_room_number (room_number),
    INDEX idx_room_status (room_status)
) ENGINE = InnoDB;

DROP TABLE IF EXISTS reservation;
CREATE TABLE IF NOT EXISTS reservation
(
    id                INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    booking_reference VARCHAR(20) UNIQUE NOT NULL,
    user_id           INT UNSIGNED       NOT NULL,
    hotel_id          INT UNSIGNED       NOT NULL,
    room_id           INT UNSIGNED       NOT NULL,
    room_type_id      INT UNSIGNED       NOT NULL,
    check_in_date     DATE               NOT NULL,
    check_out_date    DATE               NOT NULL,
    number_of_guests  TINYINT UNSIGNED   NOT NULL,
    total_nights      INT UNSIGNED GENERATED ALWAYS AS (DATEDIFF(check_out_date, check_in_date)) STORED,
    base_price        DECIMAL(10, 2)     NOT NULL, -- Price at time of booking
    discount_amount   DECIMAL(10, 2)                                                          DEFAULT 0.00,
    total_price       DECIMAL(10, 2)     NOT NULL,
    status            ENUM ('PENDING', 'CONFIRMED', 'CHECKED_IN', 'CHECKED_OUT', 'CANCELLED') DEFAULT 'PENDING',
    special_requests  TEXT,
    created_at        TIMESTAMP                                                               DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP                                                               DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_booking_user FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE RESTRICT,
    CONSTRAINT fk_booking_hotel FOREIGN KEY (hotel_id) REFERENCES hotel (id) ON DELETE RESTRICT,
    CONSTRAINT fk_booking_room FOREIGN KEY (room_id) REFERENCES room (id) ON DELETE RESTRICT,
    CONSTRAINT fk_booking_room_type FOREIGN KEY (room_type_id) REFERENCES room_type (id) ON DELETE RESTRICT,
    CONSTRAINT chk_check_out_after_check_in CHECK (check_out_date > check_in_date),
    CONSTRAINT chk_guests_positive CHECK (number_of_guests > 0),
    INDEX idx_user_bookings (user_id, status),
    INDEX idx_hotel_dates (hotel_id, check_in_date, check_out_date),
    INDEX idx_booking_reference (booking_reference),
    INDEX idx_check_in_date (check_in_date)
) ENGINE = InnoDB;

-- Flight System
DROP TABLE IF EXISTS airport;
CREATE TABLE airport
(
    id         INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    code       VARCHAR(3) UNIQUE NOT NULL, -- "JFK", "MAD"...
    name       VARCHAR(255)      NOT NULL, -- "John F. Kennedy International"
    city       VARCHAR(255)      NOT NULL,
    country    VARCHAR(255)      NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_code (code),
    INDEX idx_city (city),
    INDEX idx_country (country)
) ENGINE = InnoDB;

DROP TABLE IF EXISTS airline;
CREATE TABLE airline
(
    id         INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    code       VARCHAR(3) UNIQUE NOT NULL, -- "AA"
    name       VARCHAR(255)      NOT NULL, -- "American Airlines"
    country    VARCHAR(255),
    logo_url   VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_code (code)
) ENGINE = InnoDB;

DROP TABLE IF EXISTS flight_route;
CREATE TABLE flight_route
(
    id                     INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    airline_id             INT UNSIGNED NOT NULL,
    flight_number          VARCHAR(10)  NOT NULL,
    origin_airport_id      INT UNSIGNED NOT NULL,
    destination_airport_id INT UNSIGNED NOT NULL,
    duration_minutes       INT UNSIGNED NOT NULL,
    aircraft               VARCHAR(50),
    created_at             TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at             TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_route_airline FOREIGN KEY (airline_id) REFERENCES airline (id) ON DELETE RESTRICT,
    CONSTRAINT fk_route_origin FOREIGN KEY (origin_airport_id) REFERENCES airport (id) ON DELETE RESTRICT,
    CONSTRAINT fk_route_destination FOREIGN KEY (destination_airport_id) REFERENCES airport (id) ON DELETE RESTRICT,
    UNIQUE KEY unique_flight_number (airline_id, flight_number),
    INDEX idx_origin (origin_airport_id),
    INDEX idx_destination (destination_airport_id)
) ENGINE = InnoDB;

DROP TABLE IF EXISTS flight;
CREATE TABLE flight
(
    id                 INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    flight_route_id    INT UNSIGNED NOT NULL,
    departure_datetime DATETIME     NOT NULL,
    arrival_datetime   DATETIME     NOT NULL,
    status             ENUM ('SCHEDULED', 'BOARDING', 'DEPARTED', 'ARRIVED', 'DELAYED', 'CANCELLED') DEFAULT 'SCHEDULED',
    gate               VARCHAR(10),
    terminal           VARCHAR(10),
    created_at         TIMESTAMP                                                                     DEFAULT CURRENT_TIMESTAMP,
    updated_at         TIMESTAMP                                                                     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_flight_route FOREIGN KEY (flight_route_id) REFERENCES flight_route (id) ON DELETE RESTRICT,
    CONSTRAINT chk_arrival_after_departure CHECK (arrival_datetime > departure_datetime),
    INDEX idx_departure_date (departure_datetime),
    INDEX idx_route_departure (flight_route_id, departure_datetime),
    INDEX idx_status (status)
) ENGINE = InnoDB;

DROP TABLE IF EXISTS flight_class;
CREATE TABLE flight_class
(
    id                   INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    flight_id            INT UNSIGNED                                             NOT NULL,
    class_type           ENUM ('ECONOMY', 'PREMIUM_ECONOMY', 'BUSINESS', 'FIRST') NOT NULL,
    total_seats          INT UNSIGNED                                             NOT NULL,
    available_seats      INT UNSIGNED                                             NOT NULL,
    base_price           DECIMAL(10, 2)                                           NOT NULL,
    baggage_allowance_kg INT UNSIGNED,
    has_meal             BOOLEAN   DEFAULT FALSE,
    is_refundable        BOOLEAN   DEFAULT FALSE,
    created_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_class_flight FOREIGN KEY (flight_id) REFERENCES flight (id) ON DELETE CASCADE,
    CONSTRAINT chk_base_price_positive CHECK (base_price > 0),
    CONSTRAINT chk_available_seats_valid CHECK (available_seats >= 0 AND available_seats <= total_seats),
    INDEX idx_flight_class (flight_id, class_type)
) ENGINE = InnoDB;

DROP TABLE IF EXISTS flight_booking;
CREATE TABLE flight_booking
(
    id                INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    booking_reference VARCHAR(20) UNIQUE NOT NULL,
    user_id           INT UNSIGNED       NOT NULL,
    flight_id         INT UNSIGNED       NOT NULL,
    flight_class_id   INT UNSIGNED       NOT NULL,
    passenger_name    VARCHAR(255)       NOT NULL,
    passenger_email   VARCHAR(255)       NOT NULL,
    seat_number       VARCHAR(10),
    base_price        DECIMAL(10, 2)     NOT NULL,
    discount_amount   DECIMAL(10, 2)                                                                   DEFAULT 0.00,
    total_price       DECIMAL(10, 2)     NOT NULL,
    status            ENUM ('PENDING', 'CONFIRMED', 'CHECKED_IN', 'BOARDED', 'COMPLETED', 'CANCELLED') DEFAULT 'PENDING',
    created_at        TIMESTAMP                                                                        DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP                                                                        DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_flight_booking_user FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE RESTRICT,
    CONSTRAINT fk_flight_booking_flight FOREIGN KEY (flight_id) REFERENCES flight (id) ON DELETE RESTRICT,
    CONSTRAINT fk_flight_booking_class FOREIGN KEY (flight_class_id) REFERENCES flight_class (id) ON DELETE RESTRICT,
    INDEX idx_user_bookings (user_id, status),
    INDEX idx_flight_bookings (flight_id),
    INDEX idx_booking_reference (booking_reference)
) ENGINE = InnoDB;

DROP TABLE IF EXISTS discount;
CREATE TABLE discount
(
    id                  INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name                VARCHAR(255)             NOT NULL,
    description         TEXT,
    discount_percentage DECIMAL(5, 2)            NOT NULL,
    applicable_to       ENUM ('HOTEL', 'FLIGHT') NOT NULL,
    is_active           BOOLEAN                  NOT NULL DEFAULT TRUE,
    start_date          DATETIME                 NOT NULL,
    end_date            DATETIME,
    created_at          TIMESTAMP                         DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_discount_percentage CHECK (discount_percentage > 0 AND discount_percentage < 100),
    CONSTRAINT chk_discount_dates CHECK (end_date IS NULL OR end_date > start_date),
    INDEX idx_name (name)
) ENGINE = InnoDB;

DROP TABLE IF EXISTS hotel_discount;
CREATE TABLE hotel_discount
(
    hotel_id    INT UNSIGNED NOT NULL,
    discount_id INT UNSIGNED NOT NULL,

    PRIMARY KEY (hotel_id, discount_id),
    CONSTRAINT FOREIGN KEY (hotel_id) REFERENCES hotel (id) ON DELETE CASCADE,
    CONSTRAINT FOREIGN KEY (discount_id) REFERENCES discount (id) ON DELETE CASCADE
) ENGINE = InnoDB;

DROP TABLE IF EXISTS flight_discount;
CREATE TABLE flight_discount
(
    flight_id   INT UNSIGNED NOT NULL,
    discount_id INT UNSIGNED NOT NULL,

    PRIMARY KEY (flight_id, discount_id),
    CONSTRAINT FOREIGN KEY (flight_id) REFERENCES flight (id) ON DELETE CASCADE,
    CONSTRAINT FOREIGN KEY (discount_id) REFERENCES discount (id) ON DELETE CASCADE
) ENGINE = InnoDB;


-- Payment Management

DROP TABLE IF EXISTS payment_method;
CREATE TABLE payment_method
(
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id         INT UNSIGNED                                                  NOT NULL,
    method_type     ENUM ('CREDIT_CARD', 'DEBIT_CARD', 'PAYPAL', 'BANK_TRANSFER') NOT NULL,
    card_last_four  VARCHAR(4),
    card_brand      VARCHAR(20),  -- "Visa", "Mastercard" ...
    cardholder_name VARCHAR(255),
    expiry_month    TINYINT UNSIGNED,
    expiry_year     SMALLINT UNSIGNED,
    payment_token   VARCHAR(255), -- Some identifier potentially issued by the payment processor (Stripe, PayPal, etc.)
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_payment_method_user FOREIGN KEY (user_id)
        REFERENCES user (id) ON DELETE CASCADE,
    INDEX idx_user_methods (user_id)
) ENGINE = InnoDB;

DROP TABLE IF EXISTS payment;
CREATE TABLE payment
(
    id                       INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    payment_reference        VARCHAR(50) UNIQUE                        NOT NULL,                              -- "PAY-ABC123"
    user_id                  INT UNSIGNED                              NOT NULL,
    -- What is being paid for + their references
    booking_id               INT UNSIGNED,
    flight_booking_id        INT UNSIGNED,
    booking_type             ENUM ('HOTEL', 'FLIGHT', 'PACKAGE')       NOT NULL,

    payment_method_id        INT UNSIGNED,
    payment_processor        ENUM ('STRIPE', 'PAYPAL', 'BANK', 'CASH') NOT NULL,
    processor_transaction_id VARCHAR(255),                                                                    -- Stripe charge ID, PayPal transaction ID
    subtotal                 DECIMAL(10, 2)                            NOT NULL,
    discount_amount          DECIMAL(10, 2)                                                    DEFAULT 0.00,
    total_amount             DECIMAL(10, 2)                            NOT NULL,
    currency                 VARCHAR(3)                                                        DEFAULT 'EUR', -- EUR, USD, GBP
    status                   ENUM ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'REFUNDED') DEFAULT 'PENDING',
    failure_reason           TEXT,
    paid_at                  TIMESTAMP,
    refunded_at              TIMESTAMP,
    created_at               TIMESTAMP                                                         DEFAULT CURRENT_TIMESTAMP,
    updated_at               TIMESTAMP                                                         DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_payment_user FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE RESTRICT,
    CONSTRAINT fk_payment_booking FOREIGN KEY (booking_id) REFERENCES reservation (id) ON DELETE RESTRICT,
    CONSTRAINT fk_payment_flight_booking FOREIGN KEY (flight_booking_id) REFERENCES flight_booking (id) ON DELETE RESTRICT,
    CONSTRAINT fk_payment_method FOREIGN KEY (payment_method_id) REFERENCES payment_method (id) ON DELETE SET NULL,
    CONSTRAINT chk_total_positive CHECK (total_amount > 0),
    CONSTRAINT chk_booking_type_references CHECK (
        (booking_type = 'HOTEL' AND booking_id IS NOT NULL AND flight_booking_id IS NULL) OR
        (booking_type = 'FLIGHT' AND booking_id IS NULL AND flight_booking_id IS NOT NULL) OR
        (booking_type = 'PACKAGE' AND booking_id IS NOT NULL AND flight_booking_id IS NOT NULL)
        ),
    INDEX idx_user_payments (user_id, status),
    INDEX idx_booking (booking_id),
    INDEX idx_flight_booking (flight_booking_id),
    INDEX idx_payment_reference (payment_reference),
    INDEX idx_status (status)
) ENGINE = InnoDB;

DROP TABLE IF EXISTS refund;
CREATE TABLE refund
(
    id                  INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    payment_id          INT UNSIGNED       NOT NULL,
    refund_reference    VARCHAR(50) UNIQUE NOT NULL, -- "REF-XYZ789"
    refund_amount       DECIMAL(10, 2)     NOT NULL,
    reason              TEXT,
    status              ENUM ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED') DEFAULT 'PENDING',
    processor_refund_id VARCHAR(255),
    processed_at        TIMESTAMP,
    created_at          TIMESTAMP                                             DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_refund_payment FOREIGN KEY (payment_id) REFERENCES payment (id) ON DELETE RESTRICT,
    INDEX idx_payment_refunds (payment_id)
) ENGINE = InnoDB;

-- Others

DROP TABLE IF EXISTS notification;
CREATE TABLE notification
(
    id                 BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id            INT UNSIGNED                                                                                    NOT NULL,
    type               ENUM ('BOOKING_CONFIRMED', 'CHECKIN_REMINDER', 'CANCELLATION', 'PAYMENT_RECEIVED', 'PROMOTION') NOT NULL,
    title              VARCHAR(255)                                                                                    NOT NULL,
    message            TEXT                                                                                            NOT NULL,
    is_read            BOOLEAN   DEFAULT FALSE,
    related_booking_id INT UNSIGNED,
    related_payment_id INT UNSIGNED,
    created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_notification_user FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE CASCADE,
    CONSTRAINT fk_notification_booking FOREIGN KEY (related_booking_id) REFERENCES reservation (id) ON DELETE SET NULL,
    CONSTRAINT fk_notification_payment FOREIGN KEY (related_payment_id) REFERENCES payment (id) ON DELETE SET NULL,
    INDEX idx_user_unread (user_id, is_read),
    INDEX idx_created_at (created_at)
) ENGINE = InnoDB;

DROP TABLE IF EXISTS wishlist;
CREATE TABLE wishlist
(
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id         INT UNSIGNED                            NOT NULL,
    item_type       ENUM ('HOTEL', 'FLIGHT', 'DESTINATION') NOT NULL,
    hotel_id        INT UNSIGNED,
    flight_route_id INT UNSIGNED,
    destination_id  INT UNSIGNED,
    notes           TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_wishlist_user FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE CASCADE,
    CONSTRAINT fk_wishlist_hotel FOREIGN KEY (hotel_id) REFERENCES hotel (id) ON DELETE CASCADE,
    CONSTRAINT fk_wishlist_flight_route FOREIGN KEY (flight_route_id) REFERENCES flight_route (id) ON DELETE CASCADE,
    CONSTRAINT chk_one_item CHECK (
        (item_type = 'HOTEL' AND hotel_id IS NOT NULL AND flight_route_id IS NULL AND destination_id IS NULL) OR
        (item_type = 'FLIGHT' AND flight_route_id IS NOT NULL AND hotel_id IS NULL AND destination_id IS NULL) OR
        (item_type = 'DESTINATION' AND destination_id IS NOT NULL AND hotel_id IS NULL AND flight_route_id IS NULL)
        ),
    UNIQUE KEY unique_user_hotel (user_id, hotel_id),
    UNIQUE KEY unique_user_flight (user_id, flight_route_id),
    UNIQUE KEY unique_user_destination (user_id, destination_id),
    INDEX idx_user_items (user_id, item_type)
) ENGINE = InnoDB;

DROP TABLE IF EXISTS review;
CREATE TABLE review
(
    id                INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id           INT UNSIGNED,
    review_type       ENUM ('HOTEL', 'FLIGHT') NOT NULL,
    hotel_id          INT UNSIGNED,
    flight_id         INT UNSIGNED,
    booking_id        INT UNSIGNED,
    flight_booking_id INT UNSIGNED,
    rating            TINYINT UNSIGNED         NOT NULL,
    comment           TEXT,
    helpful_count     INT UNSIGNED DEFAULT 0,
    not_helpful_count INT UNSIGNED DEFAULT 0,
    created_at        TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP    DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_review_user FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE SET NULL, -- Anonymize if user deleted
    CONSTRAINT fk_review_hotel FOREIGN KEY (hotel_id) REFERENCES hotel (id) ON DELETE CASCADE,
    CONSTRAINT fk_review_flight FOREIGN KEY (flight_id) REFERENCES flight (id) ON DELETE CASCADE,
    CONSTRAINT fk_review_booking FOREIGN KEY (booking_id) REFERENCES reservation (id) ON DELETE SET NULL,
    CONSTRAINT fk_review_flight_booking FOREIGN KEY (flight_booking_id) REFERENCES flight_booking (id) ON DELETE SET NULL,
    CONSTRAINT chk_rating CHECK (rating BETWEEN 1 AND 5),
    -- Ensure only one type is reviewed
    CONSTRAINT chk_review_type CHECK (
        (review_type = 'HOTEL' AND hotel_id IS NOT NULL AND flight_id IS NULL) OR
        (review_type = 'FLIGHT' AND flight_id IS NOT NULL AND hotel_id IS NULL)
        ),
    UNIQUE KEY unique_booking_review (booking_id),
    UNIQUE KEY unique_flight_booking_review (flight_booking_id),
    INDEX idx_hotel_reviews (hotel_id),
    INDEX idx_flight_reviews (flight_id),
    INDEX idx_user_reviews (user_id),
    INDEX idx_rating (rating)
) ENGINE = InnoDB;

DROP TABLE IF EXISTS audit_log;
CREATE TABLE audit_log
(
    id         BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    table_name VARCHAR(64)                         NOT NULL,
    operation  ENUM ('INSERT', 'UPDATE', 'DELETE') NOT NULL,
    record_id  INT UNSIGNED                        NOT NULL,
    user_id    INT UNSIGNED,
    old_values JSON, -- NULL for INSERT
    new_values JSON,-- NULL for DELETE
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_table_record (table_name, record_id),
    INDEX idx_table_operation (table_name, operation),
    INDEX idx_user (user_id),
    INDEX idx_created_at (created_at)
) ENGINE = InnoDB;

-- Triggers for bookings, flights and payments INSERT/UPDATE/DELETE into the audit log table

-- Bookings
DELIMITER $$
CREATE TRIGGER booking_audit_insert
    AFTER INSERT
    ON reservation
    FOR EACH ROW
BEGIN
    INSERT INTO audit_log (table_name, operation, record_id, user_id, new_values)
    VALUES ('reservation',
            'INSERT',
            NEW.id,
            NEW.user_id,
            JSON_OBJECT(
                    'booking_reference', NEW.booking_reference,
                    'user_id', NEW.user_id,
                    'hotel_id', NEW.hotel_id,
                    'room_id', NEW.room_id,
                    'check_in_date', NEW.check_in_date,
                    'check_out_date', NEW.check_out_date,
                    'total_price', NEW.total_price,
                    'status', NEW.status
            ));
END$$

CREATE TRIGGER booking_audit_update
    AFTER UPDATE
    ON reservation
    FOR EACH ROW
BEGIN
    INSERT INTO audit_log (table_name, operation, record_id, user_id, old_values, new_values)
    VALUES ('reservation',
            'UPDATE',
            NEW.id,
            NEW.user_id,
            JSON_OBJECT(
                    'booking_reference', OLD.booking_reference,
                    'user_id', OLD.user_id,
                    'hotel_id', OLD.hotel_id,
                    'room_id', OLD.room_id,
                    'check_in_date', OLD.check_in_date,
                    'check_out_date', OLD.check_out_date,
                    'total_price', OLD.total_price,
                    'status', OLD.status
            ),
            JSON_OBJECT(
                    'booking_reference', NEW.booking_reference,
                    'user_id', NEW.user_id,
                    'hotel_id', NEW.hotel_id,
                    'room_id', NEW.room_id,
                    'check_in_date', NEW.check_in_date,
                    'check_out_date', NEW.check_out_date,
                    'total_price', NEW.total_price,
                    'status', NEW.status
            ));
END$$

CREATE TRIGGER booking_audit_delete
    AFTER DELETE
    ON reservation
    FOR EACH ROW
BEGIN
    INSERT INTO audit_log (table_name, operation, record_id, user_id, old_values)
    VALUES ('reservation',
            'UPDATE',
            OLD.id,
            OLD.user_id,
            JSON_OBJECT(
                    'booking_reference', OLD.booking_reference,
                    'user_id', OLD.user_id,
                    'hotel_id', OLD.hotel_id,
                    'room_id', OLD.room_id,
                    'check_in_date', OLD.check_in_date,
                    'check_out_date', OLD.check_out_date,
                    'total_price', OLD.total_price,
                    'status', OLD.status
            ));
END$$

DELIMITER ;

-- Flights

DELIMITER $$

CREATE TRIGGER flight_booking_audit_insert
    AFTER INSERT
    ON flight_booking
    FOR EACH ROW
BEGIN
    INSERT INTO audit_log (table_name, operation, record_id, user_id, new_values)
    VALUES ('flight_booking',
            'INSERT',
            NEW.id,
            NEW.user_id,
            JSON_OBJECT(
                    'booking_reference', NEW.booking_reference,
                    'user_id', NEW.user_id,
                    'flight_id', NEW.flight_id,
                    'flight_class_id', NEW.flight_class_id,
                    'passenger_name', NEW.passenger_name,
                    'total_price', NEW.total_price,
                    'status', NEW.status
            ));
END$$

CREATE TRIGGER flight_booking_audit_update
    AFTER UPDATE
    ON flight_booking
    FOR EACH ROW
BEGIN
    INSERT INTO audit_log (table_name, operation, record_id, user_id, old_values, new_values)
    VALUES ('flight_booking',
            'UPDATE',
            NEW.id,
            NEW.user_id,
            JSON_OBJECT(
                    'booking_reference', OLD.booking_reference,
                    'flight_id', OLD.flight_id,
                    'flight_class_id', OLD.flight_class_id,
                    'passenger_name', OLD.passenger_name,
                    'total_price', OLD.total_price,
                    'status', OLD.status
            ),
            JSON_OBJECT(
                    'booking_reference', NEW.booking_reference,
                    'flight_id', NEW.flight_id,
                    'flight_class_id', NEW.flight_class_id,
                    'passenger_name', NEW.passenger_name,
                    'total_price', NEW.total_price,
                    'status', NEW.status
            ));
END$$

CREATE TRIGGER flight_booking_audit_delete
    AFTER DELETE
    ON flight_booking
    FOR EACH ROW
BEGIN
    INSERT INTO audit_log (table_name, operation, record_id, user_id, old_values)
    VALUES ('flight_booking',
            'DELETE',
            OLD.id,
            OLD.user_id,
            JSON_OBJECT(
                    'booking_reference', OLD.booking_reference,
                    'flight_id', OLD.flight_id,
                    'passenger_name', OLD.passenger_name,
                    'total_price', OLD.total_price,
                    'status', OLD.status
            ));
END$$

DELIMITER ;

-- Payments

DELIMITER $$

CREATE TRIGGER payment_audit_insert
    AFTER INSERT
    ON payment
    FOR EACH ROW
BEGIN
    INSERT INTO audit_log (table_name, operation, record_id, user_id, new_values)
    VALUES ('payment',
            'INSERT',
            NEW.id,
            NEW.user_id,
            JSON_OBJECT(
                    'payment_reference', NEW.payment_reference,
                    'user_id', NEW.user_id,
                    'booking_id', NEW.booking_id,
                    'flight_booking_id', NEW.flight_booking_id,
                    'booking_type', NEW.booking_type,
                    'total_amount', NEW.total_amount,
                    'status', NEW.status,
                    'payment_processor', NEW.payment_processor
            ));
END$$

CREATE TRIGGER payment_audit_update
    AFTER UPDATE
    ON payment
    FOR EACH ROW
BEGIN
    INSERT INTO audit_log (table_name, operation, record_id, user_id, old_values, new_values)
    VALUES ('payment',
            'UPDATE',
            NEW.id,
            NEW.user_id,
            JSON_OBJECT(
                    'payment_reference', OLD.payment_reference,
                    'total_amount', OLD.total_amount,
                    'status', OLD.status,
                    'paid_at', OLD.paid_at
            ),
            JSON_OBJECT(
                    'payment_reference', NEW.payment_reference,
                    'total_amount', NEW.total_amount,
                    'status', NEW.status,
                    'paid_at', NEW.paid_at
            ));
END$$

CREATE TRIGGER payment_audit_delete
    AFTER DELETE
    ON payment
    FOR EACH ROW
BEGIN
    INSERT INTO audit_log (table_name, operation, record_id, user_id, old_values)
    VALUES ('payment',
            'DELETE',
            OLD.id,
            OLD.user_id,
            JSON_OBJECT(
                    'payment_reference', OLD.payment_reference,
                    'total_amount', OLD.total_amount,
                    'status', OLD.status
            ));
END$$

DELIMITER ;

-- Events: auto-cancelling expired pending bookings, auto-expiring discounts, cleaning up old audit logs
-- These events ease the burden of the application and allow it to focus on the business logic

DELIMITER $$

CREATE EVENT cancel_expired_pending_bookings
    ON SCHEDULE EVERY 1 HOUR
    COMMENT 'Cancels pending bookings that have been pending for more than 24 hours'
    DO
    BEGIN
        UPDATE reservation
        SET status     = 'CANCELLED',
            updated_at = NOW()
        WHERE status = 'PENDING'
          AND created_at < DATE_SUB(NOW(), INTERVAL 24 HOUR);

        UPDATE flight_booking
        SET status     = 'CANCELLED',
            updated_at = NOW()
        WHERE status = 'PENDING'
          AND created_at < DATE_SUB(NOW(), INTERVAL 24 HOUR);
    END $$

CREATE EVENT expire_old_discounts
    ON SCHEDULE EVERY 1 DAY
        STARTS CONCAT(CURDATE() + INTERVAL 1 DAY, ' 03:00:00')
    COMMENT 'Expires discounts that have expired. Runs once a day at 3AM'
    DO
    BEGIN
        UPDATE discount
        SET is_active = FALSE
        WHERE is_active = TRUE
          AND end_date < NOW();
    END $$

CREATE EVENT cleanup_old_audit_logs
    ON SCHEDULE EVERY 1 WEEK
        STARTS CONCAT(CURDATE() + INTERVAL 1 DAY, ' 03:00:00')
    COMMENT 'Deletes old (1 year) audit logs. Runs once a week at 3AM'
    DO
    BEGIN
        DELETE
        FROM audit_log
        WHERE created_at < DATE_SUB(NOW(), INTERVAL 1 YEAR); -- 1 year old audit logs is max duration
    END $$

DELIMITER ;